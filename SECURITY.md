# Security Policy — Baysöz Labs <baysozlabs@proton.me>

## 1. Trust model

`baysoz-tracecontinuity` treats all input as untrusted. It performs no network I/O, no shell execution, no dynamic code evaluation, and no service discovery. The only filesystem operations are reading the input/policy paths and optionally writing the requested report path. The process never starts subprocesses and never loads local or remote LLMs.

Input is accepted from CI fixtures, OTLP file exports, and stdin. Malformed fields become findings rather than exceptions; only unreadable paths, invalid JSON, invalid policy shapes, and non-document JSON shapes produce exit code 2.

## 2. Data handling

- Findings may contain trace IDs, span IDs, and source attribute values (for example an invalid HTTP method). Treat SARIF/JSON reports as sensitive telemetry artifacts and store them accordingly.
- The tool does not invent values: messages are generated exclusively from observed input fields and deterministic rule templates.
- The literal-value heuristic (`SC005`) is designed to reveal possible PII leakage in `db.statement`; it reports only the presence of a quoted literal, never the literal itself.
- No telemetry is transmitted. There is no analytics, telemetry, or auto-update path in the software.

## 3. Supply chain

- Runtime dependencies: **none** beyond Python 3.13+ standard library.
- Build backend: Hatchling. Dev tools: pytest, ruff, Semgrep.
- CI uses full 40-character commit SHAs for all third-party GitHub Actions to prevent mutable-tag repointing.
- Quality gates are mandatory: unit/integration tests, `ruff check --select E,F,W,S,B .`, and `semgrep --config p/default --error .`.

## 4. Safe usage guidance

- Run the oracle on sanitized or test traces when possible; redact production baggage values before exporting fixtures into public repositories.
- Use `--output` to write reports into controlled artifact storage; GitHub code scanning consumers should scope permissions to `contents: read`.
- Pin the installed version and review the SARIF rule catalog when upgrading, because rule IDs are part of the CI contract.

## 5. Reporting vulnerabilities

Report security issues privately to **baysozlabs@proton.me** with a minimal reproducer, affected version, and impact assessment. Do not open a public issue for undisclosed vulnerabilities. Baysöz Labs acknowledges reports and coordinates disclosure with the reporter.

— Baysöz Labs <baysozlabs@proton.me>
