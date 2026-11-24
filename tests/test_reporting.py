"""Report rendering tests Baysöz Labs <baysozlabs@proton.me>."""

from __future__ import annotations

import json

from baysoz_tracecontinuity import ATTRIBUTION, audit_document
from baysoz_tracecontinuity.report import RULE_CATALOG, to_json, to_sarif, to_text

from conftest import make_document, make_span


def sample_report() -> object:
    return audit_document(
        make_document([make_span("1" * 16, startTimeUnixNano=9, endTimeUnixNano=1)]),
        source="sample.json",
    )


def test_text_report_contains_attribution_and_verdict() -> None:
    rendered = to_text(sample_report())
    assert ATTRIBUTION in rendered
    assert "verdict: FAIL" in rendered
    assert "GR005" in rendered


def test_json_report_is_machine_readable() -> None:
    payload = json.loads(to_json(sample_report()))
    assert payload["attribution"] == ATTRIBUTION
    assert payload["findings"][0]["rule_id"] == "GR005"
    assert payload["summary"]["errors"] == 1


def test_sarif_report_is_valid_shape() -> None:
    payload = json.loads(to_sarif(sample_report()))
    assert payload["version"] == "2.1.0"
    assert payload["runs"][0]["tool"]["driver"]["organization"] == ATTRIBUTION
    assert payload["runs"][0]["results"][0]["ruleId"] == "GR005"
    assert payload["runs"][0]["results"][0]["locations"][0]["logicalLocations"][0]["name"].startswith("spans[")


def test_every_finding_has_a_rule_catalog_entry() -> None:
    report = sample_report()
    assert all(finding.rule_id in RULE_CATALOG for finding in report.findings)


def test_findings_are_deterministically_sorted() -> None:
    document = make_document([make_span("1" * 16, flags="zz", startTimeUnixNano=9, endTimeUnixNano=1)])
    first = audit_document(document)
    second = audit_document(document)
    assert [item.rule_id for item in first.findings] == [item.rule_id for item in second.findings]
    assert [item.pointer for item in first.findings] == [item.pointer for item in second.findings]
