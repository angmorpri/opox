"""Check that the categories cover every topic of the call rules (D012).

Inputs, for a given opposition: `processed/<opposition>/rules.json` and
`processed/<opposition>/categories.json`.

Every topic of every call in `rules.json` must belong to a category, with the same text;
topics in `categories.json` absent from `rules.json` are reported too. Read-only.
"""

import logging
from pathlib import Path

from pydantic import ValidationError

from opox.models.categories import CategoryCollection
from opox.models.rules import CallRulesCollection

log = logging.getLogger(__name__)


def check_categories(data_dir: Path, opposition: str) -> list[str]:
    """Return a list of problems found; empty if every topic is covered."""
    processed = data_dir / "processed" / opposition
    rules_path = processed / "rules.json"
    categories_path = processed / "categories.json"
    for path in (rules_path, categories_path):
        if not path.is_file():
            return [f"file not found: {path}"]
    try:
        rules = CallRulesCollection.model_validate_json(rules_path.read_text(encoding="utf-8"))
    except ValidationError as e:
        return [f"invalid model in {rules_path}\n{e}"]
    try:
        categories = CategoryCollection.model_validate_json(
            categories_path.read_text(encoding="utf-8")
        )
    except ValidationError as e:
        return [f"invalid model in {categories_path}\n{e}"]

    expected = {
        (r.call_id, b.block_id, n): text
        for r in rules.root
        for b in r.syllabus
        for n, text in enumerate(b.topics, 1)
    }
    found = {
        (call.call_id, t.block_id, t.number): t.text
        for c in categories.root
        for call in c.calls
        for t in call.topics
    }
    log.info("checking %d topic(s) of %d call(s)", len(expected), len(rules.root))

    errors = [
        f"{call} {block}.{n}: topic not in any category"
        for call, block, n in sorted(expected.keys() - found.keys())
    ]
    errors += [
        f"{call} {block}.{n}: in {categories_path.name} but not in {rules_path.name}"
        for call, block, n in sorted(found.keys() - expected.keys())
    ]
    errors += [
        f"{call} {block}.{n}: text differs from {rules_path.name}"
        for (call, block, n) in sorted(expected.keys() & found.keys())
        if expected[(call, block, n)] != found[(call, block, n)]
    ]
    return errors
