# Architecture — Baysöz Labs <baysozlabs@proton.me>

## 1. System boundary

`baysoz-tracecontinuity` is a pure, offline validator. It reads a JSON document from a path or stdin, produces a deterministic report, and exits with a CI-friendly status. There are no daemons, databases, brokers, HTTP calls, model inference, or hidden state.

```text
  OTLP/JSON export ─┐
                    ├─> model.parse_document ─> TraceDocument ─> four rule engines
  W3C observations ─┘                                   │
                                                        ├─> identity.audit_identity
                                                        ├─> graph.audit_graph
                                                        ├─> context.audit_context
                                                        └─> semconv.audit_semconv
                                                                  │
                                                                  v
                                          audit.audit_trace_document (sort + summary)
                                                                  │
                                        ┌─────────────────────────┼─────────────────────────┐
                                        v                         v                         v
                                    text report               JSON report              SARIF 2.1.0
                                        └─────────────────────────┼─────────────────────────┘
                                                                  v
                                                   CLI exit code 0 / 1 / 2
```

## 2. Module responsibilities

| Module | Responsibility |
| --- | --- |
| `model.py` | Normalizes OTLP/JSON attributes, status codes, kinds, events, links, timestamps, and W3C observations into immutable dataclasses. Structural errors only; field-level corruption becomes a finding. |
| `identity.py` | Validates trace/span/parent IDs, duplicate span IDs, and trace flag bytes. Reports `DOC001` for empty input. |
| `graph.py` | Groups spans into traces, resolves unique parent maps, detects orphans/multiple roots/cycles, computes iterative depth, and checks duration and parent/child causality with skew tolerance. |
| `context.py` | Parses W3C `traceparent`, `tracestate`, and `baggage`; anchors headers to real spans; checks sampled-flag agreement, link integrity, trace-wide sampling consistency, and baggage continuity. |
| `semconv.py` | Checks stable OpenTelemetry HTTP/RPC/DB semantic conventions, legacy keys, error typing, and span naming. |
| `policy.py` | Immutable policy object: `max_depth`, `skew_tolerance_ns`, `require_error_type`, `disabled_rules`. Loaded from JSON or CLI flags. |
| `report.py` | Central rule catalog, severity ordering, `AuditReport`, and text/JSON/SARIF renderers. Every SARIF run names **Baysöz Labs <baysozlabs@proton.me>** as the tool organization. |
| `audit.py` | Orchestration, deterministic sort by (severity, rule, pointer, message), and summary aggregation. |
| `cli.py` | `argparse` contract, stdin/file input, renderer choice, output file, failure policy, and documented exit codes. |

## 3. Data model

`TraceDocument` is `tuple[Span, ...]` plus `tuple[ContextObservation, ...]`. Each `Span` carries normalized IDs, kind, timestamps (nullable), decoded attributes, flags, status, events, links, instrumentation scope, resource attributes, and a JSON-pointer-like source path such as `resourceSpans[0].scopeSpans[0].spans[2]`. Findings reference that path instead of line numbers, so reports remain stable across formatter changes.

OTLP typed attributes (`stringValue`, `intValue`, `boolValue`, `arrayValue`, `kvlistValue`) and plain maps are both accepted. Upper/lower-case field aliases (`traceId`/`trace_id`, `spanId`/`span_id`) are normalized.

## 4. Key algorithms

- **Cycle detection**: per-trace single-parent chains are walked with a `settled` set and per-walk `visiting` set. A revisit in the active chain is a cycle. No Python recursion is used, so deep adversarial chains cannot raise `RecursionError`.
- **Depth computation**: iterative memoization over parent chains; skipped when a cycle is present to avoid meaningless depths.
- **Clock skew**: a child starting before its parent, or ending after it, is reported only when the delta exceeds `skew_tolerance_ns` (default 1 ms). This distinguishes real causality breaks from nanosecond jitter.
- **Baggage continuity**: baggage keys from headers and span attributes are indexed by `(trace_id, span_id)`; a child missing a parent key yields an advisory `CX008`.
- **Trace sampling consistency**: sampled bits across all spans in a trace are collected; mixed bits yield `CX011`.
- **Determinism**: no clocks, randomness, environment-dependent formatting, or network calls. Rule order, grouping order, and sort keys are explicit.

Complexity is O(N + E) for N spans and E parent/link edges, with O(N) memory.

## 5. Reporting and CI contract

Findings are typed with stable rule IDs (`ID*`, `GR*`, `CX*`, `SC*`, `DOC*`), a default severity from the central catalog, a human-readable message, and source/span/trace scope. SARIF 2.1.0 maps each finding to a rule descriptor with help text and a logical location. Summary counts and verdict are embedded in JSON/SARIF properties.

Exit codes: `0` = gate pass, `1` = failure at the selected `--fail-on` threshold, `2` = invalid document/policy/path. The CI workflow pins all third-party actions to full commit SHAs, runs 64 unit/integration tests, ruff (`E,F,W,S,B`), Semgrep `p/default`, and a live CLI SARIF smoke audit.

## 6. Limitations and extension points

- The oracle validates exported evidence; it cannot prove a propagator works in a process that emitted nothing.
- `SC005` is a heuristic advisory for quoted literals in SQL-like statements; parameterized statements pass.
- New rules are added by extending `_RULE_DATA` and one engine module; tests assert catalog coverage.
- Custom organizational conventions can be layered through `policy.disabled_rules` and future rule packs without changing the core model.

— Baysöz Labs <baysozlabs@proton.me>
