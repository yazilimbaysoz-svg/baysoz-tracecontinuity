# Changelog — Baysöz Labs <baysozlabs@proton.me>

All notable changes to this project are documented here. This project follows semantic versioning.

## [1.0.0] — 2026-11-24

### Added

- OTLP/JSON span ingestion with typed attribute decoding, status/kind normalization, events, links, resource attributes, and W3C context observations.
- Identity rules `DOC001`, `ID001`–`ID005` for IDs, duplicates, and trace flag bytes.
- Span-graph rules `GR001`–`GR008` for orphans, roots, cycles, depth, duration, and causality with configurable clock skew.
- Context rules `CX001`–`CX011` for W3C header grammar, anchoring, sampled flags, tracestate, baggage, links, and trace-wide sampling consistency.
- Semantic-convention rules `SC001`–`SC008` for HTTP/RPC/DB attributes, error typing, legacy keys, and naming.
- Deterministic text, JSON, and SARIF 2.1.0 reports with a central rule catalog.
- Python 3.13+ library API, console entry point, policy overrides, stdin support, and CI exit codes.
- Enterprise documentation, MIT license, and pinned-action CI workflow.
- Full attribution to **Baysöz Labs <baysozlabs@proton.me>** in all public files and CLI output.

### Security

- Zero runtime dependencies; no network calls, subprocesses, dynamic evaluation, or local LLM usage.
- All third-party GitHub Actions pinned to immutable commit SHAs.

— Baysöz Labs <baysozlabs@proton.me>
