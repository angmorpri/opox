"""Command-line interface for opox."""

import argparse
import logging
import sys
from pathlib import Path

from opox.add.contexts import add_contexts
from opox.checks.contexts import check_contexts
from opox.checks.questions import check_questions
from opox.checks.rules import check_rules
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
    questions.add_argument("--force", action="store_true", help="overwrite existing output")
    questions.set_defaults(func=_run_extract_questions)

    contexts = sources.add_parser(
        "contexts", parents=[common], help="detect and crop question contexts"
    )
    contexts.add_argument("opposition", nargs="?", default="C2_AGE")
    contexts.add_argument("--force", action="store_true", help="overwrite existing output")
    contexts.set_defaults(func=_run_extract_contexts)

    add = commands.add_parser("add", help="merge reviewed data into processed data")
    add_targets = _subcommands(add, "target")

    add_c = add_targets.add_parser(
        "contexts", parents=[common], help="assign context crops to questions"
    )
    add_c.add_argument("opposition", nargs="?", default="C2_AGE")
    add_c.add_argument("--force", action="store_true", help="replace existing contexts")
    add_c.set_defaults(func=_run_add_contexts)

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
