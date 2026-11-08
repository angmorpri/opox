"""Command-line interface for opox."""

import argparse
import logging
import sys
from pathlib import Path

from opox.add.contexts import add_contexts
from opox.add.duplicates import add_duplicates
from opox.checks.contexts import check_contexts
from opox.checks.duplicates import check_duplicates
from opox.checks.questions import check_questions
from opox.checks.rules import check_rules
from opox.extract.categories import extract_categories
from opox.extract.contexts import extract_contexts
from opox.extract.duplicates import ANSWER_THRESHOLD, THRESHOLD, extract_duplicates
from opox.extract.questions import extract_questions
from opox.make.bank import make_bank


def _print_notes(ok: bool, notes: list[str]) -> int:
    """Print notes, as errors on failure; return the exit code."""
    for note in notes:
        print(f"ERROR {note}" if not ok else note, file=sys.stderr if not ok else sys.stdout)
    return 0 if ok else 1


def _run_extract_categories(args: argparse.Namespace) -> int:
    return _print_notes(*extract_categories(args.data_dir, args.opposition, args.force))


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
    for error in errors:
        print(f"ERROR {error}", file=sys.stderr)
    for warning in warnings:
        print(f"WARNING {warning}")
    for note in notes:
        print(note)
    if errors:
        print(f"{len(errors)} problem(s) found.", file=sys.stderr)
        return 1
    print("Duplicates are consistent with questions and sheets.")
    return 0


def _run_make_bank(args: argparse.Namespace) -> int:
    return _print_notes(*make_bank(args.data_dir, args.opposition))


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
    ok, notes = add_contexts(args.data_dir, args.opposition)
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
    common.add_argument("-v", "--verbose", action="store_true", help="report progress")

    parser = argparse.ArgumentParser(prog="opox")
    parser.add_argument(
        "--data-dir", type=Path, default=Path("data"), help="data root (default: data)"
    )
    commands = _subcommands(parser, "command")

    extract = commands.add_parser("extract", help="extract structured data from raw sources")
    sources = _subcommands(extract, "target")

    questions = sources.add_parser(
        "questions", parents=[common], help="extract exam questions and answers"
    )
    questions.add_argument("opposition", nargs="?", default="C2_AGE")
    questions.add_argument("--force", action="store_true", help="extract every exam again")
    questions.set_defaults(func=_run_extract_questions)

    contexts = sources.add_parser(
        "contexts", parents=[common], help="detect and crop question contexts"
    )
    contexts.add_argument("opposition", nargs="?", default="C2_AGE")
    contexts.add_argument("--force", action="store_true", help="rebuild the sheet and crops")
    contexts.set_defaults(func=_run_extract_contexts)

    categories = sources.add_parser(
        "categories", parents=[common], help="extract categories and their topics per call"
    )
    categories.add_argument("opposition", nargs="?", default="C2_AGE")
    categories.add_argument("--force", action="store_true", help="rebuild the file")
    categories.set_defaults(func=_run_extract_categories)

    duplicates = sources.add_parser(
        "duplicates", parents=[common], help="identify duplicate questions and review sheets"
    )
    duplicates.add_argument("opposition", nargs="?", default="C2_AGE")
    duplicates.add_argument(
        "--force", action="store_true", help="rebuild, discarding manual groups and decisions"
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
    duplicates.set_defaults(func=_run_extract_duplicates)

    add = commands.add_parser("add", help="merge reviewed data into processed data")
    add_targets = _subcommands(add, "target")

    add_c = add_targets.add_parser(
        "contexts", parents=[common], help="assign context crops to questions"
    )
    add_c.add_argument("opposition", nargs="?", default="C2_AGE")
    add_c.set_defaults(func=_run_add_contexts)

    add_d = add_targets.add_parser(
        "duplicates", parents=[common], help="join the reviewed possible duplicates"
    )
    add_d.add_argument("opposition", nargs="?", default="C2_AGE")
    add_d.set_defaults(func=_run_add_duplicates)

    check = commands.add_parser("check", help="validate data against references")
    targets = _subcommands(check, "target")

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

    check_d = targets.add_parser(
        "duplicates", parents=[common], help="check duplicate groups and review sheets"
    )
    check_d.add_argument("opposition", nargs="?", default="C2_AGE")
    check_d.set_defaults(func=_run_check_duplicates)

    make = commands.add_parser("make", help="build final data from reviewed data")
    make_targets = _subcommands(make, "target")

    bank = make_targets.add_parser("bank", parents=[common], help="build the question bank")
    bank.add_argument("opposition", nargs="?", default="C2_AGE")
    bank.set_defaults(func=_run_make_bank)

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
