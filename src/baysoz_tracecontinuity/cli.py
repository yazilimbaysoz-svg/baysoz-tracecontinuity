"""Command-line interface Baysöz Labs <baysozlabs@proton.me>."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .audit import audit_document
from .model import InputError
from .policy import Policy
from .report import ATTRIBUTION, PROJECT, to_json, to_sarif, to_text

_RENDERERS = {"text": to_text, "json": to_json, "sarif": to_sarif}


def _version() -> str:
    return f"{PROJECT} {__version__} — {ATTRIBUTION}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROJECT,
        description=(
            "Deterministic offline distributed-trace continuity and W3C propagation conformance "
            f"oracle. Built by {ATTRIBUTION}."
        ),
        epilog=(
            f"Attribution: {ATTRIBUTION}. Exit codes: 0 pass, 1 gate failure, 2 invalid input. "
            "No network access, no external services."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", help="OTLP/JSON trace document path, or - for stdin")
    parser.add_argument("--version", action="version", version=_version())
    parser.add_argument("--format", choices=sorted(_RENDERERS), default="text", help="report format")
    parser.add_argument("--output", metavar="PATH", help="write the report to a file instead of stdout")
    parser.add_argument("--config", metavar="PATH", help="JSON policy override file")
    parser.add_argument("--max-depth", type=int, help="maximum allowed parent-chain depth")
    parser.add_argument("--skew-tolerance-ns", type=int, help="allowed parent/child clock skew in nanoseconds")
    parser.add_argument(
        "--fail-on",
        choices=("error", "warning", "none"),
        default="error",
        help="minimum severity that fails the CI gate",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        policy = (
            Policy()
            if args.config is None
            else Policy.from_mapping(json.loads(Path(args.config).read_text(encoding="utf-8")))
        )
        if args.max_depth is not None:
            if args.max_depth < 0:
                raise ValueError("max_depth must be non-negative")
            policy = Policy(
                max_depth=args.max_depth,
                skew_tolerance_ns=policy.skew_tolerance_ns,
                require_error_type=policy.require_error_type,
                disabled_rules=policy.disabled_rules,
            )
        if args.skew_tolerance_ns is not None:
            if args.skew_tolerance_ns < 0:
                raise ValueError("skew_tolerance_ns must be non-negative")
            policy = Policy(
                max_depth=policy.max_depth,
                skew_tolerance_ns=args.skew_tolerance_ns,
                require_error_type=policy.require_error_type,
                disabled_rules=policy.disabled_rules,
            )
        raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
        document = json.loads(raw)
        report = audit_document(document, policy, source=args.input)
        rendered = _RENDERERS[args.format](report)
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (InputError, OSError, ValueError) as exc:
        print(f"{PROJECT}: {exc} ({ATTRIBUTION})", file=sys.stderr)
        return 2

    if args.fail_on == "error":
        failed = not report.passed
    elif args.fail_on == "warning":
        failed = report.summary["errors"] + report.summary["warnings"] > 0
    else:
        failed = False
    if failed:
        print(f"{PROJECT}: gate failed ({ATTRIBUTION})", file=sys.stderr)
    return int(failed)
