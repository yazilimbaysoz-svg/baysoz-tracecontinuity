"""W3C propagation checks Baysöz Labs <baysozlabs@proton.me>."""

from __future__ import annotations

import re

from .graph import group_by_trace
from .model import TraceDocument
from .policy import Policy
from .report import RULE_CATALOG, Finding

_TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")
_TRACEPARENT_ANY = re.compile(r"^[0-9a-f]{2}-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})(-.*)?$")
_ZERO_TRACE_ID = "0" * 32
_ZERO_SPAN_ID = "0" * 16
_TOKEN = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")
_SIMPLE_KEY = re.compile(r"^[a-z0-9_*/-]{1,256}$")
_VENDOR_KEY = re.compile(r"^[a-z0-9_-]{1,241}@[a-z0-9_-]{1,256}$")
_STATE_VALUE = re.compile(r"^[\x21\x23-\x2b\x2d-\x3c\x3e-\x7e]{0,256}$")
_TRACE_ID = re.compile(r"^[0-9a-f]{32}$")
_SPAN_ID = re.compile(r"^[0-9a-f]{16}$")


def _finding(rule_id: str, message: str, pointer: str, trace_id: str = "", span_id: str = "") -> Finding:
    return Finding(
        rule_id=rule_id,
        severity=RULE_CATALOG[rule_id].severity,
        message=message,
        pointer=pointer,
        trace_id=trace_id,
        span_id=span_id,
    )


def _baggage_keys(header: str) -> tuple[str, ...] | None:
    if not header:
        return ()
    keys: list[str] = []
    for member in header.split(","):
        pair = member.strip().split(";", 1)[0].strip()
        if "=" not in pair:
            return None
        key = pair.split("=", 1)[0].strip()
        if not _TOKEN.fullmatch(key):
            return None
        keys.append(key)
    return tuple(keys)


def _tracestate_valid(header: str) -> bool:
    if len(header) > 512:
        return False
    if not header:
        return True
    entries = header.split(",")
    if len(entries) > 32:
        return False
    for entry in entries:
        if "=" not in entry:
            return False
        key, value = entry.strip().split("=", 1)
        if not (_SIMPLE_KEY.fullmatch(key) or _VENDOR_KEY.fullmatch(key)):
            return False
        if not _STATE_VALUE.fullmatch(value):
            return False
    return True


def audit_context(document: TraceDocument, policy: Policy) -> list[Finding]:
    findings: list[Finding] = []
    groups = group_by_trace(document)
    nodes_by_trace = {trace_id: {span.span_id: span for span in spans} for trace_id, spans in groups.items()}
    carried: dict[tuple[str, str], set[str]] = {}

    for observation in document.observations:
        traceparent = observation.traceparent
        match = _TRACEPARENT.fullmatch(traceparent)
        if match is None:
            reason = "unsupported version" if _TRACEPARENT_ANY.fullmatch(traceparent) else "invalid format"
            if policy.enabled("CX001"):
                findings.append(_finding("CX001", f"traceparent has {reason}", observation.path))
            continue
        trace_id, parent_id, flags_text = match.groups()
        if trace_id == _ZERO_TRACE_ID or parent_id == _ZERO_SPAN_ID:
            if policy.enabled("CX002"):
                findings.append(_finding("CX002", "traceparent contains an all-zero identifier", observation.path))
            continue
        if policy.enabled("CX006") and not _tracestate_valid(observation.tracestate):
            findings.append(_finding("CX006", "tracestate violates W3C constraints", observation.path))
        keys = _baggage_keys(observation.baggage)
        if keys is None:
            if policy.enabled("CX007"):
                findings.append(_finding("CX007", "baggage header contains an invalid member", observation.path))
        elif keys:
            carried.setdefault((trace_id, parent_id), set()).update(keys)
        if trace_id not in nodes_by_trace:
            if policy.enabled("CX003"):
                findings.append(
                    _finding("CX003", f"context for trace {trace_id} is not anchored in the export", observation.path)
                )
            continue
        parent = nodes_by_trace[trace_id].get(parent_id)
        if parent is None:
            if policy.enabled("CX004"):
                findings.append(
                    _finding(
                        "CX004", f"parent-id {parent_id} is absent from trace {trace_id}", observation.path, trace_id
                    )
                )
            continue
        if policy.enabled("CX005") and (int(flags_text, 16) & 1) != (parent.flags & 1):
            findings.append(
                _finding(
                    "CX005",
                    f"header sampled={int(flags_text, 16) & 1} but span sampled={parent.flags & 1}",
                    observation.path,
                    trace_id,
                    parent_id,
                )
            )

    for span in document.spans:
        baggage = span.attributes.get("baggage")
        if isinstance(baggage, str) and baggage:
            keys = _baggage_keys(baggage)
            if keys is None:
                if policy.enabled("CX007"):
                    findings.append(
                        _finding("CX007", "span baggage attribute is invalid", span.path, span.trace_id, span.span_id)
                    )
            elif keys:
                carried.setdefault((span.trace_id, span.span_id), set()).update(keys)

        for link in span.links:
            if not _TRACE_ID.fullmatch(link.trace_id) or not _SPAN_ID.fullmatch(link.span_id):
                if policy.enabled("CX009"):
                    findings.append(
                        _finding(
                            "CX009",
                            "link identifier is not lowercase hexadecimal",
                            span.path,
                            span.trace_id,
                            span.span_id,
                        )
                    )
            elif policy.enabled("CX010") and link.trace_id == span.trace_id and (link.flags & 1) != (span.flags & 1):
                findings.append(
                    _finding(
                        "CX010",
                        "same-trace link sampled flag differs from span",
                        span.path,
                        span.trace_id,
                        span.span_id,
                    )
                )
    for trace_id, spans in groups.items():
        sampled = {span.flags & 1 for span in spans if 0 <= span.flags <= 255}
        if policy.enabled("CX011") and len(sampled) > 1:
            findings.append(
                _finding("CX011", "trace contains both sampled and unsampled spans", spans[0].path, trace_id)
            )

    for span in document.spans:
        parent_keys = carried.get((span.trace_id, span.parent_span_id), set())
        if not parent_keys or not policy.enabled("CX008"):
            continue
        child_keys = carried.get((span.trace_id, span.span_id), set())
        missing = sorted(parent_keys - child_keys)
        if missing:
            findings.append(
                _finding(
                    "CX008",
                    f"baggage keys lost on child: {', '.join(missing)}",
                    span.path,
                    span.trace_id,
                    span.span_id,
                )
            )
    return findings
