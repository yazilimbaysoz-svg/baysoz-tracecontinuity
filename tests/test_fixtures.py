"""Repository example tests Baysöz Labs <baysozlabs@proton.me>."""

from __future__ import annotations

from typing import Any

from baysoz_tracecontinuity import audit_document

from conftest import rule_ids


def test_broken_pipeline_example_triggers_all_expected_rule_families(fixture_document: Any) -> None:
    report = audit_document(fixture_document("broken-pipeline.json"), source="broken-pipeline.json")
    expected = {
        "CX002",
        "CX008",
        "CX011",
        "GR001",
        "GR005",
        "ID004",
        "SC001",
        "SC002",
        "SC003",
        "SC005",
        "SC006",
    }
    assert expected <= rule_ids(report)
    assert report.summary["errors"] == 7
    assert report.summary["warnings"] == 5
    assert not report.passed


def test_clean_pipeline_example_passes_all_rules(fixture_document: Any) -> None:
    report = audit_document(fixture_document("clean-pipeline.json"), source="clean-pipeline.json")
    assert report.passed
    assert report.findings == ()
