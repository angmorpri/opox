"""Extract the official categories and their topics per call (D012).

Input, for a given opposition: `processed/<opposition>/rules.json` (D008).
Output: `processed/<opposition>/categories.json` (`CategoryCollection`).

Each block of a call is assigned automatically, by its id or name (extended key):
- `PSICO` is the psychotechnical block; its topics are the aptitudes.
- A name equal to a category name gives the whole block to that category.
- Any other block, named ("Actividad administrativa y ofimática") or not ("U"), is split
  at its first topic containing `SPLIT_KEYWORD`: the topics before it are administrative
  activity, and the rest office software. A block without that keyword is an error.

Calls already in the file are left as they are; only the new calls are added (D006).
`--force` rebuilds the file from scratch.
"""

import logging
from pathlib import Path

from pydantic import ValidationError

from opox.models.categories import CallTopics, Category, CategoryCollection, Topic
from opox.models.rules import PSYCHOTECHNICAL_BLOCK_ID, Block, CallRules, CallRulesCollection
from opox.normalize import extended_key

PUBLIC_ORGANIZATION, ADMINISTRATIVE_ACTIVITY, OFFICE_SOFTWARE, PSYCHOTECHNICAL = 1, 2, 3, 4
CATEGORIES = {
    PUBLIC_ORGANIZATION: "Organización pública",
    ADMINISTRATIVE_ACTIVITY: "Actividad administrativa",
    OFFICE_SOFTWARE: "Ofimática",
    PSYCHOTECHNICAL: "Psicotécnico",
}
SPLIT_KEYWORD = "informatica"  # extended key of "informática"

log = logging.getLogger(__name__)


def block_categories(block: Block) -> list[int] | None:
    """Category of each topic of a block, or None if it cannot be assigned."""
    n = len(block.topics)
    if block.block_id == PSYCHOTECHNICAL_BLOCK_ID:
        return [PSYCHOTECHNICAL] * n
    by_name = {extended_key(name): cid for cid, name in CATEGORIES.items()}
    if block.name is not None and extended_key(block.name) in by_name:
        return [by_name[extended_key(block.name)]] * n
    split = next(
        (i for i, t in enumerate(block.topics) if SPLIT_KEYWORD in extended_key(t).split()),
        None,
    )
    if split is None:
        return None
    return [ADMINISTRATIVE_ACTIVITY] * split + [OFFICE_SOFTWARE] * (n - split)


def call_categories(rules: CallRules) -> tuple[dict[int, CallTopics], list[str]]:
    """Topics of a call by category, and the blocks that could not be assigned."""
    topics: dict[int, list[Topic]] = {cid: [] for cid in CATEGORIES}
    errors = []
    for block in rules.syllabus:
        categories = block_categories(block)
        if categories is None:
            name = f" ({block.name})" if block.name else ""
            errors.append(
                f"{rules.call_id}: block {block.block_id}{name} matches no category and has "
                f"no topic with {SPLIT_KEYWORD!r}"
            )
            continue
        for number, (text, cid) in enumerate(zip(block.topics, categories, strict=True), 1):
            topics[cid].append(Topic(block_id=block.block_id, number=number, text=text))
    return {
        cid: CallTopics(call_id=rules.call_id, topics=ts) for cid, ts in topics.items() if ts
    }, errors


def extract_categories(
    data_dir: Path, opposition: str, force: bool = False
) -> tuple[bool, list[str]]:
    """Write or update the categories. Return (success, notes)."""
    processed = data_dir / "processed" / opposition
    rules_path = processed / "rules.json"
    out_path = processed / "categories.json"
    if not rules_path.is_file():
        return False, [f"file not found: {rules_path}"]
    try:
        rules = CallRulesCollection.model_validate_json(rules_path.read_text(encoding="utf-8"))
    except ValidationError as e:
        return False, [f"invalid model in {rules_path}\n{e}"]

    existing: dict[int, list[CallTopics]] = {cid: [] for cid in CATEGORIES}
    notes: list[str] = []
    if out_path.exists() and not force:
        try:
            current = CategoryCollection.model_validate_json(out_path.read_text(encoding="utf-8"))
        except ValidationError as e:
            return False, [
                f"invalid model in {out_path}\n{e}",
                "fix it, or rebuild it with --force",
            ]
        unknown = [c.category_id for c in current.root if c.category_id not in CATEGORIES]
        if unknown:
            return False, [f"{out_path}: unknown category ids {unknown}; rebuild it with --force"]
        for c in current.root:
            existing[c.category_id] = list(c.calls)
    elif out_path.exists():
        notes.append(f"rebuilding {out_path}")

    covered = {call.call_id for calls in existing.values() for call in calls}
    rule_ids = {r.call_id for r in rules.root}
    notes += [
        f"WARNING {c}: in {out_path.name} but not in {rules_path.name}"
        for c in sorted(covered - rule_ids)
    ]
    new_calls = [r for r in rules.root if r.call_id not in covered]
    errors: list[str] = []
    for i, call_rules in enumerate(new_calls, 1):
        log.info("[%d/%d] %s", i, len(new_calls), call_rules.call_id)
        by_category, call_errors = call_categories(call_rules)
        errors += call_errors
        for cid, call_topics in by_category.items():
            existing[cid].append(call_topics)
        counts = ", ".join(f"{CATEGORIES[cid]} {len(ct.topics)}" for cid, ct in by_category.items())
        notes.append(f"ADDED {call_rules.call_id}: {counts}")
    if errors:
        return False, [*errors, f"{out_path} not written"]
    if not new_calls:
        return True, [*notes, "No new calls; categories unchanged."]

    collection = CategoryCollection(
        [
            Category(
                category_id=cid,
                name=name,
                calls=sorted(existing[cid], key=lambda c: c.call_id),
            )
            for cid, name in CATEGORIES.items()
        ]
    )
    out_path.write_text(collection.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return True, [*notes, f"{len(new_calls)} call(s) added -> {out_path}"]
