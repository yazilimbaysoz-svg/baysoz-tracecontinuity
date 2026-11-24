"""Identity rule tests Baysöz Labs <baysozlabs@proton.me>."""

from baysoz_tracecontinuity import Policy

from conftest import audit, make_document, make_span, rule_ids


def test_rejects_malformed_trace_and_span_identifiers() -> None:
    report = audit(make_document([make_span("xyz"), make_span("1" * 16, traceId="ABC")]))
    assert {"ID001", "ID002"} <= rule_ids(report)
    assert report.summary["errors"] >= 2


def test_rejects_zero_identifiers() -> None:
    report = audit(make_document([make_span("0" * 16, traceId="0" * 32)]))
    assert {"ID001", "ID002"} <= rule_ids(report)


def test_rejects_malformed_parent_identifier() -> None:
    report = audit(make_document([make_span("1" * 16, parent="nope")]))
    assert "ID003" in rule_ids(report)


def test_detects_duplicate_span_ids_within_one_trace() -> None:
    report = audit(make_document([make_span("1" * 16), make_span("1" * 16)]))
    assert "ID004" in rule_ids(report)
    assert "spans[0]" in report.findings[0].message


def test_same_span_id_in_different_traces_is_allowed() -> None:
    first = make_span("1" * 16)
    second = make_span("1" * 16, traceId="c" * 32)
    report = audit(make_document([first, second]))
    assert "ID004" not in rule_ids(report)


def test_rejects_invalid_flags() -> None:
    report = audit(make_document([make_span("1" * 16, flags="zz")]))
    assert "ID005" in rule_ids(report)


def test_valid_hex_flags_are_accepted() -> None:
    report = audit(make_document([make_span("1" * 16, flags="03")]))
    assert "ID005" not in rule_ids(report)


def test_empty_document_is_reported() -> None:
    assert rule_ids(audit(make_document([]))) == {"DOC001"}


def test_disabled_rules_are_not_emitted() -> None:
    report = audit(make_document([make_span("1" * 16, flags="zz")]), policy=Policy(disabled_rules=frozenset({"ID005"})))
    assert "ID005" not in rule_ids(report)


def test_valid_minimal_trace_has_no_findings() -> None:
    report = audit(make_document([make_span("1" * 16)]))
    assert report.passed
    assert report.summary["traces"] == 1
    assert report.summary["spans"] == 1
