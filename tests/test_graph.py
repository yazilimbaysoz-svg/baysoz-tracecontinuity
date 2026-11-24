"""Span-graph rule tests Baysöz Labs <baysozlabs@proton.me>."""

from baysoz_tracecontinuity import Policy

from conftest import audit, make_document, make_span, rule_ids


def test_orphan_span_is_detected() -> None:
    report = audit(make_document([make_span("1" * 16, parent="9" * 16)]))
    assert "GR001" in rule_ids(report)
    assert not report.passed


def test_multiple_roots_are_reported() -> None:
    report = audit(make_document([make_span("1" * 16), make_span("2" * 16)]))
    assert "GR002" in rule_ids(report)


def test_parent_cycle_is_detected_without_hanging() -> None:
    spans = [
        make_span("1" * 16, parent="2" * 16),
        make_span("2" * 16, parent="1" * 16),
    ]
    report = audit(make_document(spans))
    assert "GR003" in rule_ids(report)


def test_depth_policy_is_enforced() -> None:
    spans = []
    previous = "0" * 16
    for index in range(1, 6):
        current = str(index) * 16
        spans.append(make_span(current, parent=previous))
        previous = current
    report = audit(make_document(spans), policy=Policy(max_depth=2))
    assert "GR004" in rule_ids(report)
    assert sum(item.rule_id == "GR004" for item in report.findings) == 3


def test_negative_duration_is_reported() -> None:
    report = audit(make_document([make_span("1" * 16, startTimeUnixNano=2_000, endTimeUnixNano=1_000)]))
    assert "GR005" in rule_ids(report)


def test_missing_timestamps_are_reported() -> None:
    span = make_span("1" * 16)
    del span["startTimeUnixNano"]
    report = audit(make_document([span]))
    assert "GR006" in rule_ids(report)


def test_clock_skew_tolerance_is_configurable() -> None:
    spans = [
        make_span("1" * 16, startTimeUnixNano=1_000, endTimeUnixNano=2_000),
        make_span("2" * 16, parent="1" * 16, startTimeUnixNano=500, endTimeUnixNano=2_500),
    ]
    assert "GR007" not in rule_ids(audit(make_document(spans)))
    strict = audit(make_document(spans), policy=Policy(skew_tolerance_ns=0))
    assert {"GR007", "GR008"} <= rule_ids(strict)


def test_well_formed_causal_chain_passes() -> None:
    spans = [
        make_span("1" * 16, startTimeUnixNano=1_000, endTimeUnixNano=9_000),
        make_span("2" * 16, parent="1" * 16, startTimeUnixNano=2_000, endTimeUnixNano=8_000),
        make_span("3" * 16, parent="2" * 16, startTimeUnixNano=3_000, endTimeUnixNano=7_000),
    ]
    report = audit(make_document(spans))
    assert report.passed
    assert not rule_ids(report) & {"GR001", "GR002", "GR003", "GR007", "GR008"}
