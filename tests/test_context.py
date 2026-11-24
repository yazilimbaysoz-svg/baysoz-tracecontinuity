"""W3C propagation rule tests Baysöz Labs <baysozlabs@proton.me>."""

from conftest import TRACE_ID, audit, make_document, make_span, rule_ids


def observation(traceparent: str, **extra: str) -> dict[str, str]:
    result = {"source": "edge", "traceparent": traceparent}
    result.update(extra)
    return result


def valid_traceparent(span_id: str = "1" * 16, flags: str = "01") -> str:
    return f"00-{TRACE_ID}-{span_id}-{flags}"


def test_malformed_traceparent_is_rejected() -> None:
    report = audit(make_document([make_span("1" * 16)], [observation("not-a-header")]))
    assert "CX001" in rule_ids(report)


def test_unsupported_traceparent_version_is_reported() -> None:
    header = valid_traceparent().replace("00-", "01-", 1)
    report = audit(make_document([make_span("1" * 16)], [observation(header)]))
    assert "CX001" in rule_ids(report)
    assert "unsupported version" in report.findings[0].message


def test_zero_context_identifier_is_rejected() -> None:
    report = audit(make_document([make_span("1" * 16)], [observation(f"00-{TRACE_ID}-{'0' * 16}-01")]))
    assert "CX002" in rule_ids(report)


def test_unanchored_context_is_reported() -> None:
    header = f"00-{'b' * 32}-{'1' * 16}-01"
    report = audit(make_document([make_span("1" * 16)], [observation(header)]))
    assert "CX003" in rule_ids(report)


def test_missing_context_parent_is_reported() -> None:
    report = audit(make_document([make_span("1" * 16)], [observation(valid_traceparent("f" * 16))]))
    assert "CX004" in rule_ids(report)


def test_sampled_flag_disagreement_is_reported() -> None:
    report = audit(make_document([make_span("1" * 16, flags=1)], [observation(valid_traceparent(flags="00"))]))
    assert "CX005" in rule_ids(report)


def test_invalid_tracestate_is_reported() -> None:
    report = audit(
        make_document(
            [make_span("1" * 16)],
            [observation(valid_traceparent(), tracestate="UPPER=value")],
        )
    )
    assert "CX006" in rule_ids(report)


def test_valid_tracestate_is_accepted() -> None:
    report = audit(
        make_document(
            [make_span("1" * 16)],
            [observation(valid_traceparent(), tracestate="congo=t61rcWkgMzE,rojo=00f067aa0ba902b7")],
        )
    )
    assert "CX006" not in rule_ids(report)


def test_malformed_baggage_header_is_rejected() -> None:
    report = audit(
        make_document(
            [make_span("1" * 16)],
            [observation(valid_traceparent(), baggage="tenant")],
        )
    )
    assert "CX007" in rule_ids(report)


def test_baggage_loss_between_parent_and_child_is_reported() -> None:
    spans = [
        make_span("1" * 16, attributes={"baggage": "tenant=acme"}),
        make_span("2" * 16, parent="1" * 16),
    ]
    report = audit(make_document(spans))
    assert "CX008" in rule_ids(report)


def test_baggage_continuity_is_accepted() -> None:
    spans = [
        make_span("1" * 16, attributes={"baggage": "tenant=acme"}),
        make_span("2" * 16, parent="1" * 16, attributes={"baggage": "tenant=acme"}),
    ]
    report = audit(make_document(spans))
    assert "CX008" not in rule_ids(report)


def test_invalid_link_identifier_is_rejected() -> None:
    span = make_span("1" * 16, links=[{"traceId": "nope", "spanId": "nope"}])
    report = audit(make_document([span]))
    assert "CX009" in rule_ids(report)


def test_same_trace_link_sampling_mismatch_is_reported() -> None:
    span = make_span(
        "1" * 16,
        flags=1,
        links=[{"traceId": TRACE_ID, "spanId": "2" * 16, "flags": 0}],
    )
    report = audit(make_document([span]))
    assert "CX010" in rule_ids(report)


def test_inconsistent_sampling_within_trace_is_reported() -> None:
    spans = [make_span("1" * 16, flags=1), make_span("2" * 16, parent="1" * 16, flags=0)]
    report = audit(make_document(spans))
    assert "CX011" in rule_ids(report)


def test_fully_valid_propagation_has_no_findings() -> None:
    report = audit(
        make_document(
            [make_span("1" * 16)],
            [observation(valid_traceparent(), tracestate="congo=t61rcWkgMzE")],
        )
    )
    assert report.passed
    assert report.findings == ()
