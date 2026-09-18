# AI Signal

A distinct static editorial publication at https://ddugi.github.io/ai-signal/.

## Content, not hand-written articles

`content/publication.json` is the editorial source of truth. It contains publication metadata, story records, map rationales and a weekly edition. `content/schema.json` documents the format using JSON Schema 2020-12.

`scripts/build.py` generates the homepage, seven initial story pages, the weekly edition and editorial-method page. All generated HTML is committed so the existing GitHub Pages branch deployment needs no new workflow or package installation.

Do not edit generated HTML directly.

## Edit and publish

From the repository root:

```sh
python3 ai-signal/scripts/build.py
python3 ai-signal/scripts/test_build.py
python3 ai-signal/scripts/build.py --check
```

Then inspect the pages, commit the content and generated files together, and push to the Pages branch. Preview with `python3 -m http.server 8000` from the repository root.

Python 3.9+ and its standard library are sufficient. Reading works without JavaScript. Search/category filtering is a progressive enhancement; the map uses native HTML disclosure controls. Asset URLs are content-hashed to prevent stale-script behavior after deployment.

## Story record

- Identity: `id`, `slug`, `title`, `summary`, `topic`, `category`, `author`.
- Lifecycle: `status` (demo, draft, published), `publishedAt`, `updatedAt`, `review`.
- Significance: `signal` (Noise, Interesting, Important, Structural Shift). This is qualitative judgment, never a numeric confidence or investment score.
- Evidence: `facts` with text, sourceIds and verifiedAt; `sources` with id, title, publisher, HTTPS URL, source date or null, and access date.
- Narrative: `scenario`, `changed`, `whyItMatters`, `technicalImpact`, `businessImpact`, `outlook`, `uncertainties`, `analysis`, `sourceNote`.
- Presentation: `featured` and `visual` (reserved for future data-driven illustrations). Reading time is calculated from content at 220 words/minute.

For a demonstration, facts must be empty. Fictional premises go in scenario. Every demonstration is labeled on the homepage and story page.
Drafts are excluded from generated pages and must not be referenced by the map or weekly edition.

For real reporting, set status to published only after verification and human review. The builder requires nonempty facts and sources, resolved fact citations, verification dates and review status approved with reviewer/date. These are structural checks, not an independent claim that review occurred. The reviewer is responsible for accuracy.

The current publication mode is demo. For a fully real edition, set publication.mode to live after replacing demonstrations with approved stories. Update edition/date and map/weekly status together. The launch-method page explains the original demo edition and can be revised when editorial policy changes.

## Signal Map

Every entry has area, direction, dimension, rationale and an optional storyId. Directions are up, up-strong, down or flat. They refer to the named dimension, so a decrease in inference cost is distinct from a decrease in capability. All launch arrows are illustrative.

An editorial map requires linked story evidence for every area. Do not turn qualitative arrows into fabricated numerical scores. As-of date and status are visible.

## Initial edition

Seven fictional editorial exercises, no current events or fabricated quotes:
- Agents and delegation boundaries
- Inference economics
- Model evaluation
- Robotics operations
- Enterprise workflow adoption
- Agent authorization
- Research transparency

Weekly Signal connects six of these exercises and labels its watch list as questions. No email capture or subscription service is present.

## Future ingestion boundary

Sources → collection → deduplication → fact extraction → verification → analysis draft → human approval → article JSON → build → GitHub Pages.

No part of the ingestion or automated analysis pipeline is enabled here. Future tooling should write drafts to this content contract, preserve provenance, and pass the same validation and editorial review before publication.

## Safety and privacy

Text is HTML-escaped. Slugs and source URLs are validated. No third-party fonts, analytics, model API calls, browser storage, user accounts, or backend. GitHub Pages may keep ordinary hosting request logs. Generated-file cleanup is restricted to the recorded generated manifest inside this publication.

## Checks

Tests cover publication approval gates, resolved sources, unsafe URLs/slugs, duplicate records, draft exclusion, escaped content, derived reading time, internal links, unique IDs and page headings. `--check` rejects stale generated files.

