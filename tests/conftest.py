"""Shared adversarial fixtures Baysöz Labs <baysozlabs@proton.me>."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from baysoz_tracecontinuity import audit_document
from baysoz_tracecontinuity.report import AuditReport

ROOT = Path(__file__).resolve().parents[1]
TRACE_ID = "a" * 32
OTHER_TRACE_ID = "b" * 32


def make_span(span_id: str, parent: str = "", **overrides: Any) -> dict[str, Any]:
    span: dict[str, Any] = {
        "traceId": TRACE_ID,
        "spanId": span_id,
        "parentSpanId": parent or "0" * 16,
        "name": "operation",
        "kind": "SPAN_KIND_INTERNAL",
        "startTimeUnixNano": 1_000,
        "endTimeUnixNano": 2_000,
        "flags": 1,
        "attributes": {},
    }
    span.update(overrides)
    return span


def make_document(
    spans: list[dict[str, Any]],
    observations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    document: dict[str, Any] = {"spans": spans}
    if observations is not None:
        document["contextObservations"] = observations
    return document


def audit(document: dict[str, Any], **kwargs: Any) -> AuditReport:
    return audit_document(document, source="tests", **kwargs)


def rule_ids(report: AuditReport) -> set[str]:
    return {finding.rule_id for finding in report.findings}


@pytest.fixture
def fixture_document() -> Any:
    def load(name: str) -> dict[str, Any]:
        return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))

    return load
