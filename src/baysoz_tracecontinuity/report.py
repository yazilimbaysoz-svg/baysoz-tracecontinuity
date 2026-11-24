"""Deterministic findings and SARIF/JSON/text rendering by Baysöz Labs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

ATTRIBUTION = "Baysöz Labs <baysozlabs@proton.me>"
PROJECT = "baysoz-tracecontinuity"
VERSION = "1.0.0"
HOMEPAGE = "https://github.com/yazilimbaysoz-svg/baysoz-tracecontinuity"
SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"

SEVERITY_ORDER = {"error": 0, "warning": 1, "note": 2}


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    message: str
    pointer: str
    trace_id: str = ""
    span_id: str = ""


@dataclass(frozen=True)
class RuleSpec:
    title: str
    explanation: str
    severity: str


_RULE_DATA: dict[str, tuple[str, str, str]] = {
    "DOC001": ("Empty trace document", "No spans were found in the document.", "error"),
    "ID001": ("Invalid trace identifier", "A trace id must be 32 lowercase hex digits and non-zero.", "error"),
    "ID002": ("Invalid span identifier", "A span id must be 16 lowercase hex digits and non-zero.", "error"),
    "ID003": ("Invalid parent identifier", "A parent span id must be 16 lowercase hex digits.", "error"),
    "ID004": ("Duplicate span identifier", "A span id may occur only once inside a trace.", "error"),
    "ID005": ("Invalid trace flags", "Trace flags must be an integer from 0 to 255 or a hex byte.", "error"),
    "GR001": ("Orphan span", "The parent span is absent from the same trace export.", "error"),
    "GR002": ("Multiple root spans", "A trace export contains more than one root span.", "warning"),
    "GR003": ("Parent cycle", "Parent references form a cycle, so causality is unresolved.", "error"),
    "GR004": ("Trace depth exceeded", "The parent chain exceeds the configured policy limit.", "warning"),
    "GR005": ("Negative span duration", "The end timestamp precedes the start timestamp.", "error"),
    "GR006": ("Missing timestamps", "Start and end timestamps are required for causality checks.", "error"),
    "GR007": ("Child starts before parent", "A child starts before its parent beyond the skew tolerance.", "warning"),
    "GR008": ("Child outlives parent", "A child ends after its parent beyond the skew tolerance.", "warning"),
    "CX001": ("Malformed traceparent", "W3C traceparent must use version 00 with 32/16/2 hex fields.", "error"),
    "CX002": ("Zero context identifier", "W3C trace-id and span-id fields must not be all zeros.", "error"),
    "CX003": ("Unanchored observation", "A context references a trace absent from the export.", "warning"),
    "CX004": ("Context parent missing", "The traceparent parent-id matches no span in the trace.", "error"),
    "CX005": ("Sampled flag disagreement", "The propagated sampled flag disagrees with the span.", "warning"),
    "CX006": ("Malformed tracestate", "tracestate violates W3C size, key, or value constraints.", "warning"),
    "CX007": ("Malformed baggage", "A baggage member is not a valid key=value pair.", "error"),
    "CX008": ("Baggage key lost", "A parent baggage key is absent on the child.", "warning"),
    "CX009": ("Invalid link identifier", "A span link has an invalid trace id or span id.", "error"),
    "CX010": ("Link sampling mismatch", "A same-trace link disagrees with its span sampled flag.", "warning"),
    "CX011": ("Inconsistent trace sampling", "Spans in one trace carry different sampled flags.", "warning"),
    "SC001": ("Protocol attributes missing", "Client and server spans need HTTP, RPC, or DB attributes.", "error"),
    "SC002": ("Invalid HTTP method", "The HTTP request method must be an uppercase token.", "error"),
    "SC003": ("Invalid HTTP status", "The HTTP response status must be an integer from 100 to 599.", "error"),
    "SC004": ("Incomplete RPC attributes", "RPC spans require rpc.system, rpc.service, and rpc.method.", "warning"),
    "SC005": ("Literal in db.statement", "A database statement embeds a quoted literal.", "warning"),
    "SC006": ("Error status without error.type", "An ERROR status needs error.type or an exception event.", "warning"),
    "SC007": (
        "Legacy semantic convention key",
        "A deprecated attribute key needs migration to stable names.",
        "warning",
    ),
    "SC008": ("Missing span name", "Every span should carry a non-empty operation name.", "warning"),
}

RULE_CATALOG: dict[str, RuleSpec] = {
    rule_id: RuleSpec(title=title, explanation=explanation, severity=severity)
    for rule_id, (title, explanation, severity) in _RULE_DATA.items()
}


@dataclass(frozen=True)
class AuditReport:
    source: str
    summary: dict[str, Any]
    findings: tuple[Finding, ...]

    @property
    def passed(self) -> bool:
        return self.summary["errors"] == 0

    @property
    def verdict(self) -> str:
        return "PASS" if self.passed else "FAIL"


def to_json(report: AuditReport) -> str:
    payload = {
        "tool": f"{PROJECT} {VERSION}",
        "attribution": ATTRIBUTION,
        "source": report.source,
        "summary": report.summary,
        "findings": [
            {
                "rule_id": finding.rule_id,
                "severity": finding.severity,
                "message": finding.message,
                "pointer": finding.pointer,
                "trace_id": finding.trace_id,
                "span_id": finding.span_id,
            }
            for finding in report.findings
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def to_sarif(report: AuditReport) -> str:
    used_rules = sorted({finding.rule_id for finding in report.findings})
    rules = []
    for rule_id in used_rules:
        spec = RULE_CATALOG[rule_id]
        rules.append(
            {
                "id": rule_id,
                "name": spec.title.replace(" ", ""),
                "shortDescription": {"text": spec.title},
                "fullDescription": {"text": spec.explanation},
                "help": {"text": f"{spec.explanation} Attributed to {ATTRIBUTION}."},
                "defaultConfiguration": {"level": spec.severity},
            }
        )
    results = []
    for finding in report.findings:
        results.append(
            {
                "ruleId": finding.rule_id,
                "level": finding.severity,
                "message": {"text": finding.message},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": report.source},
                            "region": {"startLine": 1},
                        },
                        "logicalLocations": [{"name": finding.pointer, "kind": "other"}],
                    }
                ],
                "properties": {
                    "pointer": finding.pointer,
                    "traceId": finding.trace_id,
                    "spanId": finding.span_id,
                },
            }
        )
    payload = {
        "$schema": SARIF_SCHEMA,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": PROJECT,
                        "organization": ATTRIBUTION,
                        "version": VERSION,
                        "informationUri": HOMEPAGE,
                        "rules": rules,
                    }
                },
                "results": results,
                "properties": {
                    "attribution": ATTRIBUTION,
                    "summary": report.summary,
                },
            }
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def to_text(report: AuditReport) -> str:
    summary = report.summary
    lines = [
        f"{PROJECT} audit — {ATTRIBUTION}",
        f"source: {report.source}",
        (f"spans: {summary['spans']} | traces: {summary['traces']} | observations: {summary['observations']}"),
    ]
    if not report.findings:
        lines.append("findings: none")
    for finding in report.findings:
        scope = ""
        if finding.trace_id:
            scope = f" trace={finding.trace_id}"
        if finding.span_id:
            scope += f" span={finding.span_id}"
        lines.append(f"{finding.severity.upper():7} {finding.rule_id} {finding.message} [{finding.pointer}{scope}]")
    lines.append(
        f"verdict: {report.verdict} "
        f"({summary['errors']} errors, {summary['warnings']} warnings, {summary['notes']} notes)"
    )
    return "\n".join(lines) + "\n"
