"""OpenTelemetry semantic-convention checks Baysöz Labs <baysozlabs@proton.me>."""

from __future__ import annotations

import re

from .model import TraceDocument
from .policy import Policy
from .report import RULE_CATALOG, Finding

_METHOD = re.compile(r"^[A-Z][A-Z0-9!#$%&'*+.^_`|~-]{0,31}$")
_LITERAL = re.compile(r"['\"](?:[0-9]+|[A-Za-z0-9_%]{4,})['\"]")
_LEGACY_KEYS = ("http.method", "http.status_code", "http.url", "db.instance")


def _finding(rule_id: str, message: str, pointer: str, trace_id: str, span_id: str) -> Finding:
    return Finding(
        rule_id=rule_id,
        severity=RULE_CATALOG[rule_id].severity,
        message=message,
        pointer=pointer,
        trace_id=trace_id,
        span_id=span_id,
    )


def _first(attributes: dict[str, object], *keys: str) -> tuple[str, object] | None:
    for key in keys:
        if key in attributes:
            return key, attributes[key]
    return None


def _status_code(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value, 10)
    return None


def audit_semconv(document: TraceDocument, policy: Policy) -> list[Finding]:
    findings: list[Finding] = []
    for span in document.spans:
        attrs = span.attributes
        if policy.enabled("SC008") and not span.name.strip():
            findings.append(_finding("SC008", "span name is empty", span.path, span.trace_id, span.span_id))
        legacy = [key for key in _LEGACY_KEYS if key in attrs]
        if policy.enabled("SC007") and legacy:
            findings.append(
                _finding("SC007", f"deprecated keys: {', '.join(legacy)}", span.path, span.trace_id, span.span_id)
            )
        if span.kind in {"client", "server"}:
            has_protocol = any(
                key.startswith("http.") or key.startswith("rpc.") or key.startswith("db.") for key in attrs
            )
            if policy.enabled("SC001") and not has_protocol:
                findings.append(
                    _finding(
                        "SC001",
                        f"{span.kind} span has no HTTP, RPC, or DB attributes",
                        span.path,
                        span.trace_id,
                        span.span_id,
                    )
                )
        method = _first(attrs, "http.request.method", "http.method")
        if method is not None and policy.enabled("SC002"):
            value = method[1]
            if not isinstance(value, str) or not _METHOD.fullmatch(value):
                findings.append(
                    _finding(
                        "SC002",
                        f"HTTP method {value!r} is not an uppercase token",
                        span.path,
                        span.trace_id,
                        span.span_id,
                    )
                )
        status = _first(attrs, "http.response.status_code", "http.status_code")
        if status is not None and policy.enabled("SC003"):
            code = _status_code(status[1])
            if code is None or not 100 <= code <= 599:
                findings.append(
                    _finding(
                        "SC003",
                        f"HTTP status {status[1]!r} is outside 100..599",
                        span.path,
                        span.trace_id,
                        span.span_id,
                    )
                )
        if "rpc.system" in attrs and policy.enabled("SC004"):
            missing = [key for key in ("rpc.service", "rpc.method") if key not in attrs]
            if missing:
                findings.append(
                    _finding(
                        "SC004", f"RPC span is missing {', '.join(missing)}", span.path, span.trace_id, span.span_id
                    )
                )
        statement = attrs.get("db.statement")
        if policy.enabled("SC005") and isinstance(statement, str) and _LITERAL.search(statement):
            findings.append(
                _finding("SC005", "db.statement embeds a quoted literal", span.path, span.trace_id, span.span_id)
            )
        has_error_type = any(key in attrs for key in ("error.type", "exception.type")) or any(
            "exception.type" in event.attributes for event in span.events
        )
        if span.status_code == "ERROR" and policy.require_error_type and not has_error_type:
            if policy.enabled("SC006"):
                findings.append(
                    _finding(
                        "SC006",
                        "ERROR status has no error.type or exception event",
                        span.path,
                        span.trace_id,
                        span.span_id,
                    )
                )
    return findings
