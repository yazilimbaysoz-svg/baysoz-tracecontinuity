"""Semantic-convention rule tests Baysöz Labs <baysozlabs@proton.me>."""

from baysoz_tracecontinuity import Policy

from conftest import audit, make_document, make_span, rule_ids


def test_client_span_without_protocol_attributes_is_rejected() -> None:
    span = make_span("1" * 16, kind="SPAN_KIND_CLIENT")
    assert "SC001" in rule_ids(audit(make_document([span])))


def test_http_protocol_attributes_satisfy_protocol_rule() -> None:
    span = make_span(
        "1" * 16,
        kind="SPAN_KIND_CLIENT",
        attributes={"http.request.method": "GET", "http.response.status_code": 200},
    )
    assert "SC001" not in rule_ids(audit(make_document([span])))


def test_lowercase_http_method_is_rejected() -> None:
    span = make_span("1" * 16, attributes={"http.request.method": "get"})
    assert "SC002" in rule_ids(audit(make_document([span])))


def test_invalid_http_status_is_rejected() -> None:
    span = make_span("1" * 16, attributes={"http.response.status_code": 99})
    assert "SC003" in rule_ids(audit(make_document([span])))


def test_incomplete_rpc_span_is_reported() -> None:
    span = make_span("1" * 16, attributes={"rpc.system": "grpc", "rpc.method": "Get"})
    assert "SC004" in rule_ids(audit(make_document([span])))


def test_literal_database_value_is_reported() -> None:
    span = make_span(
        "1" * 16, attributes={"db.system": "postgresql", "db.statement": "SELECT id FROM t WHERE x='alice'"}
    )
    report = audit(make_document([span]))
    assert "SC005" in rule_ids(report)


def test_parameterized_statement_is_accepted() -> None:
    span = make_span("1" * 16, attributes={"db.system": "postgresql", "db.statement": "SELECT id FROM t WHERE x=$1"})
    assert "SC005" not in rule_ids(audit(make_document([span])))


def test_error_status_without_error_type_is_reported() -> None:
    span = make_span("1" * 16, status={"code": "STATUS_CODE_ERROR"})
    assert "SC006" in rule_ids(audit(make_document([span])))


def test_exception_event_satisfies_error_type_rule() -> None:
    span = make_span(
        "1" * 16,
        status={"code": 2},
        events=[
            {"name": "exception", "attributes": [{"key": "exception.type", "value": {"stringValue": "ValueError"}}]}
        ],
    )
    assert "SC006" not in rule_ids(audit(make_document([span])))


def test_error_type_rule_can_be_disabled_by_policy() -> None:
    span = make_span("1" * 16, status={"code": 2})
    report = audit(make_document([span]), policy=Policy(require_error_type=False))
    assert "SC006" not in rule_ids(report)


def test_legacy_attribute_key_is_reported() -> None:
    span = make_span("1" * 16, attributes={"http.method": "GET"})
    assert "SC007" in rule_ids(audit(make_document([span])))


def test_missing_span_name_is_reported() -> None:
    assert "SC008" in rule_ids(audit(make_document([make_span("1" * 16, name="  ")])))


def test_otlp_typed_attributes_are_decoded() -> None:
    span = make_span(
        "1" * 16,
        attributes=[
            {"key": "http.request.method", "value": {"stringValue": "GET"}},
            {"key": "http.response.status_code", "value": {"intValue": "200"}},
        ],
    )
    report = audit(make_document([span]))
    assert "SC002" not in rule_ids(report)
    assert "SC003" not in rule_ids(report)
