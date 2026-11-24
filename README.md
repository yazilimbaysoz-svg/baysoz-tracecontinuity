[![CI](https://github.com/yazilimbaysoz-svg/baysoz-tracecontinuity/actions/workflows/ci.yml/badge.svg)](https://github.com/yazilimbaysoz-svg/baysoz-tracecontinuity/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)
[![Baysöz Labs](https://img.shields.io/badge/attribution-Bays%C3%B6z%20Labs-7d3cff.svg)](mailto:baysozlabs@proton.me)

# baysoz-tracecontinuity

**Deterministic offline distributed-trace continuity and W3C context-propagation conformance oracle with SARIF CI gates.**
Built by **Baysöz Labs <baysozlabs@proton.me>**.

Most tracing outages are not backend outages; they are broken parent links, dropped propagators, inconsistent sampling decisions, or context that never reaches the next hop. This tool audits the trace evidence you already export — before it reaches Jaeger, Tempo, or an OTel collector — and turns structural defects into deterministic CI failures. It is a production engineering tool for `systems-observability`, not a toy utility: no services, no network, no local LLMs, zero runtime dependencies.

## Why it exists

- Jaeger issue activity shows recurring sampling-parameter drift and stale adaptive-sampling state ([examples](docs/MARKET_RESEARCH.md)).
- Tempo openly tracks structural queries for **incomplete traces** and UTF-8-safe attribute handling failures.
- Existing Baysöz Labs tools cover Collector config, PromQL, cardinality, routing, and supply chain — but **none validates emitted span graphs or W3C propagation headers**. See [market research](docs/MARKET_RESEARCH.md).

## Install

Requires Python 3.13+ and `uv`.

```bash
uv pip install git+https://github.com/yazilimbaysoz-svg/baysoz-tracecontinuity.git
```

From source:

```bash
git clone https://github.com/yazilimbaysoz-svg/baysoz-tracecontinuity.git
cd baysoz-tracecontinuity
uv venv
uv pip install -e .
```

## Architecture

```text
OTLP/JSON spans + W3C observations
        -> model.parse_document
        -> identity | graph | context | semconv rule engines
        -> audit summary + deterministic sort
        -> text | JSON | SARIF 2.1.0
        -> exit 0 (pass), 1 (gate failure), 2 (invalid input)
```

The four engines check:

| Family | Coverage |
| --- | --- |
| `DOC/ID` | empty documents, lowercase-hex IDs, zero IDs, duplicate span IDs, trace flag bytes |
| `GR` | orphan spans, multiple roots, cycles, bounded depth, negative duration, missing timestamps, parent/child clock skew |
| `CX` | W3C `traceparent` grammar, zero IDs, anchoring, sampled-flag agreement, `tracestate`, `baggage`, links, trace-wide sampling consistency |
| `SC` | HTTP/RPC/DB semantic conventions, error typing, legacy keys, span naming |

All findings are deterministic, catalogued by stable rule ID, and carry a source pointer such as `spans[2]`. Full design notes: [ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Real CLI output

Version:

```console
$ uv run baysoz-tracecontinuity --version
baysoz-tracecontinuity 1.0.0 — Baysöz Labs <baysozlabs@proton.me>
```

Help:

```console
$ uv run baysoz-tracecontinuity --help
usage: baysoz-tracecontinuity [-h] [--version] [--format {json,sarif,text}]
                              [--output PATH] [--config PATH]
                              [--max-depth MAX_DEPTH]
                              [--skew-tolerance-ns SKEW_TOLERANCE_NS]
                              [--fail-on {error,warning,none}]
                              input

Deterministic offline distributed-trace continuity and W3C propagation conformance oracle. Built by Baysöz Labs <baysozlabs@proton.me>.

positional arguments:
  input                 OTLP/JSON trace document path, or - for stdin

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  --format {json,sarif,text}
                        report format
  --output PATH         write the report to a file instead of stdout
  --config PATH         JSON policy override file
  --max-depth MAX_DEPTH
                        maximum allowed parent-chain depth
  --skew-tolerance-ns SKEW_TOLERANCE_NS
                        allowed parent/child clock skew in nanoseconds
  --fail-on {error,warning,none}
                        minimum severity that fails the CI gate

Attribution: Baysöz Labs <baysozlabs@proton.me>. Exit codes: 0 pass, 1 gate failure, 2 invalid input. No network access, no external services.
```

Well-formed export:

```console
$ uv run baysoz-tracecontinuity examples/clean-pipeline.json
baysoz-tracecontinuity audit — Baysöz Labs <baysozlabs@proton.me>
source: examples/clean-pipeline.json
spans: 2 | traces: 1 | observations: 1
findings: none
verdict: PASS (0 errors, 0 warnings, 0 notes)
```

Adversarial export (shown with `--fail-on none` so the report can be displayed without failing the shell):

```console
$ uv run baysoz-tracecontinuity examples/broken-pipeline.json --fail-on none
baysoz-tracecontinuity audit — Baysöz Labs <baysozlabs@proton.me>
source: examples/broken-pipeline.json
spans: 4 | traces: 1 | observations: 2
ERROR   CX002 traceparent contains an all-zero identifier [contextObservations[1]]
ERROR   GR001 parent 9999999999999999 is absent from the export [spans[2] trace=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa span=3333333333333333]
ERROR   GR005 duration is -10000000 ns [spans[2] trace=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa span=3333333333333333]
ERROR   ID004 spanId first appeared at spans[1] [spans[3] trace=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa span=2222222222222222]
ERROR   SC001 client span has no HTTP, RPC, or DB attributes [spans[3] trace=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa span=2222222222222222]
ERROR   SC002 HTTP method 'get' is not an uppercase token [spans[1] trace=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa span=2222222222222222]
ERROR   SC003 HTTP status 700 is outside 100..599 [spans[1] trace=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa span=2222222222222222]
WARNING CX008 baggage keys lost on child: tenant [spans[1] trace=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa span=2222222222222222]
WARNING CX008 baggage keys lost on child: tenant [spans[3] trace=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa span=2222222222222222]
WARNING CX011 trace contains both sampled and unsampled spans [spans[0] trace=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa]
WARNING SC005 db.statement embeds a quoted literal [spans[2] trace=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa span=3333333333333333]
WARNING SC006 ERROR status has no error.type or exception event [spans[1] trace=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa span=2222222222222222]
verdict: FAIL (7 errors, 5 warnings, 0 notes)
```

CI integration with SARIF:

```bash
uv run baysoz-tracecontinuity export.json --format sarif --output trace-audit.sarif
cat export.json | uv run baysoz-tracecontinuity - --format json
```

## Python API

```python
from baysoz_tracecontinuity import Policy, audit_document

report = audit_document(document, policy=Policy(skew_tolerance_ns=5_000_000))
print(report.verdict, report.summary["errors"])
```

## Quality gates

```bash
uv venv
uv pip install -e .
uv pip install pytest
uv run pytest -q
ruff check --select E,F,W,S,B .
semgrep --config p/default --error .
```

Documentation: [PLAN.md](PLAN.md) · [SECURITY.md](SECURITY.md) · [CHANGELOG.md](CHANGELOG.md) · [MARKET_RESEARCH.md](docs/MARKET_RESEARCH.md)

**Baysöz Labs <baysozlabs@proton.me>** — https://github.com/yazilimbaysoz-svg
