"""Span-graph causality analysis Baysöz Labs <baysozlabs@proton.me>."""

from __future__ import annotations

from collections import defaultdict

from .model import Span, TraceDocument
from .policy import Policy
from .report import RULE_CATALOG, Finding

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


def group_by_trace(document: TraceDocument) -> dict[str, list[Span]]:
    groups: dict[str, list[Span]] = defaultdict(list)
    for span in document.spans:
        groups[span.trace_id].append(span)
    return dict(groups)


def _unique_spans(spans: list[Span]) -> dict[str, Span]:
    result: dict[str, Span] = {}
    for span in spans:
        result.setdefault(span.span_id, span)
    return result


def _find_cycle(nodes: dict[str, Span]) -> str | None:
    settled: set[str] = set()
    for start in nodes:
        if start in settled:
            continue
        chain: list[str] = []
        visiting: set[str] = set()
        current = start
        while current in nodes and current not in settled:
            if current in visiting:
                return current
            visiting.add(current)
            chain.append(current)
            current = nodes[current].parent_span_id
        settled.update(chain)
    return None


def _depths(nodes: dict[str, Span]) -> dict[str, int]:
    memo: dict[str, int] = {}
    for start in nodes:
        if start in memo:
            continue
        chain: list[str] = []
        visiting: set[str] = set()
        current = start
        while current in nodes and current not in memo:
            if current in visiting:
                break
            visiting.add(current)
            chain.append(current)
            current = nodes[current].parent_span_id
        depth = memo.get(current, 0)
        for node in reversed(chain):
            depth += 1
            memo[node] = depth
    return memo


def audit_graph(document: TraceDocument, policy: Policy) -> list[Finding]:
    findings: list[Finding] = []
    for trace_id, spans in group_by_trace(document).items():
        nodes = _unique_spans(spans)
        anchor = spans[0].path
        roots = [span for span in spans if not span.parent_span_id or span.parent_span_id == _ZERO_SPAN_ID]
        if policy.enabled("GR002") and len(roots) > 1:
            findings.append(_finding("GR002", f"trace has {len(roots)} root spans", anchor, trace_id, roots[0].span_id))
        if policy.enabled("GR001"):
            for span in spans:
                parent = span.parent_span_id
                if parent and parent != _ZERO_SPAN_ID and parent not in nodes:
                    findings.append(
                        _finding(
                            "GR001", f"parent {parent} is absent from the export", span.path, trace_id, span.span_id
                        )
                    )
        cycle = _find_cycle(nodes) if policy.enabled("GR003") else None
        if cycle is not None:
            findings.append(_finding("GR003", f"cycle detected at span {cycle}", nodes[cycle].path, trace_id, cycle))
        if policy.enabled("GR004") and cycle is None:
            for span_id, depth in _depths(nodes).items():
                if depth > policy.max_depth:
                    findings.append(
                        _finding(
                            "GR004",
                            f"depth {depth} exceeds limit {policy.max_depth}",
                            nodes[span_id].path,
                            trace_id,
                            span_id,
                        )
                    )
        for span in spans:
            if policy.enabled("GR006") and (span.start_ns is None or span.end_ns is None):
                findings.append(
                    _finding(
                        "GR006", "startTimeUnixNano or endTimeUnixNano is missing", span.path, trace_id, span.span_id
                    )
                )
                continue
            if span.start_ns is None or span.end_ns is None:
                continue
            if policy.enabled("GR005") and span.end_ns < span.start_ns:
                findings.append(
                    _finding(
                        "GR005",
                        f"duration is {span.end_ns - span.start_ns} ns",
                        span.path,
                        trace_id,
                        span.span_id,
                    )
                )
            parent = nodes.get(span.parent_span_id)
            if parent is None or parent.start_ns is None or parent.end_ns is None or cycle is not None:
                continue
            tolerance = policy.skew_tolerance_ns
            if policy.enabled("GR007") and span.start_ns < parent.start_ns - tolerance:
                findings.append(
                    _finding(
                        "GR007",
                        f"child starts {parent.start_ns - span.start_ns} ns before parent",
                        span.path,
                        trace_id,
                        span.span_id,
                    )
                )
            if policy.enabled("GR008") and span.end_ns > parent.end_ns + tolerance:
                findings.append(
                    _finding(
                        "GR008",
                        f"child ends {span.end_ns - parent.end_ns} ns after parent",
                        span.path,
                        trace_id,
                        span.span_id,
                    )
                )
    return findings
