"""Command-line interface for opox."""

import argparse
import sys
from pathlib import Path

from opox.checks.questions import check_questions
from opox.checks.rules import check_rules
from opox.extract.questions import extract_questions


def _run_extract_questions(args: argparse.Namespace) -> int:
    written, notes = extract_questions(args.data_dir, args.opposition, args.force)
    if not written:
        for note in notes:
            print(f"ERROR {note}", file=sys.stderr)
        return 1
    for note in notes:
        print(f"REVIEW {note}")
    print(f"Questions written. {len(notes)} point(s) to review.")
    return 0


def _run_check_questions(args: argparse.Namespace) -> int:
    errors, warnings = check_questions(args.data_dir, args.opposition)
    for error in errors:
        print(f"ERROR {error}", file=sys.stderr)
    for warning in warnings:
        print(f"WARNING {warning}")
    if errors:
        print(f"{len(errors)} problem(s) found.", file=sys.stderr)
        return 1
    print("Questions are consistent with rules and sources.")
    return 0


def _run_check_rules(args: argparse.Namespace) -> int:
    errors = check_rules(args.data_dir, args.opposition)
    for error in errors:
        print(f"ERROR {error}", file=sys.stderr)
    if errors:
        print(f"{len(errors)} problem(s) found.", file=sys.stderr)
        return 1
    print("All rules match the reference.")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="opox")
    parser.add_argument(
        "--data-dir", type=Path, default=Path("data"), help="data root (default: data)"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    extract = commands.add_parser("extract", help="extract structured data from raw sources")
    sources = extract.add_subparsers(dest="target", required=True)

    questions = sources.add_parser("questions", help="extract exam questions and answers")
    questions.add_argument("opposition", nargs="?", default="C2_AGE")
    questions.add_argument("--force", action="store_true", help="overwrite existing output")
    questions.set_defaults(func=_run_extract_questions)

    check = commands.add_parser("check", help="validate data against references")
    targets = check.add_subparsers(dest="target", required=True)

    rules = targets.add_parser("rules", help="check extracted call rules")
    rules.add_argument("opposition", nargs="?", default="C2_AGE")
    rules.set_defaults(func=_run_check_rules)

    check_q = targets.add_parser("questions", help="check extracted exam questions")
    check_q.add_argument("opposition", nargs="?", default="C2_AGE")
    check_q.set_defaults(func=_run_check_questions)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the `opox` command."""
    args = _build_parser().parse_args(argv)
    return args.func(args)
