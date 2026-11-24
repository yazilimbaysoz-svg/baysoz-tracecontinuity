"""Audit orchestration Baysöz Labs <baysozlabs@proton.me>."""

from __future__ import annotations

from typing import Any

from .context import audit_context
from .graph import audit_graph, group_by_trace
from .identity import audit_identity
from .model import TraceDocument, parse_document
from .policy import Policy
from .report import AuditReport, Finding, SEVERITY_ORDER
from .semconv import audit_semconv


def audit_trace_document(
    document: TraceDocument,
    policy: Policy | None = None,
    source: str = "<memory>",
) -> AuditReport:
    active = policy if policy is not None else Policy()
    findings: list[Finding] = []
    for auditor in (audit_identity, audit_graph, audit_context, audit_semconv):
        findings.extend(auditor(document, active))
    findings.sort(key=lambda item: (SEVERITY_ORDER[item.severity], item.rule_id, item.pointer, item.message))
    errors = sum(item.severity == "error" for item in findings)
    warnings = sum(item.severity == "warning" for item in findings)
    notes = len(findings) - errors - warnings
    summary: dict[str, Any] = {
        "spans": len(document.spans),
        "traces": len(group_by_trace(document)),
        "observations": len(document.observations),
        "errors": errors,
        "warnings": warnings,
        "notes": notes,
        "rules_triggered": len({item.rule_id for item in findings}),
    }
    return AuditReport(source=source, summary=summary, findings=tuple(findings))


def audit_document(
    document: Any,
    policy: Policy | None = None,
    source: str = "<memory>",
) -> AuditReport:
    return audit_trace_document(parse_document(document), policy, source)
