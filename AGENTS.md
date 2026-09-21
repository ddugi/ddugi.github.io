# Dugi Research Lab

This repository publishes the static research hub at <https://ddugi.github.io/>. AI Signal lives under `ai-signal/` and is published at <https://ddugi.github.io/ai-signal/>.

## AI Signal mission

AI Signal identifies meaningful developments across AI, agents, infrastructure, cybersecurity, platform engineering, enterprise AI, governance, and research. It explains what changed, why it matters, what remains uncertain, and what may happen next for engineers, architects, CTOs, founders, and enterprises.

It is an editorial technology publication, not a generic headline aggregator. Prefer a small number of consequential, well-supported signals over broad coverage.

## Source of truth

- Edit `ai-signal/content/publication.json` for publication content.
- Follow `ai-signal/content/schema.json` and the field definitions in `ai-signal/README.md`.
- Read `ai-signal/content/update-state.json` before researching an update.
- Run `ai-signal/scripts/build.py` to generate pages. Never edit generated AI Signal HTML directly.
- Preserve the existing visual design and static GitHub Pages architecture unless the user explicitly requests a redesign.

## “Update AI Signal” workflow

When asked to update AI Signal, complete this workflow.

### 1. Establish the research window

Read `last_successful_update` from `ai-signal/content/update-state.json`.

- When it contains a timestamp, research developments published after that timestamp and through the current run time.
- When it is `null`, this is the first live editorial update. Use the configured `initial_lookback_days`, state the exact date range in the report, and do not imply earlier coverage is complete.
- Treat publication time and event time separately when they differ.

### 2. Discover from primary sources

Prioritize first-party release notes, documentation, research papers, repositories, security advisories, and official company or project announcements from sources such as OpenAI, Anthropic, Google/DeepMind, Microsoft/Azure, AWS, NVIDIA, Meta, GitHub, Hugging Face, major open-source projects, standards bodies, regulators, and relevant research venues.

Secondary reporting may help discovery or provide independent context. It must not replace an available primary source for the central fact.

### 3. Verify

- Never invent an event, date, quote, release, benchmark, metric, source, or implication.
- Open and read every source used for a factual statement.
- Record the exact source title, publisher, HTTPS URL, source publication date when available, access date, and fact verification date.
- Distinguish what the source demonstrably establishes from claims made by the source.
- If the central claim cannot be verified, reject the candidate.
- If sources disagree, report the disagreement or keep the item out of the edition.

### 4. Filter and deduplicate

Accept a candidate only when it materially affects enterprise technology, AI engineering, infrastructure, security, software delivery, governance, or research practice. Reject routine marketing, minor feature announcements, unsupported performance claims, and duplicated coverage.

Search existing story IDs, slugs, titles, facts, sources, and themes before adding a story. Update an existing story when the underlying development materially changed; do not publish a second version of the same signal.

### 5. Write within the existing content model

For each accepted story, populate all fields required by `publication.json` and its schema. Keep these lanes distinct:

1. `facts`: atomic, source-linked verified statements.
2. `changed`: the material delta beyond the announcement wording.
3. `whyItMatters`: the structural significance.
4. `technicalImpact` and `businessImpact`: reasoned implications.
5. `outlook`: explicitly conditional possibilities, never facts.
6. `uncertainties`: meaningful counterarguments, evidence gaps, and failure conditions.
7. `analysis`: concise editorial judgment grounded in the preceding evidence.
8. `sources`: complete provenance and dates.

Use the existing qualitative signal labels only: `Noise`, `Interesting`, `Important`, and `Structural Shift`. Do not add numeric scores, confidence percentages, or invented quantitative precision.

Write concise, direct prose. Remove generic AI language, corporate phrasing, and claims that are stronger than the evidence.

### 6. Detect larger signals

Identify a trend only when multiple independent developments support the same direction. A single story cannot establish an emerging trend.

Every editorial Signal Map movement must reference a published story through `storyId`, name the dimension that moved, and explain the rationale. Do not change an arrow merely to make the map look active.

### 7. Preserve the human review gate

New or materially revised reporting must remain `draft` until the user explicitly approves it for publication.

While preparing drafts:

- do not set `review.status` to `approved`;
- do not invent a reviewer or review date;
- do not change `publication.mode` from `demo` to `live`;
- do not add drafts to the published weekly edition or editorial Signal Map;
- do not advance `last_successful_update`.

After explicit human approval, record the real reviewer and review date, publish the accepted stories, update the edition, weekly issue, and traceable Signal Map together, then run all validation. Advance `last_successful_update` only after the approved commit has passed validation and been successfully published. Record that commit in `last_successful_commit` and the published IDs in `last_published_story_ids`.

### 8. Validate before completing

From the repository root, run:

```sh
python3 ai-signal/scripts/build.py
python3 ai-signal/scripts/test_build.py
python3 ai-signal/scripts/build.py --check
git diff --check
```

Also inspect the generated homepage and every changed story page. Verify dates, source URLs, fact citations, duplicate coverage, internal links, generated output, and the separation of facts, interpretation, and outlook. Do not publish when a check fails.

### 9. Report

Return:

```text
Research window: <exact start> → <exact end>
New draft signals: X
Updated draft signals: X
Rejected candidates: X
Emerging trends detected: X
Human review: REQUIRED/COMPLETE
Build: PASS/FAIL
```

Briefly list the most important additions, why rejected candidates were excluded, and any unresolved uncertainty. Never describe a draft as published.

## Automation boundary

No ingestion, model-analysis, scheduling, or automatic publishing pipeline is active. Do not add one during a normal editorial update. Any future automation must produce drafts, preserve source provenance, pass the same validation, and stop at human approval before publication.
