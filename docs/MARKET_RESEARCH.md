# Market Research — Baysöz Labs <baysozlabs@proton.me>

## 1. Method and evidence provenance

This research was mined live on **2026-11-24** with the GitHub CLI (`gh search repos`, `gh search issues`) from the authenticated account `yazilimbaysoz-svg`. Repository star counts and issue titles below are captured observations, not estimates. A subsequent batch of searches hit the unauthenticated GitHub search rate limit (HTTP 403); no data is inferred beyond the successful responses.

The local corpus `/home/runner/work/_temp/existing-repos.json` contains 27 prior Baysöz Labs projects. It was inspected in full to enforce strict non-redundancy.

## 2. Ecosystem gravity (live observations)

| Repository (captured 2026-11-24) | Stars | Why it matters |
| --- | ---: | --- |
| `netdata/netdata` | 81,599 | Full-stack observability; traces are a first-class signal next to metrics and logs. |
| `SigNoz/signoz` | 32,722 | OTel-native APM, explicitly serving teams and their AI agents. |
| `jaegertracing/jaeger` | 23,441 | CNCF tracing control plane; sampling configuration is a recurring production failure source. |
| `openobserve/openobserve` | 23,168 | Single-binary alternative with traces plus SLO and LLM observability. |
| `ClickHouse/ClickStack` | 10,073 | Session replay + traces + logs on ClickHouse; high ingest volumes. |
| `open-telemetry/opentelemetry-collector` | 7,800 | The de facto telemetry routing layer; configuration is validated elsewhere, not emitted span semantics. |
| `grafana/tempo` | 5,588 | High-volume trace backend; incomplete traces are a structural query problem. |
| `open-telemetry/opentelemetry-collector-contrib` | 5,064 | Broad processor/receiver ecosystem where context can be dropped between hops. |
| `open-telemetry/opentelemetry-python` | 2,717 | Reference SDK whose propagation behavior applications depend on. |

The trend is unambiguous: the market moved from "collect traces" to **OTel-native, high-volume, multi-signal platforms**. The expensive failure mode is no longer storage; it is silently broken context before ingest.

## 3. Live pain signals (open issues)

Sampling and context propagation dominate the traced production incidents observed:

- `jaegertracing/jaeger#10023` — *File sampling provider serves out-of-range probabilistic and ratelimiting params* — <https://github.com/jaegertracing/jaeger/issues/10023>
- `jaegertracing/jaeger#10148` — *Adaptive sampling leader keeps leadership after its lease expires when lock renewal keeps failing* — <https://github.com/jaegertracing/jaeger/issues/10148>
- `jaegertracing/jaeger#9826` — *Reload resets sampling strategies to defaults on a transient source error* — <https://github.com/jaegertracing/jaeger/issues/9826>
- `jaegertracing/jaeger#9953` — *jaeger validate accepts non-positive adaptive sampling settings that then fail at startup* — <https://github.com/jaegertracing/jaeger/issues/9953>
- `jaegertracing/jaeger#9880` — *ES sampling store can return stale probabilities when the index holds more docs than max_doc_count* — <https://github.com/jaegertracing/jaeger/issues/9880>
- `jaegertracing/jaeger#9794` — *503 from the sampling strategies URL stops reloading or resets all strategies* — <https://github.com/jaegertracing/jaeger/issues/9794>
- `jaegertracing/jaeger#9833` — *file-based sampling provider never starts auto-reload if the first load returns 503 or null* — <https://github.com/jaegertracing/jaeger/issues/9833>
- `grafana/tempo#8467` — *Distributor attribute truncation is not UTF-8 safe: corrupted parquet rows make entire traces unqueryable* — <https://github.com/grafana/tempo/issues/8467>
- `grafana/tempo#6393` — *Improve structural and root/parent queries on incomplete traces* — <https://github.com/grafana/tempo/issues/6393>
- `open-telemetry/opentelemetry-ebpf-instrumentation` — *Add support for traceparent as X-Amzn-Trace-Id header* (captured via issue search).
- `Arize-ai/openinference` — *semantic-conventions: validate flattened-list leaves in live-check* (captured via issue search).

Synthesis: sampling state drifts at runtime, propagators disagree across languages and proxies, and backends must build expensive structural workarounds for **incomplete traces**. A deterministic pre-ingest oracle that catches orphans, cycles, skew, flag conflicts, and lost baggage converts these production surprises into CI failures.

## 4. Non-redundancy against the 27-repo Baysöz Labs corpus

The corpus already covers adjacent layers: Collector config policy (`baysoz-otelgate`), telemetry cardinality (`baysoz-cardinalis`), PromQL conformance (`baysoz-queryoracle`), SLO burn rules (`baysoz-burnlattice`), Alertmanager routing (`baysoz-alertpath-oracle`), Kubernetes topology gates (`baysoz-netpol-oracle`, `baysoz-routegate`, `baysoz-disruption-oracle`), supply chain (`baysoz-actionlock`, `baysoz-reachoracle`), API/appsec oracles (`bolaforge`, `baysoz-desyncforge`, `baysoz-josegate`, `baysoz-cspforge`), MCP contracts (`baysoz-mcpcontract`), detection-rule parity (`atr-parity-gate`), and log PII masking (`baysoz-logmask`).

**None of them validates the emitted distributed-trace object graph or W3C propagation headers.** This project occupies the missing seam between instrumentation and ingest:

1. It audits spans that already exist (unlike `baysoz-otelgate`, which audits Collector YAML).
2. It audits continuity, causality, and context propagation (unlike `baysoz-cardinalis`, which audits label economics).
3. It is offline and deterministic with SARIF output, requiring no Jaeger, Tempo, Collector, or network service (unlike issue-driven debugging in live backends).
4. It is a CI contract for 2026-2027 polyglot/agentic systems: one broken propagator or one sampling mismatch can invalidate an entire trace despite healthy infrastructure.

## 5. Product definition

`baysoz-tracecontinuity` is a Python 3.13+ CLI and importable library that consumes OTLP/JSON span exports plus optional W3C `traceparent`/`tracestate`/`baggage` observations and emits deterministic findings in text, JSON, or SARIF 2.1.0. It combines four engines:

- **Identity**: lowercase-hex IDs, non-zero IDs, duplicate span IDs, byte-valid trace flags.
- **Graph**: orphans, multiple roots, cycles, bounded depth, duration sanity, parent/child causality with configurable clock-skew tolerance.
- **Context**: W3C header grammar, anchored propagation, sampled-flag agreement, tracestate/baggage grammar, baggage continuity, link validity.
- **Semantics**: stable HTTP/RPC/DB semantic conventions, error typing, legacy key detection.

Rejected alternatives: a backend UI clone (toy/redundant), another YAML linter (redundant with `baysoz-otelgate`), a live sampler service (heavy, non-deterministic), and an LLM-based trace explainer (explicitly out of scope: zero local LLMs, zero heavy services).

## 6. Success criteria

- Zero findings on a well-formed OTel export; reproducible non-zero findings on adversarial exports.
- O(N + E) validation with no recursion-dependent failure on deep chains.
- SARIF consumable by GitHub code scanning and existing Baysöz Labs CI gates.
- 100% attribution to **Baysöz Labs <baysozlabs@proton.me>** in code, docs, metadata, and CLI output.

— Baysöz Labs <baysozlabs@proton.me>
