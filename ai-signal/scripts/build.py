#!/usr/bin/env python3
"""Build AI Signal from structured content. Python standard library only."""
from pathlib import Path
import argparse
import hashlib
import html
import json
import math
import re
from datetime import date
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "content" / "publication.json"
CATEGORIES = ["Models", "Agents", "Infrastructure", "Robotics", "Enterprise AI", "Security & Governance", "Research"]
SIGNALS = ["Noise", "Interesting", "Important", "Structural Shift"]
SECTIONS = [("facts", "Verified facts"), ("changed", "What actually changed"), ("why", "Why it matters"), ("technical", "Technical implications"), ("business", "Business implications"), ("outlook", "Where this could be going"), ("uncertainties", "Risks & uncertainties"), ("analysis", "Editorial analysis"), ("sources", "Sources")]
BASE = "https://ddugi.github.io/ai-signal/"

def e(value):
    return html.escape(str(value), quote=True)

def require(condition, message):
    if not condition:
        raise ValueError(message)

def valid_date(value):
    try:
        return isinstance(value, str) and date.fromisoformat(value).isoformat() == value
    except (ValueError, TypeError):
        return False

def validate(data):
    require(data.get("schemaVersion") == 1, "Unsupported schemaVersion")
    pub = data["publication"]
    require(pub["mode"] in ("demo", "live"), "Invalid publication mode")
    require(valid_date(pub["updatedAt"]), "Invalid publication date")
    require(data["stories"], "At least one story is required")
    ids = set()
    featured = 0
    for story in data["stories"]:
        slug = story["slug"]
        require(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug), "Unsafe story slug")
        require(story["id"] == slug and slug not in ids, "Story IDs must be unique and match slugs")
        ids.add(slug)
        require(story["status"] in ("demo", "draft", "published"), "Unknown story status")
        require(story["category"] in CATEGORIES and story["signal"] in SIGNALS, "Unknown category or signal")
        for field in ("title", "summary", "topic", "author", "scenario", "changed", "whyItMatters", "technicalImpact", "businessImpact", "outlook", "analysis", "sourceNote"):
            require(isinstance(story[field], str) and story[field].strip(), "Missing text field: " + field)
        require(isinstance(story["featured"], bool), "featured must be boolean")
        require(valid_date(story["publishedAt"]) and valid_date(story["updatedAt"]), "Invalid story dates")
        require(story["updatedAt"] >= story["publishedAt"], "Update date precedes publication")
        require(isinstance(story["facts"], list) and isinstance(story["sources"], list), "facts and sources must be arrays")
        require(isinstance(story["uncertainties"], list) and story["uncertainties"] and all(isinstance(x, str) and x.strip() for x in story["uncertainties"]), "Uncertainties must be explicit")
        source_ids = set()
        for source in story["sources"]:
            require(isinstance(source["id"], str) and source["id"] not in source_ids, "Duplicate source ID")
            require(re.fullmatch(r"[a-z0-9-]+", source["id"]), "Unsafe source ID")
            source_ids.add(source["id"])
            parsed = urlsplit(source["url"])
            require(parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password, "Sources must be public HTTPS URLs")
            require(source["title"].strip() and source["publisher"].strip(), "Source metadata missing")
            require(valid_date(source["accessedAt"]), "Invalid source access date")
            require(source.get("publishedAt") is None or valid_date(source["publishedAt"]), "Invalid source publication date")
        for fact in story["facts"]:
            require(isinstance(fact["text"], str) and fact["text"].strip(), "Empty fact")
            require(fact["sourceIds"] and all(x in source_ids for x in fact["sourceIds"]), "Fact has unresolved sources")
            require(valid_date(fact["verifiedAt"]), "Fact needs verification date")
        if story["status"] == "demo":
            require(not story["facts"], "Demonstration scenarios must not be labeled verified facts")
            require(story["review"]["status"] == "demonstration", "Demo must have demonstration review status")
        if story["status"] == "published":
            require(story["facts"] and story["sources"], "Published reporting requires verified facts and sources")
            require(story["review"]["status"] == "approved" and story["review"].get("reviewer") and valid_date(story["review"].get("reviewedAt")), "Published reporting requires recorded editorial approval")
        if pub["mode"] == "live" and story["status"] != "draft":
            require(story["status"] == "published", "Live edition cannot contain demo reporting")
        featured += int(story["featured"] and story["status"] != "draft")
    require(featured == 1, "Exactly one visible story must be featured")
    visible_ids = {s["id"] for s in data["stories"] if s["status"] != "draft"}
    signal_map = data["signalMap"]
    require(signal_map["status"] in ("demo", "editorial"), "Invalid map status")
    require(valid_date(signal_map["asOf"]), "Invalid map date")
    require(len(signal_map["items"]) == 10, "Signal Map requires ten areas")
    require(len({x["area"] for x in signal_map["items"]}) == 10, "Duplicate map areas")
    for item in signal_map["items"]:
        require(item["direction"] in ("up", "up-strong", "down", "flat"), "Invalid map direction")
        require(item["dimension"].strip() and item["rationale"].strip(), "Map needs a dimension and rationale")
        require(item["storyId"] is None or item["storyId"] in visible_ids, "Map story reference is invalid")
        if signal_map["status"] == "editorial":
            require(item["storyId"] is not None, "Editorial map movements require story evidence")
    weekly = data["weekly"]
    require(re.fullmatch(r"\d{4}-\d{2}-\d{2}", weekly["slug"]) and valid_date(weekly["date"]), "Invalid weekly edition")
    require(weekly["status"] in ("demo", "published"), "Invalid weekly status")
    require(weekly["storyIds"] and all(x in visible_ids for x in weekly["storyIds"]), "Weekly has unresolved stories")
    require(weekly["watchNext"] and all(isinstance(x, str) and x.strip() for x in weekly["watchNext"]), "Weekly watch list missing")
    if weekly["status"] == "published":
        require(all(s["status"] == "published" for s in data["stories"] if s["id"] in weekly["storyIds"]), "Published weekly cannot feature demos")
    return data

def read_minutes(story):
    fields = [story[k] for k in ("summary", "scenario", "changed", "whyItMatters", "technicalImpact", "businessImpact", "outlook", "analysis")]
    fields += story["uncertainties"] + [f["text"] for f in story["facts"]]
    return max(1, math.ceil(len(" ".join(fields).split()) / 220))

def stamp(value):
    return date.fromisoformat(value).strftime("%d %b %Y")

def strength(story):
    cls = {"Structural Shift": "structural", "Important": "important", "Interesting": "interesting", "Noise": "noise"}[story["signal"]]
    return f'<span class="strength {cls}">{e(story["signal"])}</span>'

def meta(story):
    return f'<div class="meta"><span>{e(story["topic"])}</span><time datetime="{e(story["publishedAt"])}">{stamp(story["publishedAt"])}</time><span>{read_minutes(story)} min read</span></div>'

def demo_tag(story):
    return '<span class="demo-tag">Editorial demonstration</span>' if story["status"] == "demo" else '<span class="label">Reported signal</span>'

def header(title, description, prefix, canonical, data, asset_version):
    pub = data["publication"]
    label = "DEMONSTRATION EDITION" if pub["mode"] == "demo" else "INDEPENDENT EDITORIAL"
    note = "All stories are fictional scenarios. No current news is being reported." if pub["mode"] == "demo" else "Facts, interpretation, and outlook are labeled separately. Read our editorial method."
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} — AI Signal</title><meta name="description" content="{e(description)}"><meta name="theme-color" content="#f5f3eb">
<link rel="canonical" href="{e(canonical)}"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(description)}"><meta property="og:type" content="website"><meta property="og:url" content="{e(canonical)}">
<link rel="alternate" type="application/atom+xml" title="AI Signal" href="{prefix}feed.xml">
<link rel="stylesheet" href="{prefix}assets/signal.css?v={asset_version}"><script src="{prefix}assets/signal.js?v={asset_version}" defer></script>
</head><body><a class="skip" href="#main">Skip to content</a><div class="shell">
<div class="utility"><a href="{prefix}../">A publication from Dugi Research Lab ↗</a><span>Edition {e(pub["edition"])} / <b>{label}</b></span></div>
<header class="masthead"><a class="wordmark" href="{prefix}" aria-label="AI Signal home"><span class="asterisk" aria-hidden="true">✳</span>AI Signal</a><nav class="mastnav" aria-label="Publication navigation"><a href="{prefix}#latest">Latest Signals</a><a href="{prefix}#signal-map">Signal Map</a><a href="{prefix}about/">Our method</a><a class="weekly-link" href="{prefix}weekly/{e(data["weekly"]["slug"])}/">Weekly Signal ↗</a></nav></header>
<div class="edition-note"><strong>{label}</strong><span>{e(note)}</span></div>'''

def footer(prefix):
    return f'''<footer class="footer"><div><a class="wordmark" href="{prefix}">AI Signal<span style="color:var(--orange)">✳</span></a><p>What changed. Why it matters. Where it’s going.</p><p class="small">© 2026 Dugi Selmanaj. Editorial content: all rights reserved.</p></div><div class="footer-links"><a href="{prefix}about/">Editorial method</a><a href="{prefix}policies/editorial/">Editorial standards</a><a href="{prefix}policies/corrections/">Corrections</a><a href="{prefix}policies/privacy/">Privacy</a><a href="{prefix}content/publication.json">Open content / JSON</a><a href="https://github.com/ddugi/ddugi.github.io/tree/main/ai-signal">Publication source ↗</a></div></footer></div></body></html>'''

ART = '''<svg viewBox="0 0 280 330" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><rect x="12" y="15" width="256" height="295" rx="128" fill="#e6f29b"/><circle cx="140" cy="145" r="83" fill="none" stroke="#839570"/><circle cx="140" cy="145" r="52" fill="none" stroke="#839570"/><path d="M34 210L140 145L232 75" fill="none" stroke="#172822" stroke-width="2"/><path d="M218 77L233 74L230 89" fill="none" stroke="#172822" stroke-width="2"/><rect x="118" y="123" width="44" height="44" rx="4" fill="#172822" transform="rotate(12 140 145)"/><circle cx="80" cy="182" r="9" fill="#b74220"/><path d="M43 245H238" stroke="#839570"/><text x="140" y="271" text-anchor="middle" font-family="monospace" font-size="9" fill="#172822">CAPABILITY ≠ AUTHORITY</text><text x="140" y="287" text-anchor="middle" font-family="monospace" font-size="7" fill="#65716b">A CONCEPTUAL STUDY</text></svg>'''

def article_item(story, index):
    search = " ".join(story[k] for k in ("title", "summary", "topic", "category", "signal")).lower()
    return f'''<article class="story-item" data-story data-category="{e(story["category"])}" data-signal="{e(story["signal"])}" data-search="{e(search)}">
<span class="story-number">{index:02d} / {e(story["category"])}</span>{demo_tag(story)}<h3><a href="stories/{e(story["slug"])}/">{e(story["title"])}</a></h3><p>{e(story["summary"])}</p>{meta(story)}{strength(story)}</article>'''

def home(data, version):
    stories = sorted([s for s in data["stories"] if s["status"] != "draft"], key=lambda s: s["publishedAt"], reverse=True)
    featured = next(s for s in stories if s["featured"])
    others = [s for s in stories if s is not featured]
    briefing = "".join(f'<li><span class="label">{e(s["category"])}</span><a href="stories/{e(s["slug"])}/">{e(s["title"])}</a><span class="demo-tag">{"Demo scenario" if s["status"] == "demo" else stamp(s["publishedAt"])}</span></li>' for s in others[:3])
    items = []
    arrows = {"up": "↑", "up-strong": "↑↑", "down": "↓", "flat": "→"}
    arrow_labels = {"up": "Upward direction", "up-strong": "Strong upward direction", "down": "Downward direction", "flat": "No change assumed"}
    for item in data["signalMap"]["items"]:
        link = f'<a href="stories/{e(item["storyId"])}/">Read the scenario ↗</a>' if item["storyId"] else ""
        items.append(f'<article class="map-cell"><h3>{e(item["area"])}</h3><span class="direction" aria-label="{arrow_labels[item["direction"]]}">{arrows[item["direction"]]}</span><span class="dimension">{e(item["dimension"])}</span><details><summary>Why this direction</summary><p class="rationale">{e(item["rationale"])}</p>{link}</details></article>')
    filters = ["All", "Structural Shifts"] + CATEGORIES
    filter_html = "".join(f'<button type="button" data-filter="{e(c)}" aria-pressed="{str(c == "All").lower()}">{e(c)}</button>' for c in filters)
    weekly = data["weekly"]
    demo_map = data["signalMap"]["status"] == "demo"
    return header("What changed. Why it matters. Where it’s going.", "An editorial AI publication. The launch edition contains clearly labeled fictional demonstrations, not current news.", "./", BASE, data, version) + f'''
<main id="main"><section class="hero" aria-labelledby="publication-title"><h1 id="publication-title">AI Signal<span>✳</span></h1><div class="hero-copy"><p>What changed. Why it matters.<br>Where it’s going.</p><small>A little less breathless. A lot more context.<br>Technology, incentives, and the occasional reality check.</small></div></section>
<section class="lead-grid" aria-label="Lead signal and briefing"><article class="lead-article"><div><div class="section-kicker">The lead / {e(featured["category"])}</div>{demo_tag(featured)}<h2><a href="stories/{e(featured["slug"])}/">{e(featured["title"])}</a></h2><p>{e(featured["summary"])}</p>{strength(featured)}<div style="margin-top:17px">{meta(featured)}</div><a class="read-link" href="stories/{e(featured["slug"])}/">Read the {"demonstration" if featured["status"] == "demo" else "analysis"} →</a></div><div class="lead-art">{ART}</div></article><aside class="briefing"><h2>The short version / {"Demo desk" if data["publication"]["mode"] == "demo" else "Briefing"}</h2><ol>{briefing}</ol></aside></section>
<section id="signal-map" class="map-section" aria-labelledby="map-title"><div class="section-heading"><h2 id="map-title">The Signal Map <span aria-hidden="true">↗</span></h2><p>{"ILLUSTRATIVE MOVEMENT / NOT LIVE DATA" if demo_map else "EDITORIAL DIRECTIONS / NOT QUANTITATIVE SCORES"}</p></div><p class="map-intro">{e(data["signalMap"]["note"])} Select “Why this direction” to see each rationale.</p><div class="signal-map">{"".join(items)}</div><div class="map-legend"><span>↑ Increasing</span><span>↑↑ Stronger directional emphasis</span><span>↓ Decreasing</span><span>→ No change assumed</span><span>As of {stamp(data["signalMap"]["asOf"])} · {"Demo" if demo_map else "Editorial assessment"}</span></div></section>
<section id="latest" class="latest" aria-labelledby="latest-title"><div class="section-heading"><h2 id="latest-title">Latest Signals</h2><p>Context before conclusions.</p></div><div class="filter-top"><p id="result-count" class="result-count" role="status" data-edition-label="{'demonstration edition' if data['publication']['mode'] == 'demo' else 'publication'}">{len(stories)} signals · {"demonstration edition" if data["publication"]["mode"] == "demo" else "publication"}</p><label class="search" data-search hidden for="story-search">FIND A SIGNAL <input id="story-search" type="search" placeholder="Search topics or headlines"></label></div><div class="filters" data-filters aria-label="Filter stories" hidden>{filter_html}</div><noscript><p class="map-intro">All stories are shown below. Enable JavaScript to filter or search.</p></noscript><div class="stories">{"".join(article_item(s, i + 1) for i, s in enumerate(stories))}</div><div id="empty-state" class="empty-state" hidden><p>No signals match this combination. Try another category or search.</p><button id="reset-filters" type="button">Clear filters</button></div></section>
<section class="weekly" aria-labelledby="weekly-title"><div><span class="section-kicker">One edition. A wider lens.</span><h2 id="weekly-title">Weekly<br>Signal.</h2><span class="label">{"Demonstration issue" if weekly["status"] == "demo" else "Weekly edition"} / {stamp(weekly["date"])}</span></div><div><h3>{e(weekly["title"])}</h3><p>{e(weekly["intro"])}</p><a href="weekly/{e(weekly["slug"])}/">Read the weekly edition ↗</a></div></section>
<section class="principles" aria-label="Editorial principles"><div><h3>Facts get sources.</h3><p>Verified reporting belongs in its own lane. These launch scenarios contain no verified news claims.</p></div><div><h3>Predictions stay conditional.</h3><p>An interesting possibility is not an inevitable future. Look for assumptions and uncertainty.</p></div><div><h3>Judgment, not a magic score.</h3><p>Noise, Interesting, Important, Structural Shift. Qualitative labels, with room to change our minds.</p></div></section></main>''' + footer("./")

def section(key, title, content, label):
    return f'<section id="{key}"><span class="section-index">{e(label)}</span><h2>{e(title)}</h2>{content}</section>'

def paragraph(text):
    return f'<p>{e(text)}</p>'

def story_page(story, data, version):
    prefix = "../../"
    demo = story["status"] == "demo"
    note = '<strong>Editorial demonstration, not a news report.</strong> This story uses a fictional premise to demonstrate the format. Its signal label is illustrative; none of the events or outcomes below are being asserted as current facts.' if demo else '<strong>Reported signal.</strong> Source-backed facts are separated from interpretation and conditional outlook.'
    toc = "".join(f'<li><a href="#{key}">{i:02d} / {e(title)}</a></li>' for i, (key, title) in enumerate(SECTIONS, 1))
    if story["facts"]:
        facts = '<ul>' + "".join('<li>' + e(f["text"]) + " " + " ".join(f'<a href="#source-{e(sid)}">[{e(sid)}]</a>' for sid in f["sourceIds"]) + '</li>' for f in story["facts"]) + '</ul>'
    else:
        facts = '<div class="fact-box"><p><strong>No verified news facts are asserted.</strong> The premise below is invented. The remaining sections show how facts and interpretation would be separated in a future reported story.</p></div>'
    facts += f'<div class="scenario-box"><strong>{"Hypothetical premise" if demo else "Reporting context"}</strong><p>{e(story["scenario"])}</p></div>'
    body = section("facts", "Verified facts", facts, "01 / Evidence boundary")
    body += section("changed", "What actually changed", paragraph(story["changed"]), "02 / " + ("Within this fictional scenario" if demo else "Observed change"))
    body += section("why", "Why it matters", paragraph(story["whyItMatters"]), "03 / Interpretation")
    body += section("technical", "Technical implications", paragraph(story["technicalImpact"]), "04 / Engineering analysis")
    body += section("business", "Business implications", paragraph(story["businessImpact"]), "05 / Potential beneficiaries & pressure")
    body += section("outlook", "Where this could be going", '<div class="outlook-block"><span class="section-index">Conditional outlook · Not a fact</span>' + paragraph(story["outlook"]) + '</div>', "06 / Possibility, not certainty")
    body += section("uncertainties", "Risks & uncertainties", '<ul>' + "".join(f'<li>{e(x)}</li>' for x in story["uncertainties"]) + '</ul>', "07 / What could change the picture")
    body += section("analysis", "The AI Signal take", '<div class="analysis-block">' + paragraph(story["analysis"]) + '</div>', "08 / Editorial analysis")
    sources = paragraph(story["sourceNote"])
    if story["sources"]:
        sources += '<ol>' + "".join(f'<li id="source-{e(s["id"])}"><a href="{e(s["url"])}">{e(s["title"])}</a> — {e(s["publisher"])}. Accessed {e(s["accessedAt"])}.</li>' for s in story["sources"]) + '</ol>'
    sources += f'<p class="small">Published <time datetime="{e(story["publishedAt"])}">{stamp(story["publishedAt"])}</time> · Last updated <time datetime="{e(story["updatedAt"])}">{stamp(story["updatedAt"])}</time><br>By {e(story["author"])}. {"AI-assisted demonstration content; no real-world claim verification is implied." if demo else "Editorial review recorded in the source data."}<br><a href="../../content/publication.json">View structured content</a> · <a href="../../about/">Read the editorial method</a></p>'
    body += section("sources", "Sources & publication record", sources, "09 / Provenance")
    concept = '<figure class="concept"><div class="flow"><span>Evidence</span><b aria-hidden="true">→</b><span>Changed capability</span><b aria-hidden="true">→</b><span>Conditional impact</span></div><figcaption>Reading lens: establish what is supported before interpreting what it might mean. Conceptual diagram, not experimental data.</figcaption></figure>'
    related = [s for s in data["stories"] if s["status"] != "draft" and s["id"] != story["id"]][:2]
    return header(story["title"], ("Editorial demonstration. " if demo else "") + story["summary"], prefix, BASE + "stories/" + story["slug"] + "/", data, version) + f'''
<main id="main"><div class="breadcrumbs"><a href="../../">AI Signal</a> / <a href="../../?category={e(story["category"])}#latest">{e(story["category"])}</a> / {"Demonstration" if demo else "Signal"}</div>
<header class="article-header"><div class="flags"><span class="label">{e(story["category"])} / {e(story["topic"])}</span>{strength(story)}{demo_tag(story)}</div><h1>{e(story["title"])}</h1><p class="article-dek">{e(story["summary"])}</p><div class="meta"><span>By {e(story["author"])}</span><span>Published {stamp(story["publishedAt"])}</span><span>Updated {stamp(story["updatedAt"])}</span><span>{read_minutes(story)} min read</span></div></header>
<div class="demonstration">{note}</div><div class="article-layout"><nav class="article-toc" aria-label="Story sections"><strong>The reading path</strong><ol>{toc}</ol></nav><article class="article-body">{concept}{body}</article></div><section class="related"><h2>Keep following the thread.</h2><div class="related-links">{"".join(f'<a href="../{e(s["slug"])}/">{e(s["title"])} ↗</a>' for s in related)}</div></section></main>''' + footer(prefix)

def weekly_page(data, version):
    weekly = data["weekly"]
    stories = {s["id"]: s for s in data["stories"]}
    blocks = "".join(f'<li><span class="label">{e(stories[sid]["category"])} / {e(stories[sid]["signal"])}</span><h2><a href="../../stories/{e(sid)}/">{e(stories[sid]["title"])}</a></h2><p>{e(stories[sid]["summary"])}</p></li>' for sid in weekly["storyIds"])
    return header("Weekly Signal: " + weekly["title"], weekly["intro"], "../../", BASE + "weekly/" + weekly["slug"] + "/", data, version) + f'''<main id="main" class="narrow"><p class="section-kicker">Weekly Signal / {stamp(weekly["date"])} / {e(weekly["status"])}</p><h1>{e(weekly["title"])}</h1><div class="demonstration">{e(weekly["intro"])}</div><h2>The connecting thread</h2><p>{e(weekly["theme"])}</p><ol class="weekly-stories">{blocks}</ol><h2>What we would watch next</h2><p class="small">Questions for future reporting, not predictions or current claims.</p><ul>{"".join(f'<li>{e(x)}</li>' for x in weekly["watchNext"])}</ul><p>{e(weekly["closing"])}</p><p class="small">Published and updated {stamp(weekly["date"])}. AI-assisted editorial demonstration. Sources are listed on each linked story; this edition makes no independent news claims.</p></main>''' + footer("../../")

def about_page(data, version):
    return header("The editorial method", "How AI Signal separates evidence, interpretation, and outlook.", "../", BASE + "about/", data, version) + '''<main id="main" class="narrow"><p class="section-kicker">A note from the desk</p><h1>Interesting is not the same as true.</h1><p>AI Signal is a publication within Dugi Research Lab. Its purpose is to make technical change understandable without flattening every announcement into a breakthrough—or dismissing every ambitious idea as hype.</p><div class="demonstration"><strong>Launch edition: demonstration content.</strong> The initial stories are fictional editorial exercises created with AI assistance. They do not report current events, quote real people, or assign ratings to real companies. Map directions are examples.</div><h2>Three distinct kinds of statement</h2><ol><li><strong>Verified facts:</strong> statements tied to identifiable sources, with verification dates. A source's claim is not automatically independent proof.</li><li><strong>Interpretation:</strong> technical and business implications, with the reasoning and assumptions visible.</li><li><strong>Outlook:</strong> conditional possibilities and what would need to happen for them to become plausible. Never presented as an observed outcome.</li></ol><h2>Signal strength is editorial judgment.</h2><p>These labels describe our assessment of significance. They are not a measurement, a confidence percentage, or investment advice.</p><ul><li><strong>Noise:</strong> insufficient evidence or little actionable change in the story as presented. Not a claim that an idea or researcher has no value.</li><li><strong>Interesting:</strong> a development or question worth investigating; practical significance remains unclear.</li><li><strong>Important:</strong> a material change for an identifiable set of users, if supported by the evidence.</li><li><strong>Structural Shift:</strong> a potential change in the constraints or incentives shaping a wider system. A strong label that requires a clear argument.</li></ul><h2>The Signal Map is directional.</h2><p>Every arrow names a dimension, supplies a rationale, and links to relevant coverage where available. Rising governance requirements and falling inference costs refer to different things. They cannot be combined into a single score. The launch map is entirely illustrative.</p><h2>Before a real story is published</h2><ol><li>Collect primary sources and preserve their dates and provenance.</li><li>Separate the reported event from claims made by the source.</li><li>Verify the fact statements and document what remains uncertain.</li><li>Write analysis and outlook in their own fields.</li><li>Record human editorial approval, then build and review the resulting page.</li></ol><p>The builder requires sources, linked fact records, verification dates, and recorded approval before a story can be marked as published reporting. A machine can validate those fields; it cannot establish that a human actually did the review.</p><h2>Corrections and ownership</h2><p>Dugi Selmanaj maintains the publication. Future factual corrections should identify what changed and why in the article, update its last-updated date, and retain the repository history. To flag an issue, use the <a href="https://github.com/ddugi/ddugi.github.io/issues">publication repository</a>.</p><h2>A static publication, for now.</h2><p>Stories are stored as structured JSON and transformed into standalone HTML. Reading does not require JavaScript; search and filters use a small local script. No news collector, model pipeline, subscriber database, analytics, or scheduled publication is running.</p><p class="small">This site has no application tracking or form submission. GitHub Pages may keep ordinary hosting request logs. <a href="../content/publication.json">Read the content JSON</a> · <a href="https://github.com/ddugi/ddugi.github.io/tree/main/ai-signal">Inspect the source</a>.</p></main>''' + footer("../")

def build(data=None):
    data = validate(data if data is not None else json.loads(SOURCE.read_text(encoding="utf-8")))
    version = hashlib.sha256((ROOT / "assets/signal.css").read_bytes() + (ROOT / "assets/signal.js").read_bytes()).hexdigest()[:12]
    pages = {"index.html": home(data, version), "about/index.html": about_page(data, version), f'weekly/{data["weekly"]["slug"]}/index.html': weekly_page(data, version)}
    for story in data["stories"]:
        if story["status"] != "draft":
            pages[f'stories/{story["slug"]}/index.html'] = story_page(story, data, version)
    return pages

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Validate content and ensure generated pages are up to date")
    args = parser.parse_args()
    pages = build()
    manifest = ROOT / "generated.json"
    old = json.loads(manifest.read_text()) if manifest.exists() else []
    if args.check:
        for path, content in pages.items():
            require((ROOT / path).is_file() and (ROOT / path).read_text(encoding="utf-8") == content, "Generated page is stale: " + path)
        require(sorted(old) == sorted(pages), "Generated manifest is stale")
        print(f"PASS: content validation and {len(pages)} generated pages are current.")
        return
    # Only remove files previously recorded as generated inside this publication.
    for path in set(old) - set(pages):
        require(re.fullmatch(r"(?:stories/[a-z0-9-]+/|weekly/\d{4}-\d{2}-\d{2}/)?index\.html|about/index\.html", path), "Unsafe generated path")
        target = ROOT / path
        if target.is_file():
            target.unlink()
    for path, content in pages.items():
        target = ROOT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    manifest.write_text(json.dumps(sorted(pages), indent=2) + "\n", encoding="utf-8")
    print(f"Built {len(pages)} pages from {SOURCE.relative_to(ROOT)}.")

if __name__ == "__main__":
    main()
