"""Join the reviewed possible duplicates into the duplicate groups (D011).

Inputs, for a given opposition: `processed/<opposition>/questions.json` and the outputs
of `opox bank extract duplicates`.

Every pair marked `y` in `dup_check.csv` joins its two groups into a `manual` one. Then,
as a rerun of `opox bank extract duplicates` with the stored thresholds, it rewrites
`duplicates.json`, adds the new context pairs to `dup_contexts.csv`, keeping every
decision, and regenerates `dup_check.csv` without the pairs already joined.
"""

import logging
from pathlib import Path

from opox.extract.duplicates import DupPaths, State, load_questions, read_state, rebuild

log = logging.getLogger(__name__)


def add_duplicates(data_dir: Path, opposition: str) -> tuple[bool, list[str]]:
    """Join the reviewed pairs. Return (success, notes)."""
    paths = DupPaths.of(data_dir, opposition)
    questions, errors = load_questions(paths.questions)
    if errors:
        return False, errors
    for path in (paths.duplicates, paths.check_sheet):
        if not path.is_file():
            return False, [f"file not found: {path}", "run `opox bank extract duplicates` first"]
    state, errors = read_state(paths)
    if errors or state is None or state.thresholds is None:
        return False, [*errors, "fix the problems above and retry"]

    joined = [list(r.pair) for r in state.check_rows if r.same == "y"]
    errors = [
        f"{paths.check_sheet.name} line {r.line}: question not answered or not found: {q}"
        for r in state.check_rows
        if r.same == "y"
        for q in r.pair
        if q not in questions
    ]
    if errors:
        return False, [*errors, "fix the sheet and retry"]
    log.info("%d reviewed pair(s) to join", len(joined))
    new_state = State(
        manual=state.manual + joined,
        context_decisions=state.context_decisions,
        check_rows=state.check_rows,
        thresholds=state.thresholds,
    )
    notes = rebuild(paths, opposition, questions, new_state, state.thresholds)
    return True, [f"{len(joined)} reviewed pair(s) joined", *notes]
