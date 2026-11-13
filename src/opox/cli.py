"""Command-line interface for opox.

Pattern (D004): `opox <step> extract|add|check|make [<target>] [<options>]`. The target
is required except in steps without targets and in `make`. `extract` and `check` accept
`all` when a step has several targets: `extract all` stops at the first failure, `check
all` runs every check.
"""

import argparse
import logging
import sys
from collections.abc import Callable
from pathlib import Path

from opox.add.contexts import add_contexts
from opox.add.duplicates import add_duplicates
from opox.checks.categories import check_categories
from opox.checks.contexts import check_contexts
from opox.checks.duplicates import check_duplicates
from opox.checks.questions import check_questions
from opox.checks.rules import check_rules
from opox.extract.categories import extract_categories
from opox.extract.contexts import extract_contexts
from opox.extract.duplicates import ANSWER_THRESHOLD, THRESHOLD, extract_duplicates
from opox.extract.questions import extract_questions
from opox.extract.rules import rules_instructions
from opox.make.bank import make_bank

Runner = Callable[[argparse.Namespace], int]

# What `extract --force` discards, per target (D006); shown before asking to confirm.
FORCE_LOSSES = {
    "questions": "questions.json: every exam, its manual fixes and the assigned contexts",
    "contexts": "contexts.csv and the crops: the manual review of contexts",
    "duplicates": "duplicates.json, dup_contexts.csv and dup_check.csv: manual groups and "
    "every review decision",
    "categories": "categories.json: any manual edit",
}


def _print_notes(ok: bool, notes: list[str]) -> int:
    """Print notes, as errors on failure; return the exit code."""
    for note in notes:
        print(f"ERROR {note}" if not ok else note, file=sys.stderr if not ok else sys.stdout)
    return 0 if ok else 1


def _print_errors(errors: list[str], success: str) -> int:
    """Print check errors and a closing line; return the exit code."""
    for error in errors:
        print(f"ERROR {error}", file=sys.stderr)
    if errors:
        print(f"{len(errors)} problem(s) found.", file=sys.stderr)
        return 1
    print(success)
    return 0


def _run_extract_rules(args: argparse.Namespace) -> int:
    return _print_notes(*rules_instructions(args.data_dir, args.opposition, args.force))


def _run_check_rules(args: argparse.Namespace) -> int:
    return _print_errors(
        check_rules(args.data_dir, args.opposition), "All rules match the reference."
    )


def _run_extract_questions(args: argparse.Namespace) -> int:
    added, notes = extract_questions(args.data_dir, args.opposition, args.force)
    for note in notes:
        print(f"REVIEW {note}")
    for exam in added:
        print(f"ADDED {exam.exam_id}: {len(exam.questions)} question(s)")
    if not added:
        print("No new exams; questions unchanged.")
        return 0
    n_questions = sum(len(e.questions) for e in added)
    print(
        f"{len(added)} exam(s), {n_questions} question(s) added. {len(notes)} point(s) to review."
    )
    return 0


def _run_extract_contexts(args: argparse.Namespace) -> int:
    scanned, added, notes = extract_contexts(args.data_dir, args.opposition, args.force)
    for note in notes:
        print(f"REVIEW {note}")
    for c in added:
        print(f"ADDED {c.exam_id} p{c.page}: questions {c.first}-{c.last}")
    if not scanned:
        print("No new exams; contexts unchanged.")
        return 0
    print(
        f"{len(scanned)} exam(s) scanned, {len(added)} context(s) added. "
        f"{len(notes)} point(s) to review."
    )
    return 0


def _run_add_contexts(args: argparse.Namespace) -> int:
    return _print_notes(*add_contexts(args.data_dir, args.opposition))


def _run_check_questions(args: argparse.Namespace) -> int:
    errors, warnings = check_questions(args.data_dir, args.opposition)
    for warning in warnings:
        print(f"WARNING {warning}")
    return _print_errors(errors, "Questions are consistent with rules and sources.")


def _run_check_contexts(args: argparse.Namespace) -> int:
    return _print_errors(
        check_contexts(args.data_dir, args.opposition),
        "Contexts are consistent with crops and questions.",
    )


def _run_extract_duplicates(args: argparse.Namespace) -> int:
    return _print_notes(
        *extract_duplicates(
            args.data_dir, args.opposition, args.force, args.threshold, args.answer_threshold
        )
    )


def _run_add_duplicates(args: argparse.Namespace) -> int:
    return _print_notes(*add_duplicates(args.data_dir, args.opposition))


def _run_check_duplicates(args: argparse.Namespace) -> int:
    errors, warnings, notes = check_duplicates(args.data_dir, args.opposition)
    for warning in warnings:
        print(f"WARNING {warning}")
    for note in notes:
        print(note)
    return _print_errors(errors, "Duplicates are consistent with questions and sheets.")


def _run_make_bank(args: argparse.Namespace) -> int:
    return _print_notes(*make_bank(args.data_dir, args.opposition))


def _run_extract_categories(args: argparse.Namespace) -> int:
    return _print_notes(*extract_categories(args.data_dir, args.opposition, args.force))


def _run_check_categories(args: argparse.Namespace) -> int:
    return _print_errors(
        check_categories(args.data_dir, args.opposition),
        "Categories cover every topic of the rules.",
    )


def _run_all(targets: list[tuple[str, Runner]], stop_on_error: bool) -> Runner:
    """Run several targets in order; fail if any fails."""

    def run(args: argparse.Namespace) -> int:
        code = 0
        for name, func in targets:
            print(f"== {name} ==")
            code = max(code, func(args))
            if code and stop_on_error:
                print(f"Stopped after {name} failed.", file=sys.stderr)
                break
        return code

    return run


def _confirm_force(losses: list[str], assume_yes: bool) -> bool:
    """Show what --force discards and ask for confirmation."""
    print("--force rebuilds from scratch and discards:")
    for loss in losses:
        print(f"  - {loss}")
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        print("ERROR not an interactive terminal; pass --yes to confirm", file=sys.stderr)
        return False
    try:
        return input("Continue? [y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        print()
        return False


class _Subcommands(dict):
    """Subcommand map that also accepts any unambiguous prefix (D004)."""

    def resolve(self, name: str) -> str:
        if dict.__contains__(self, name):
            return name
        matches = [k for k in self if k.startswith(name)]
        return matches[0] if len(matches) == 1 else name

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and dict.__contains__(self, self.resolve(name))

    def __getitem__(self, name: str) -> argparse.ArgumentParser:
        return dict.__getitem__(self, self.resolve(name))


class _PrefixSubParsersAction(argparse._SubParsersAction):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._name_parser_map = self.choices = _Subcommands()

    def __call__(self, parser, namespace, values, option_string=None) -> None:
        name = self._name_parser_map.resolve(values[0])
        super().__call__(parser, namespace, [name, *values[1:]], option_string)


def _subcommands(parser: argparse.ArgumentParser, dest: str) -> argparse._SubParsersAction:
    return parser.add_subparsers(dest=dest, required=True, action=_PrefixSubParsersAction)


def _build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("opposition", nargs="?", default="C2_AGE")
    common.add_argument("-v", "--verbose", action="store_true", help="report progress")
    forced = argparse.ArgumentParser(add_help=False)
    forced.add_argument(
        "--force", action="store_true", help="rebuild from scratch, discarding manual work"
    )
    forced.add_argument("-y", "--yes", action="store_true", help="confirm --force without asking")

    def command(subs, name: str, help: str, func: Runner, *, force: bool = False, losses=()):
        p = subs.add_parser(name, parents=[common, forced] if force else [common], help=help)
        p.set_defaults(func=func, losses=list(losses))
        return p

    parser = argparse.ArgumentParser(prog="opox")
    parser.add_argument(
        "--data-dir", type=Path, default=Path("data"), help="data root (default: data)"
    )
    steps = _subcommands(parser, "step")

    # rules: call rules, extracted by an agent (D008).
    rules = _subcommands(steps.add_parser("rules", help="call rules (bases)"), "action")
    command(
        rules,
        "extract",
        "show the instructions for the extraction agent",
        _run_extract_rules,
        force=True,
    )
    command(rules, "check", "check the rules against the manual topic count", _run_check_rules)

    # tests: questions and contexts per exam (D009, D005).
    tests = _subcommands(steps.add_parser("tests", help="exams: questions and contexts"), "action")
    extract = _subcommands(tests.add_parser("extract", help="extract from the exam PDFs"), "target")
    command(
        extract,
        "questions",
        "extract exam questions and answers",
        _run_extract_questions,
        force=True,
        losses=[FORCE_LOSSES["questions"]],
    )
    command(
        extract,
        "contexts",
        "detect and crop question contexts",
        _run_extract_contexts,
        force=True,
        losses=[FORCE_LOSSES["contexts"]],
    )
    command(
        extract,
        "all",
        "extract questions, then contexts",
        _run_all(
            [("questions", _run_extract_questions), ("contexts", _run_extract_contexts)], True
        ),
        force=True,
        losses=[FORCE_LOSSES["questions"], FORCE_LOSSES["contexts"]],
    )
    add = _subcommands(tests.add_parser("add", help="merge reviewed data"), "target")
    command(add, "contexts", "assign context crops to questions", _run_add_contexts)
    check = _subcommands(tests.add_parser("check", help="validate exam data"), "target")
    command(check, "questions", "check extracted exam questions", _run_check_questions)
    command(check, "contexts", "check the context sheet and crops", _run_check_contexts)
    command(
        check,
        "all",
        "check questions and contexts",
        _run_all([("questions", _run_check_questions), ("contexts", _run_check_contexts)], False),
    )

    # bank: deduplication and question bank (D010, D011).
    bank = _subcommands(steps.add_parser("bank", help="question bank"), "action")
    extract = _subcommands(bank.add_parser("extract", help="extract from the questions"), "target")
    duplicates = command(
        extract,
        "duplicates",
        "identify duplicate questions and review sheets",
        _run_extract_duplicates,
        force=True,
        losses=[FORCE_LOSSES["duplicates"]],
    )
    duplicates.add_argument(
        "--threshold",
        type=float,
        help=f"min key similarity for review, 0-100 (default: stored, else {THRESHOLD:g})",
    )
    duplicates.add_argument(
        "--answer-threshold",
        type=float,
        help=f"min answer similarity for review, 0-100 (default: stored, else {ANSWER_THRESHOLD:g})",
    )
    add = _subcommands(bank.add_parser("add", help="merge reviewed data"), "target")
    command(add, "duplicates", "join the reviewed possible duplicates", _run_add_duplicates)
    check = _subcommands(bank.add_parser("check", help="validate bank data"), "target")
    command(check, "duplicates", "check duplicate groups and review sheets", _run_check_duplicates)
    command(bank, "make", "build the question bank", _run_make_bank)

    # categories: official categories and their topics per call (D012).
    categories = _subcommands(
        steps.add_parser("categories", help="categories and topics per call"), "action"
    )
    command(
        categories,
        "extract",
        "extract categories and their topics per call",
        _run_extract_categories,
        force=True,
        losses=[FORCE_LOSSES["categories"]],
    )
    command(categories, "check", "check that every topic has a category", _run_check_categories)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the `opox` command."""
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(message)s",
        datefmt="%H:%M:%S",
    )
    if getattr(args, "force", False) and args.losses and not _confirm_force(args.losses, args.yes):
        print("Aborted; nothing changed.")
        return 1
    return args.func(args)
