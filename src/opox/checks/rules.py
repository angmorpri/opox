"""Check extracted call rules against a manual count of topics per block.

Inputs, for a given opposition:
- `processed/<opposition>/rules.json`: rules of all calls, extracted by an agent (D008).
- `interim/<opposition>/check_rules.csv`: manual reference, one row per call, with
  columns `call_id, n_topics_block_1, n_topics_block_2, ...`. Columns follow the
  order of the non-psychotechnical blocks in the syllabus; `-` means no such block.

This check is read-only.
"""

import csv
import logging
from pathlib import Path

from pydantic import ValidationError

from opox.models.rules import PSYCHOTECHNICAL_BLOCK_ID, CallRulesCollection

_NO_BLOCK = "-"

log = logging.getLogger(__name__)


def _read_expected(csv_path: Path) -> dict[str, list[int]]:
    """Map each call_id to its expected topic counts, in block order."""
    expected: dict[str, list[int]] = {}
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        count_columns = [c for c in reader.fieldnames or [] if c != "call_id"]
        for row in reader:
            values = [row[c].strip() for c in count_columns]
            expected[row["call_id"].strip()] = [int(v) for v in values if v != _NO_BLOCK]
    return expected


def check_rules(data_dir: Path, opposition: str) -> list[str]:
    """Return a list of problems found; empty if everything matches."""
    rules_path = data_dir / "processed" / opposition / "rules.json"
    csv_path = data_dir / "interim" / opposition / "check_rules.csv"
    raw_dir = data_dir / "raw" / opposition

    for path in (rules_path, csv_path):
        if not path.is_file():
            return [f"file not found: {path}"]
    expected = _read_expected(csv_path)
    try:
        collection = CallRulesCollection.model_validate_json(rules_path.read_text(encoding="utf-8"))
    except ValidationError as e:
        return [f"invalid model in {rules_path}\n{e}"]
    rules_by_id = {r.call_id: r for r in collection.root}

    log.info("checking %d call(s) from %s", len(rules_by_id), rules_path)
    errors: list[str] = []
    for call_id in sorted(expected.keys() - rules_by_id.keys()):
        errors.append(f"{call_id}: missing in {rules_path}")
    for call_id in sorted(rules_by_id.keys() - expected.keys()):
        errors.append(f"{call_id}: not listed in {csv_path}")

    for call_id in sorted(expected.keys() & rules_by_id.keys()):
        rules = rules_by_id[call_id]
        log.info("  %s", call_id)
        if not (raw_dir / rules.source).is_file():
            errors.append(f"{call_id}: source not found: {raw_dir / rules.source}")

        actual = [len(b.topics) for b in rules.syllabus if b.block_id != PSYCHOTECHNICAL_BLOCK_ID]
        if actual != expected[call_id]:
            errors.append(f"{call_id}: topics per block {actual}, expected {expected[call_id]}")

    return errors
