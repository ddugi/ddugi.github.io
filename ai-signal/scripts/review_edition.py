#!/usr/bin/env python3
"""Validate an unpublished edition and build an ignored local review bundle."""
from pathlib import Path
import argparse
import html
import json
import re
import shutil
from datetime import date
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "content" / "review" / "edition-01.json"
DEFAULT_OUTPUT = ROOT / ".review" / "edition-01"
CATEGORIES = {"Models", "Agents", "Infrastructure", "Robotics", "Enterprise AI", "Security & Governance", "Research"}
SIGNALS = {"Noise", "Interesting", "Important", "Structural Shift"}
DIRECTIONS = {"up", "up-strong", "down", "flat"}
CHECKS = ("factCheck", "rightsCheck", "fairnessCheck", "copyCheck")

def require(condition, message):
    if not condition:
        raise ValueError(message)

def valid_date(value):
    try:
        return isinstance(value, str) and date.fromisoformat(value).isoformat() == value
    except (TypeError, ValueError):
        return False

def e(value):
    return html.escape(str(value), quote=True)

def validate(data, ready=False):
    require(data.get("schemaVersion") == 1, "Unsupported review schema")
    edition = data["edition"]
    require(edition["status"] == "editorial-review", "Edition must remain in editorial-review")
    require(valid_date(edition["preparedAt"]), "Invalid preparedAt date")
    require(edition["publicationDate"] is None or valid_date(edition["publicationDate"]), "Invalid publication date")
    require(3 <= len(data["stories"]) <= 5, "A review edition requires 3–5 stories")
    ids = set()
    featured = 0
    for story in data["stories"]:
        require(story["id"] == story["slug"] and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", story["slug"]), "Unsafe or mismatched story ID")
        require(story["id"] not in ids, "Duplicate story ID")
        ids.add(story["id"])
        require(story["status"] == "draft", "Review stories must remain drafts")
        require(story["category"] in CATEGORIES and story["signal"] in SIGNALS, "Unknown category or signal")
        require(valid_date(story["publishedAt"]) and valid_date(story["updatedAt"]), "Invalid exact publication date")
        require(story["updatedAt"] >= story["publishedAt"], "Story update predates source publication")
        require(story["facts"] and story["sources"], "Drafts require facts and sources")
        source_ids = set()
        for source in story["sources"]:
            require(source["kind"] == "primary", "Every initial source must be marked primary")
            require(source["id"] not in source_ids, "Duplicate source ID")
            source_ids.add(source["id"])
            parsed = urlsplit(source["url"])
            require(parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password, "Sources must use public HTTPS URLs")
            require(valid_date(source["publishedAt"]) and valid_date(source["accessedAt"]), "Sources require exact publication and access dates")
        for fact in story["facts"]:
            require(fact["text"].strip() and fact["sourceIds"] and all(x in source_ids for x in fact["sourceIds"]), "Every fact must resolve to a source")
            require(valid_date(fact["verifiedAt"]), "Every fact requires a verification date")
        require(story["uncertainties"], "Every story needs uncertainties or counterarguments")
        require(story["outlook"].startswith("Conditional outlook:"), "Outlook must be explicitly conditional")
        review = story["review"]
        require(review["status"] in ("pending", "approved"), "Invalid review status")
        require(all(isinstance(review[x], bool) for x in CHECKS), "Review checks must be booleans")
        if ready:
            require(review["status"] == "approved", f'{story["id"]}: approval missing')
            require(all(review[x] for x in CHECKS), f'{story["id"]}: review checklist incomplete')
            require(review["reviewer"] and valid_date(review["reviewedAt"]), f'{story["id"]}: reviewer record incomplete')
        featured += int(story["featured"])
    require(featured == 1, "Exactly one review story must be featured")
    areas = set()
    for movement in data["signalMapChanges"]:
        require(movement["area"] not in areas, "Duplicate Signal Map area")
        areas.add(movement["area"])
        require(movement["direction"] in DIRECTIONS, "Invalid map direction")
        require(movement["storyId"] in ids, "Every map movement must resolve to an edition story")
        require(movement["dimension"].strip() and movement["rationale"].strip(), "Map movement requires dimension and rationale")
    require(data["weekly"]["watchNext"], "Weekly review needs explicit watch questions")
    if ready:
        require(valid_date(edition["publicationDate"]), "Approved edition requires publicationDate")
    return data

def page_shell(title, body, depth, home):
    prefix = "../" * depth
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>{e(title)} — AI Signal review</title><link rel="stylesheet" href="{prefix}assets/signal.css"></head><body><a class="skip" href="#main">Skip to content</a><div class="shell"><header class="masthead"><a class="wordmark" href="{home}"><span class="asterisk" aria-hidden="true">✳</span>AI Signal</a><strong class="demo-tag">LOCAL EDITORIAL REVIEW · NOT PUBLISHED</strong></header><main id="main" class="narrow">{body}</main></div></body></html>'''

def render_story(story):
    facts = "".join(f'<li>{e(f["text"])} <small>Sources: {e(", ".join(f["sourceIds"]))} · verified {e(f["verifiedAt"])}</small></li>' for f in story["facts"])
    uncertainties = "".join(f"<li>{e(x)}</li>" for x in story["uncertainties"])
    sources = "".join(f'<li id="source-{e(s["id"])}"><a href="{e(s["url"])}">{e(s["title"])}</a> — {e(s["publisher"])} · published {e(s["publishedAt"])} · accessed {e(s["accessedAt"])} · primary source</li>' for s in story["sources"])
    review = story["review"]
    checks = "".join(f'<li>{"✓" if review[x] else "○"} {e(x)}</li>' for x in CHECKS)
    sections = [
        ("Verified facts", f"<ul>{facts}</ul><p class='small'>{e(story['sourceNote'])}</p>"),
        ("What actually changed", f"<p>{e(story['changed'])}</p>"),
        ("Why it matters", f"<p>{e(story['whyItMatters'])}</p>"),
        ("Technical implications", f"<p>{e(story['technicalImpact'])}</p>"),
        ("Business implications", f"<p>{e(story['businessImpact'])}</p>"),
        ("Where this could be going · Conditional outlook", f"<div class='outlook-block'><p>{e(story['outlook'])}</p></div>"),
        ("Risks, uncertainty & counterarguments", f"<ul>{uncertainties}</ul>"),
        ("Editorial analysis", f"<div class='analysis-block'><p>{e(story['analysis'])}</p></div>"),
        ("Primary sources", f"<ol>{sources}</ol>"),
        ("Human review gate", f"<p>Status: <strong>{e(review['status'])}</strong></p><ul>{checks}</ul><p>{e(review['notes'])}</p>")
    ]
    body = f'''<p class="section-kicker">{e(story["category"])} / {e(story["signal"])} / Source publication {e(story["publishedAt"])}</p><h1>{e(story["title"])}</h1><p class="intro">{e(story["summary"])}</p><div class="demonstration"><strong>Editorial draft.</strong> This page is generated for human review and is not part of the public edition.</div>'''
    body += "".join(f"<section><h2>{e(title)}</h2>{content}</section>" for title, content in sections)
    return page_shell(story["title"], body, 3, "../../index.html")

def render_index(data):
    cards = "".join(f'''<article class="story-item"><span class="label">{e(s["category"])} · {e(s["signal"])}</span><h2><a href="stories/{e(s["slug"])}/">{e(s["title"])}</a></h2><p>{e(s["summary"])}</p><p class="small">Source publication: {e(s["publishedAt"])} · Review: {e(s["review"]["status"])}</p></article>''' for s in data["stories"])
    moves = "".join(f'<li><strong>{e(m["area"])}</strong> {e(m["direction"])} · {e(m["dimension"])} — {e(m["rationale"])} <small>Story: {e(m["storyId"])}</small></li>' for m in data["signalMapChanges"])
    body = f'''<p class="section-kicker">Edition {e(data["edition"]["id"])} / Prepared {e(data["edition"]["preparedAt"])}</p><h1>{e(data["edition"]["title"])}</h1><div class="demonstration"><strong>Review bundle.</strong> {e(data["edition"]["note"])}</div><section><h2>Story review queue</h2><div class="stories">{cards}</div></section><section><h2>Proposed Signal Map changes</h2><p>Every proposal below resolves to a story in this review edition. Promotion remains blocked until all stories are approved.</p><ul>{moves}</ul></section><section><h2>Approval procedure</h2><ol><li>Open each story and verify every fact against its linked primary source.</li><li>Review rights, fairness, uncertainty, headline, analysis, and tone.</li><li>Set the four checklist fields to true, status to approved, and record reviewer and reviewedAt.</li><li>Set edition.publicationDate.</li><li>Run the ready check and promotion preview before changing the live edition.</li></ol><pre>python3 ai-signal/scripts/review_edition.py --ready</pre></section>'''
    return page_shell("Edition 01 review", body, 1, "index.html")

def build(data, output):
    if output.exists():
        shutil.rmtree(output)
    for story in data["stories"]:
        target = output / "stories" / story["slug"] / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_story(story), encoding="utf-8")
    (output / "index.html").write_text(render_index(data), encoding="utf-8")
    assets = output.parent / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "assets" / "signal.css", assets / "signal.css")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--ready", action="store_true", help="Require completed human approval records")
    args = parser.parse_args()
    data = validate(json.loads(args.source.read_text(encoding="utf-8")), ready=args.ready)
    build(data, args.output)
    print(f'PASS: validated {len(data["stories"])} review drafts and built {args.output}')

if __name__ == "__main__":
    main()
