"""Command-line interface for opox."""

import argparse
import logging
import sys
from pathlib import Path

from opox.add.bank import add_bank
from opox.add.contexts import add_contexts
from opox.checks.bank import check_bank
from opox.checks.contexts import check_contexts
from opox.checks.questions import check_questions
from opox.checks.rules import check_rules
from opox.extract.bank import SIMILARITY_THRESHOLD, extract_bank
from opox.extract.contexts import extract_contexts
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


def _run_extract_contexts(args: argparse.Namespace) -> int:
    written, notes = extract_contexts(args.data_dir, args.opposition, args.force)
    if not written:
        print(f"ERROR {notes[0]}", file=sys.stderr)
    for note in notes[1:] if not written else notes:
        print(f"REVIEW {note}")
    if not written:
        return 1
    print(f"Contexts written. {len(notes)} point(s) to review.")
    return 0


def _run_extract_bank(args: argparse.Namespace) -> int:
    written, notes = extract_bank(args.data_dir, args.opposition, args.force, args.threshold)
    for note in notes:
        print(note if written else f"ERROR {note}", file=sys.stdout if written else sys.stderr)
    return 0 if written else 1


def _run_add_bank(args: argparse.Namespace) -> int:
    ok, notes = add_bank(args.data_dir, args.opposition, args.force)
    for note in notes:
        print(note if ok else f"ERROR {note}", file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1


def _run_check_bank(args: argparse.Namespace) -> int:
    errors = check_bank(args.data_dir, args.opposition)
    for error in errors:
        print(f"ERROR {error}", file=sys.stderr)
    if errors:
        print(f"{len(errors)} problem(s) found.", file=sys.stderr)
        return 1
    print("Every answered question is in the bank.")
    return 0


def _run_add_contexts(args: argparse.Namespace) -> int:
    ok, notes = add_contexts(args.data_dir, args.opposition, args.force)
    for note in notes:
        print(f"ERROR {note}" if not ok else note, file=sys.stderr if not ok else sys.stdout)
    return 0 if ok else 1


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


def _run_check_contexts(args: argparse.Namespace) -> int:
    errors = check_contexts(args.data_dir, args.opposition)
    for error in errors:
        print(f"ERROR {error}", file=sys.stderr)
    if errors:
        print(f"{len(errors)} problem(s) found.", file=sys.stderr)
        return 1
    print("Contexts are consistent with crops and questions.")
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
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-v", "--verbose", action="store_true", help="report progress")

    parser = argparse.ArgumentParser(prog="opox")
    parser.add_argument(
        "--data-dir", type=Path, default=Path("data"), help="data root (default: data)"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    extract = commands.add_parser("extract", help="extract structured data from raw sources")
    sources = extract.add_subparsers(dest="target", required=True)

    questions = sources.add_parser(
        "questions", parents=[common], help="extract exam questions and answers"
    )
    questions.add_argument("opposition", nargs="?", default="C2_AGE")
    questions.add_argument("--force", action="store_true", help="overwrite existing output")
    questions.set_defaults(func=_run_extract_questions)

    contexts = sources.add_parser(
        "contexts", parents=[common], help="detect and crop question contexts"
    )
    contexts.add_argument("opposition", nargs="?", default="C2_AGE")
    contexts.add_argument("--force", action="store_true", help="overwrite existing output")
    contexts.set_defaults(func=_run_extract_contexts)

    bank = sources.add_parser(
        "bank", parents=[common], help="build the question bank and its control sheets"
    )
    bank.add_argument("opposition", nargs="?", default="C2_AGE")
    bank.add_argument("--force", action="store_true", help="overwrite existing output")
    bank.add_argument(
        "--threshold",
        type=float,
        default=SIMILARITY_THRESHOLD,
        help=f"text and answer similarity for candidates (default: {SIMILARITY_THRESHOLD})",
    )
    bank.set_defaults(func=_run_extract_bank)

    add = commands.add_parser("add", help="merge reviewed data into processed data")
    add_targets = add.add_subparsers(dest="target", required=True)

    add_c = add_targets.add_parser(
        "contexts", parents=[common], help="assign context crops to questions"
    )
    add_c.add_argument("opposition", nargs="?", default="C2_AGE")
    add_c.add_argument("--force", action="store_true", help="replace existing contexts")
    add_c.set_defaults(func=_run_add_contexts)

    add_b = add_targets.add_parser(
        "bank", parents=[common], help="add decided candidates to the question bank"
    )
    add_b.add_argument("opposition", nargs="?", default="C2_AGE")
    add_b.add_argument("--force", action="store_true", help="replace differing entries")
    add_b.set_defaults(func=_run_add_bank)

    check = commands.add_parser("check", help="validate data against references")
    targets = check.add_subparsers(dest="target", required=True)

    rules = targets.add_parser("rules", parents=[common], help="check extracted call rules")
    rules.add_argument("opposition", nargs="?", default="C2_AGE")
    rules.set_defaults(func=_run_check_rules)

    check_q = targets.add_parser(
        "questions", parents=[common], help="check extracted exam questions"
    )
    check_q.add_argument("opposition", nargs="?", default="C2_AGE")
    check_q.set_defaults(func=_run_check_questions)

    check_c = targets.add_parser(
        "contexts", parents=[common], help="check the context sheet and crops"
    )
    check_c.add_argument("opposition", nargs="?", default="C2_AGE")
    check_c.set_defaults(func=_run_check_contexts)

    check_b = targets.add_parser("bank", parents=[common], help="check the question bank")
    check_b.add_argument("opposition", nargs="?", default="C2_AGE")
    check_b.set_defaults(func=_run_check_bank)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the `opox` command."""
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(message)s",
        datefmt="%H:%M:%S",
    )
    return args.func(args)
