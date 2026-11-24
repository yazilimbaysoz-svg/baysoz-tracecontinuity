"""Identifier and flag validation Baysöz Labs <baysozlabs@proton.me>."""

from __future__ import annotations

import re

from .model import TraceDocument
from .policy import Policy
from .report import RULE_CATALOG, Finding

_TRACE_ID = re.compile(r"^[0-9a-f]{32}$")
_SPAN_ID = re.compile(r"^[0-9a-f]{16}$")
_ZERO_TRACE_ID = "0" * 32
_ZERO_SPAN_ID = "0" * 16


def _finding(rule_id: str, message: str, pointer: str, trace_id: str, span_id: str) -> Finding:
    return Finding(
        rule_id=rule_id,
        severity=RULE_CATALOG[rule_id].severity,
        message=message,
        pointer=pointer,
        trace_id=trace_id,
        span_id=span_id,
    )


def audit_identity(document: TraceDocument, policy: Policy) -> list[Finding]:
    findings: list[Finding] = []
    if not document.spans and policy.enabled("DOC001"):
        findings.append(_finding("DOC001", "the document contains no spans", "<root>", "", ""))
    seen: dict[tuple[str, str], str] = {}
    for span in document.spans:
        if policy.enabled("ID001") and (not _TRACE_ID.fullmatch(span.trace_id) or span.trace_id == _ZERO_TRACE_ID):
            findings.append(
                _finding(
                    "ID001", "traceId is not 32 lowercase hex digits or is zero", span.path, span.trace_id, span.span_id
                )
            )
        if policy.enabled("ID002") and (not _SPAN_ID.fullmatch(span.span_id) or span.span_id == _ZERO_SPAN_ID):
            findings.append(
                _finding(
                    "ID002", "spanId is not 16 lowercase hex digits or is zero", span.path, span.trace_id, span.span_id
                )
            )
        if policy.enabled("ID003") and span.parent_span_id and not _SPAN_ID.fullmatch(span.parent_span_id):
            findings.append(
                _finding("ID003", "parentSpanId is not 16 lowercase hex digits", span.path, span.trace_id, span.span_id)
            )
        if policy.enabled("ID005") and (span.flags < 0 or span.flags > 255):
            findings.append(
                _finding(
                    "ID005", "trace flags are outside the byte range 0..255", span.path, span.trace_id, span.span_id
                )
            )
        key = (span.trace_id, span.span_id)
        if policy.enabled("ID004") and key in seen:
            findings.append(
                _finding(
                    "ID004",
                    f"spanId first appeared at {seen[key]}",
                    span.path,
                    span.trace_id,
                    span.span_id,
                )
            )
        else:
            seen[key] = span.path
    return findings
