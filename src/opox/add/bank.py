"""Add the decisions of the bank control sheets to the question bank (D010).

Inputs, for a given opposition: `processed/<opposition>/questions.json`, `bank.json`
and the control sheets `interim/<opposition>/bank_merges.csv` and `bank_contexts.csv`.

Output: `bank.json`, with the entries of every fully decided set of candidates. Entries
already present are kept; replacing a different one requires `force` (D006). The review
report is rewritten with the rows still pending.
"""

import logging
from pathlib import Path

from opox.extract.bank import (
    CONTEXT_COLUMNS,
    MERGE_COLUMNS,
    BankPaths,
    load_groups,
    read_rows,
    resolve_bank,
    write_bank,
    write_review,
)
from opox.models.bank import BankQuestion, QuestionBank

log = logging.getLogger(__name__)


def merge_entries(
    current: list[BankQuestion], resolved: list[BankQuestion], force: bool
) -> tuple[list[BankQuestion], int, int, list[str]]:
    """Merge resolved entries into the bank; return (bank, added, unchanged, conflicts).

    A resolved entry sharing sources with a different existing one is a conflict: it
    replaces the existing ones only if forced.
    """
    bank = {e.bank_id: e for e in current}
    owner = {s: e.bank_id for e in current for s in e.sources}
    added = unchanged = 0
    conflicts: list[str] = []
    for entry in resolved:
        if bank.get(entry.bank_id) == entry:
            unchanged += 1
            continue
        overlapping = sorted({owner[s] for s in entry.sources if s in owner})
        if overlapping:
            conflicts.append(f"{entry.bank_id}: differs from existing {', '.join(overlapping)}")
            if not force:
                continue
            for bank_id in overlapping:
                for s in bank.pop(bank_id).sources:
                    owner.pop(s, None)
        bank[entry.bank_id] = entry
        owner.update({s: entry.bank_id for s in entry.sources})
        added += 1
    return list(bank.values()), added, unchanged, conflicts


def add_bank(data_dir: Path, opposition: str, force: bool = False) -> tuple[bool, list[str]]:
    """Add decided candidates to the bank. Return (success, notes)."""
    paths = BankPaths.of(data_dir, opposition)
    for path in (paths.questions, paths.merges, paths.contexts):
        if not path.is_file():
            return False, [f"file not found: {path}", "run `opox extract bank` first"]
    merge_rows, errors = read_rows(paths.merges, MERGE_COLUMNS)
    context_rows, context_errors = read_rows(paths.contexts, CONTEXT_COLUMNS)
    if errors or context_errors:
        return False, errors + context_errors

    groups = load_groups(paths.questions)
    resolution = resolve_bank(groups, merge_rows, context_rows)
    if resolution.errors:
        return False, [*resolution.errors, "fix the sheets and retry"]

    current = (
        QuestionBank.model_validate_json(paths.bank.read_text(encoding="utf-8")).root
        if paths.bank.is_file()
        else []
    )
    bank, added, unchanged, conflicts = merge_entries(current, resolution.entries, force)
    log.info("%d resolved entries: %d new, %d unchanged", len(resolution.entries), added, unchanged)
    if added:
        write_bank(paths.bank, bank)
    write_review(paths.review, opposition, groups, merge_rows, context_rows)

    notes = [f"{'replaced' if force else 'skipped'} {c}" for c in conflicts]
    if conflicts and not force:
        notes.append(
            f"{len(conflicts)} entries differ from existing ones; use --force to replace them"
        )
    notes.append(
        f"{added} entries added, {unchanged} already present, "
        f"{resolution.pending} decision(s) pending (see {paths.review})"
    )
    return True, notes
