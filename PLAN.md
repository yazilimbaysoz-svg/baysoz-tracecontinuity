# Plan — Baysöz Labs <baysozlabs@proton.me>

## Phase 0 — Market validation (COMPLETE)

- Inspected all 27 entries in `existing-repos.json` and excluded covered domains.
- Mined live star trends and open issues with `gh search repos` / `gh search issues`.
- Selected distributed-trace continuity and W3C propagation conformance as the unoccupied seam. Evidence is recorded in `docs/MARKET_RESEARCH.md`.

## Phase 1 — Core data model (COMPLETE)

- OTLP/JSON envelope support: `resourceSpans`, `spans`, scope/resource attributes, typed values, aliases.
- W3C observation ingestion: `traceparent`, `tracestate`, `baggage`.
- Immutable dataclasses with source pointers; structural errors separated from findable data defects.

## Phase 2 — Rule engines (COMPLETE)

- Identity rules: `DOC001`, `ID001`–`ID005`.
- Graph rules: `GR001`–`GR008`, including iterative cycle and depth handling.
- Context rules: `CX001`–`CX011`, including baggage continuity and sampling agreement.
- Semantic-convention rules: `SC001`–`SC008`.

## Phase 3 — Reporting and CLI (COMPLETE)

- Text, JSON, and SARIF 2.1.0 renderers with central rule catalog.
- `--config`, `--max-depth`, `--skew-tolerance-ns`, `--fail-on`, `--format`, `--output`, stdin support.
- Deterministic exit codes and attribution in `--version`, `--help`, and every report.

## Phase 4 — Enterprise documentation and CI (COMPLETE)

- Required files: `README.md`, `PLAN.md`, `SECURITY.md`, `CHANGELOG.md`, `LICENSE`, `pyproject.toml`, CI workflow, ignore rules, architecture, market research.
- CI pins actions to immutable SHAs and runs tests, ruff, Semgrep, and a live CLI smoke audit.
- MIT license and authorship credited to **Baysöz Labs <baysozlabs@proton.me>**.

## Phase 5 — Quality gates (COMPLETE)

1. `uv venv && uv pip install -e . && uv pip install pytest`
2. `uv run pytest -q`
3. `ruff check --select E,F,W,S,B .`
4. `semgrep --config p/default --error .`

Each gate must be green with zero findings before release. Any regression reopens this phase.

## Phase 6 — Supreme Grand Jury Tribunal (COMPLETE)

The tribunal executed the installed CLI and library against the clean and adversarial examples plus hand-built malformed inputs, checked SARIF validity, and verified that all 33 emitted rule IDs exist in the catalog and map to real input defects. Determinism was confirmed across 25 CLI render cases with different `PYTHONHASHSEED` values. Verdict: **unanimous PASS** from all three jurors.

## Phase 7 — Publication (COMPLETE)

- Created public repository `yazilimbaysoz-svg/baysoz-tracecontinuity` with a crisp attributed description and nine topics.
- Pushed source from the workspace and emitted the showcase result JSON without touching other showcase files.
- Repository URL: <https://github.com/yazilimbaysoz-svg/baysoz-tracecontinuity>.

## Post-release backlog

- Additional semantic-convention packs (messaging, LLM, database metrics).
- JSON Schema for policy files and fixture-based golden SARIF snapshots.
- Optional compressed OTLP ingest adapter; still offline and service-free.

— Baysöz Labs <baysozlabs@proton.me>
