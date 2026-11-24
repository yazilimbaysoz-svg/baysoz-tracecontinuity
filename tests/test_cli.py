"""CLI contract tests Baysöz Labs <baysozlabs@proton.me>."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from baysoz_tracecontinuity import ATTRIBUTION
from baysoz_tracecontinuity.cli import main

from conftest import make_document, make_span

ROOT = Path(__file__).resolve().parents[1]


def test_version_output_attributes_baysöz_labs(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["-", "--version"])
    assert excinfo.value.code == 0
    assert ATTRIBUTION in capsys.readouterr().out


def test_help_output_attributes_baysöz_labs(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0
    assert ATTRIBUTION in capsys.readouterr().out


def test_stdin_audit_returns_zero_for_clean_trace(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(make_document([make_span("1" * 16)]))))
    assert main(["-"]) == 0
    assert "verdict: PASS" in capsys.readouterr().out


def test_json_format_on_stdin(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(make_document([make_span("1" * 16)]))))
    assert main(["-", "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["attribution"] == ATTRIBUTION


def test_sarif_format_on_stdin(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(make_document([make_span("1" * 16)]))))
    assert main(["-", "--format", "sarif"]) == 0
    assert json.loads(capsys.readouterr().out)["runs"][0]["results"] == []


def test_fail_on_warning_blocks_warning_only_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    document = make_document([make_span("1" * 16, name="")])
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(document)))
    assert main(["-", "--fail-on", "warning"]) == 1
    assert "gate failed" in capsys.readouterr().err


def test_fail_on_none_allows_reporting_without_gating(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    document = make_document([make_span("1" * 16, name="")])
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(document)))
    assert main(["-", "--fail-on", "none"]) == 0
    capsys.readouterr()


def test_invalid_document_returns_exit_code_two_and_attributes_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text(json.dumps({"unexpected": "shape"}), encoding="utf-8")
    assert main([str(invalid)]) == 2
    captured = capsys.readouterr()
    assert ATTRIBUTION in captured.err
    assert "expected 'resourceSpans' or 'spans'" in captured.err


def test_policy_config_file_is_applied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "policy.json"
    config.write_text(json.dumps({"max_depth": 0}), encoding="utf-8")
    document = make_document(
        [
            make_span("1" * 16),
            make_span("2" * 16, parent="1" * 16),
        ]
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(document)))
    assert main(["-", "--config", str(config), "--format", "json"]) == 0


def test_output_file_receives_rendered_report(tmp_path: Path) -> None:
    output = tmp_path / "report.sarif"
    assert main([str(ROOT / "examples" / "clean-pipeline.json"), "--format", "sarif", "--output", str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["runs"][0]["tool"]["driver"]["organization"] == ATTRIBUTION


def test_invalid_policy_key_returns_exit_code_two(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "bad-policy.json"
    config.write_text(json.dumps({"unknown": True}), encoding="utf-8")
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(make_document([make_span("1" * 16)]))))
    assert main(["-", "--config", str(config)]) == 2
