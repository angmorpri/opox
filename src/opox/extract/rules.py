"""Instructions for the agent that extracts the call rules (D008).

The extraction itself is done by an agent: this module only writes the instructions to
give it, listing the calls to extract. Incremental by default: only the PDFs of
`raw/<opposition>/rules/` without an entry in `rules.json` (D006); `force` asks for
every call, rebuilding the file.
"""

import json
from pathlib import Path

INSTRUCTIONS = """\
Extract the call rules (bases de convocatoria) of {opposition} into {rules_path},
following the `CallRulesCollection` model (src/opox/models/rules.py, D008).

{scope}

For each call:
- Exam format (parts, sections, reserve questions, penalty, duration, software
  versions): transcribe it from the "Proceso de selección" or "Fase de oposición"
  section. List the sections of each part in exam order.
- Psychotechnical test: a `PSICO` block whose topics are the aptitudes it names
  ("administrativas", "numéricas", "verbales"), only in calls that include it.
- Syllabus: extract the text with `pdftotext -layout`, remove headers and page
  numbers, and join the lines of each topic. Compare the topics with those of other
  calls to detect lost text: a line visible in the PDF may be missing from its text
  layer (known in 2024I topic 3 and 2024L topic II.7) and must be completed by hand.
- Block ids: the document numeral if any ("I", "II"); "PSICO" for the psychotechnical
  test; "U" if the syllabus has no blocks; the name in upper case without accents if it
  has a name but no numeral.

Validate the result with `opox rules check {opposition}`.
"""


def _known_calls(rules_path: Path) -> set[str]:
    if not rules_path.is_file():
        return set()
    try:
        return {r["call_id"] for r in json.loads(rules_path.read_text(encoding="utf-8"))}
    except json.JSONDecodeError, KeyError, TypeError:
        return set()


def _counted_calls(csv_path: Path) -> set[str]:
    if not csv_path.is_file():
        return set()
    lines = csv_path.read_text(encoding="utf-8-sig").splitlines()[1:]
    return {line.split(",", 1)[0].strip() for line in lines if line.strip()}


def rules_instructions(
    data_dir: Path, opposition: str, force: bool = False
) -> tuple[bool, list[str]]:
    """Return (success, lines): the agent instructions, or why there is nothing to do."""
    raw_dir = data_dir / "raw" / opposition / "rules"
    rules_path = data_dir / "processed" / opposition / "rules.json"
    csv_path = data_dir / "interim" / opposition / "check_rules.csv"
    if not raw_dir.is_dir():
        return False, [f"directory not found: {raw_dir}"]
    available = sorted(p.stem for p in raw_dir.glob("*.pdf"))
    if not available:
        return False, [f"no PDF files in {raw_dir}"]

    known = set() if force else _known_calls(rules_path)
    pending = [c for c in available if c not in known]
    if not pending:
        return True, ["No new calls; rules unchanged."]

    pdfs = ", ".join(f"{c}.pdf" for c in pending)
    if force:
        scope = (
            f"Rebuild the whole file from scratch, replacing its current content, with every "
            f"call in {raw_dir.as_posix()}: {pdfs}."
        )
    else:
        scope = (
            f"Add only these new calls from {raw_dir.as_posix()}, keeping every existing "
            f"entry untouched: {pdfs}."
        )
    lines = [
        INSTRUCTIONS.format(
            opposition=opposition, rules_path=rules_path.as_posix(), scope=scope
        ).rstrip()
    ]
    uncounted = [c for c in pending if c not in _counted_calls(csv_path)]
    if uncounted:
        lines.append(
            f"\nWARNING the manual topic count in {csv_path.as_posix()} lacks "
            f"{', '.join(uncounted)}: `opox rules check` cannot validate them without it."
        )
    return True, lines
