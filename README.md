# Dugi Research Lab

Static GitHub Pages research hub at https://ddugi.github.io/.

## Publications and tools
- /ai-signal/ — distinct editorial publication, JSON-driven demonstration stories, Signal Map and Weekly Signal. See ai-signal/README.md for authoring and build commands.
- / — research hub and roadmap
- /ai-readiness/ — five-dimension, equal-weight evidence self-assessment
- /gitops-maturity/ — cumulative Level 0–5 evidence gates
- /ai-agent-security/ — deterministic trust-boundary simulation
- /ai-infrastructure-report/ — proposed study, with no empirical findings
- /data/measurement-template.csv — header-only measurement schema

## Run and deploy
Run `python3 -m http.server 8000` from this directory to preview locally. Deploy `main` at the repository root using GitHub Pages' branch source. `.nojekyll` keeps this plain static content. Pull requests and pushes run the quality workflow in `.github/workflows/quality.yml`.

For production governance, protect `main`, require pull requests, require the `validate` job, prevent force pushes, and enable private vulnerability reporting in repository settings. These server-side controls cannot be established by files alone.

## Data and privacy
No backend, analytics, external fonts, third-party scripts, or model calls. Answers live in page memory and are cleared on reload. Users can export JSON results. GitHub Pages may retain normal hosting request logs. Do not add confidential organizational data to exported files intended for public sharing.

## Scoring
AI readiness: round(100 × sum(scores) / 15). All five scores must be integers from 0 through 3. Unknown scores zero; it is not inferred evidence of failure.
GitOps: highest consecutive gate scoring 3, starting at gate 1. A gap prevents higher levels even if subsequent controls are present. These models are author-defined drafts, not validated indexes or certifications.

## Simulation
Three fixed scenarios: injection, excessive privilege, and identity scope. Task-boundary enforcement blocks first; capability policy blocks second; approval pauses third; with none enabled the UI marks the action as simulated execution. Audit changes visibility, not prevention. No actions are executed.

## Authoring
Add each future publication under its own slug/index.html and link it from the root. Preserve visible status labels, source attribution and assumptions. Never turn hypothetical benchmark values into reported findings. The initial site and content were developed with AI assistance.

## Ownership and policy
Source code is MIT-licensed. Editorial text, research, diagrams, datasets, and branding remain all rights reserved unless explicitly stated otherwise; see `LICENSE` and `NOTICE.md`. Repository governance, security reporting, and contribution terms are documented in `GOVERNANCE.md`, `SECURITY.md`, and `CONTRIBUTING.md`. AI Signal publishes editorial, correction, and privacy policies under `/ai-signal/policies/`.

## Inspiration and references
Publication information architecture was inspired by https://harnesstax.github.io/ without copying its design, text or results. Primary references (NIST, Google SRE, OpenTelemetry, OpenGitOps and OWASP) are linked on the relevant pages.
