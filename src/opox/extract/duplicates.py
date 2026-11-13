"""Identify duplicate questions and write their review sheets (D011).

Input, for a given opposition: `processed/<opposition>/questions.json`.

Outputs, in `interim/<opposition>/`:
- `duplicates.json`: groups of duplicate questions (`DuplicateCollection`).
- `dup_contexts.csv` (+ `.md` guide): one pair of context crops found together in a group
  per row, `context_a, context_b, same, groups`. Mandatory review.
- `dup_check.csv` (+ `.md` guide): one pair of similar groups per row, identified by a
  question of each, `question_a, question_b, score, answer_score, same`. Optional review.

Only answered questions count. Each one is keyed as `"{extended stem} {base answer}"`;
questions with equal key form an `exact` group. Pairs of groups whose keys reach
`threshold` and whose answers reach `answer_threshold` are proposed in `dup_check.csv`.

Decisions are identified by ids, never by position: a rerun keeps the `manual` groups and
every decided row, and only adds the new pairs (D006). `--force` rebuilds from scratch.
The CSV files are the source of truth; the guides are regenerated with them.
"""

import csv
import difflib
import logging
import re
from collections import defaultdict
from collections.abc import Hashable, Iterable
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path, PurePosixPath

from pydantic import ValidationError
from rapidfuzz import process
from rapidfuzz.distance import Levenshtein

from opox.models.duplicates import DuplicateCollection, DuplicateGroup
from opox.models.questions import ExamCollection, Question
from opox.normalize import base_key, extended_key, similarity

THRESHOLD = 75.0
ANSWER_THRESHOLD = 95.0
CONTEXT_COLUMNS = ["context_a", "context_b", "same", "groups"]
CHECK_COLUMNS = ["question_a", "question_b", "score", "answer_score", "same"]
DECISIONS = {"y", "n", ""}

log = logging.getLogger(__name__)

type Pair = tuple[str, str]


@dataclass(frozen=True)
class DupPaths:
    questions: Path
    duplicates: Path
    contexts_sheet: Path
    contexts_guide: Path
    check_sheet: Path
    check_guide: Path

    @classmethod
    def of(cls, data_dir: Path, opposition: str) -> DupPaths:
        interim = data_dir / "interim" / opposition
        return cls(
            questions=data_dir / "processed" / opposition / "questions.json",
            duplicates=interim / "duplicates.json",
            contexts_sheet=interim / "dup_contexts.csv",
            contexts_guide=interim / "dup_contexts.md",
            check_sheet=interim / "dup_check.csv",
            check_guide=interim / "dup_check.md",
        )


# --- Questions and groups ----------------------------------------------------------------


def answer_text(q: Question) -> str:
    assert q.answer is not None
    return q.options[q.answer]


def question_key(q: Question) -> str:
    """Key of a question: extended stem and base answer (D011)."""
    return f"{extended_key(q.text)} {base_key(answer_text(q))}"


def recency(q: Question) -> tuple[int, str]:
    """Sort key, most recent first: latest year, ties by `question_id`."""
    return -int(q.question_id[:4]), q.question_id


def canonical(questions: Iterable[Question]) -> Question:
    """Most recent question (D011)."""
    return min(questions, key=recency)


def group_context(questions: Iterable[Question]) -> PurePosixPath | None:
    """Context of a group: that of its most recent question with context, if any."""
    with_context = [q for q in questions if q.context is not None]
    return canonical(with_context).context if with_context else None


def load_questions(path: Path) -> tuple[dict[str, Question], list[str]]:
    """Answered questions by id, or the errors that prevent reading them."""
    if not path.is_file():
        return {}, [f"file not found: {path}"]
    try:
        exams = ExamCollection.model_validate_json(path.read_text(encoding="utf-8"))
    except ValidationError as e:
        return {}, [f"invalid model in {path}\n{e}"]
    return {q.question_id: q for e in exams.root for q in e.questions if q.answer is not None}, []


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[Hashable, Hashable] = {}

    def find(self, x: Hashable) -> Hashable:
        root = x
        while (parent := self.parent.setdefault(root, root)) != root:
            root = parent
        while x != root:
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a: Hashable, b: Hashable) -> None:
        self.parent[self.find(a)] = self.find(b)


def make_groups(
    questions: dict[str, Question], manual: Iterable[Iterable[str]]
) -> tuple[list[DuplicateGroup], list[str]]:
    """Exact groups joined by the manual ones; also notes on unknown manual members."""
    by_key: dict[str, list[str]] = defaultdict(list)
    for qid, q in questions.items():
        by_key[question_key(q)].append(qid)
    uf = UnionFind()
    for ids in by_key.values():
        for qid in ids:
            uf.union(ids[0], qid)
    notes: list[str] = []
    for members in manual:
        known = [m for m in members if m in questions]
        notes += [
            f"manual member not answered or not found, dropped: {m}"
            for m in members
            if m not in known
        ]
        for qid in known[1:]:
            uf.union(known[0], qid)

    components: dict[Hashable, list[str]] = defaultdict(list)
    for qid in questions:
        components[uf.find(qid)].append(qid)
    exact = {frozenset(ids) for ids in by_key.values()}
    groups = [
        DuplicateGroup(members=sorted(ids), origin="exact" if frozenset(ids) in exact else "manual")
        for ids in components.values()
        if len(ids) > 1
    ]
    return sorted(groups, key=lambda g: g.members[0]), notes


def blocks_of(questions: dict[str, Question], groups: Iterable[DuplicateGroup]) -> list[list[str]]:
    """Every answered question in one block: the groups plus one block per unique question."""
    blocks = [list(g.members) for g in groups]
    grouped = {m for b in blocks for m in b}
    return blocks + [[qid] for qid in questions if qid not in grouped]


# --- Sheets ------------------------------------------------------------------------------


@dataclass(frozen=True)
class ContextRow:
    line: int
    pair: Pair
    same: str


@dataclass(frozen=True)
class CheckRow:
    line: int
    pair: Pair  # question ids, sorted
    score: float
    answer_score: float
    same: str


def _read_csv(path: Path, columns: list[str]) -> tuple[list[tuple[int, dict[str, str]]], list[str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != columns:
            return [], [f"{path}: columns must be {', '.join(columns)}"]
        return [
            (reader.line_num, {k: (v or "").strip() for k, v in row.items()}) for row in reader
        ], []


def read_contexts_sheet(path: Path) -> tuple[list[ContextRow], list[str]]:
    """Rows of `dup_contexts.csv` and their format errors."""
    raw, errors = _read_csv(path, CONTEXT_COLUMNS)
    rows = []
    for line, r in raw:
        same = r["same"].lower()
        if same not in DECISIONS:
            errors.append(f"{path.name} line {line}: same must be y, n or blank, got {same!r}")
            continue
        a, b = sorted((r["context_a"], r["context_b"]))
        rows.append(ContextRow(line, (a, b), same))
    return rows, errors


def read_check_sheet(path: Path) -> tuple[list[CheckRow], list[str]]:
    """Rows of `dup_check.csv` and their format errors."""
    raw, errors = _read_csv(path, CHECK_COLUMNS)
    rows = []
    for line, r in raw:
        same = r["same"].lower()
        if same not in DECISIONS:
            errors.append(f"{path.name} line {line}: same must be y, n or blank, got {same!r}")
            continue
        try:
            score, answer_score = float(r["score"]), float(r["answer_score"])
        except ValueError:
            errors.append(f"{path.name} line {line}: score and answer_score must be numbers")
            continue
        a, b = sorted((r["question_a"], r["question_b"]))
        rows.append(CheckRow(line, (a, b), score, answer_score, same))
    return rows, errors


def repeated_rows(rows: Iterable[ContextRow | CheckRow], name: str) -> list[str]:
    """Errors for rows whose pair already appeared in the sheet."""
    seen: dict[Pair, int] = {}
    errors = []
    for row in rows:
        if row.pair in seen:
            errors.append(f"{name} line {row.line}: pair repeated (line {seen[row.pair]})")
        seen.setdefault(row.pair, row.line)
    return errors


def context_pairs(
    questions: dict[str, Question], groups: Iterable[DuplicateGroup]
) -> dict[Pair, list[str]]:
    """Pairs of distinct crops found together in a group, with the canonicals of the groups."""
    pairs: dict[Pair, list[str]] = defaultdict(list)
    for g in groups:
        crops = sorted({str(c) for m in g.members if (c := questions[m].context) is not None})
        top = canonical(questions[m] for m in g.members).question_id
        for pair in combinations(crops, 2):
            pairs[pair].append(top)
    return dict(sorted(pairs.items()))


@dataclass(frozen=True)
class Candidate:
    pair: Pair  # canonical question ids of both blocks, sorted
    score: float
    answer_score: float


def find_candidates(
    questions: dict[str, Question],
    blocks: list[list[str]],
    threshold: float,
    answer_threshold: float,
) -> list[Candidate]:
    """Most similar pair of keys of every two blocks reaching both thresholds."""
    keys: list[str] = []
    answers: list[str] = []
    owner: list[int] = []
    for b, ids in enumerate(blocks):
        for key, qid in {question_key(questions[m]): m for m in ids}.items():
            keys.append(key)
            answers.append(base_key(answer_text(questions[qid])))
            owner.append(b)

    best: dict[tuple[int, int], tuple[float, float]] = {}
    for i, key in enumerate(keys):
        for _, score, j in process.extract(
            key,
            keys,
            scorer=Levenshtein.normalized_similarity,
            score_cutoff=threshold / 100,
            limit=None,
        ):
            if j <= i or owner[i] == owner[j]:
                continue
            answer_score = similarity(answers[i], answers[j])
            if answer_score < answer_threshold:
                continue
            bp = (min(owner[i], owner[j]), max(owner[i], owner[j]))
            best[bp] = max(best.get(bp, (0.0, 0.0)), (100 * score, answer_score))

    tops = [canonical(questions[m] for m in ids).question_id for ids in blocks]
    candidates = [
        Candidate(tuple(sorted((tops[a], tops[b]))), round(s, 1), round(ans, 1))
        for (a, b), (s, ans) in best.items()
    ]
    log.info("%d block(s), %d candidate pair(s)", len(blocks), len(candidates))
    return sorted(candidates, key=lambda c: (-c.score, c.pair))


def merge_check_rows(
    candidates: list[Candidate], old: list[CheckRow], block_of: dict[str, int]
) -> tuple[list[CheckRow], list[str]]:
    """New sheet rows: decided rows kept, joined `y` rows dropped, new candidates added."""
    rows: list[CheckRow] = []
    decided: set[tuple[int, int]] = set()
    notes: list[str] = []
    for r in old:
        if not r.same:
            continue
        a, b = r.pair
        if a not in block_of or b not in block_of:
            notes.append(
                f"decision dropped, question not answered or not found: {a}, {b} ({r.same})"
            )
            continue
        ba, bb = block_of[a], block_of[b]
        if ba == bb and r.same == "y":
            continue  # already joined
        rows.append(r)
        decided.add((min(ba, bb), max(ba, bb)))
    for c in candidates:
        ba, bb = block_of[c.pair[0]], block_of[c.pair[1]]
        if (min(ba, bb), max(ba, bb)) not in decided:
            rows.append(CheckRow(0, c.pair, c.score, c.answer_score, ""))
    return sorted(rows, key=lambda r: (-r.score, r.pair)), notes


def write_contexts_sheet(
    path: Path, pairs: dict[Pair, list[str]], decisions: dict[Pair, str]
) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CONTEXT_COLUMNS)
        for (a, b), groups in pairs.items():
            writer.writerow([a, b, decisions.get((a, b), ""), " ".join(groups)])


def write_check_sheet(path: Path, rows: list[CheckRow]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CHECK_COLUMNS)
        for r in rows:
            writer.writerow([*r.pair, f"{r.score:.1f}", f"{r.answer_score:.1f}", r.same])


# --- Guides ------------------------------------------------------------------------------

_MD_SPECIAL = re.compile(r"([\\`*_~\[\]<>|#])")


def _md(text: str) -> str:
    return _MD_SPECIAL.sub(r"\\\1", " ".join(text.split()))


def word_diff(a: str, b: str) -> str:
    """Words only in `a` as ~~x~~ and only in `b` as **x**, Markdown-escaped."""
    wa, wb = a.split(), b.split()
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, wa, wb, autojunk=False).get_opcodes():
        if op == "equal":
            out.append(_md(" ".join(wa[i1:i2])))
        if op in ("delete", "replace"):
            out.append(f"~~{_md(' '.join(wa[i1:i2]))}~~")
        if op in ("insert", "replace"):
            out.append(f"**{_md(' '.join(wb[j1:j2]))}**")
    return " ".join(out)


def write_contexts_guide(
    path: Path,
    opposition: str,
    questions: dict[str, Question],
    groups: list[DuplicateGroup],
    pairs: dict[Pair, list[str]],
) -> None:
    by_top = {canonical(questions[m] for m in g.members).question_id: g for g in groups}
    lines = [
        f"# Contexts of duplicate questions — {opposition}",
        "",
        f"Generated by `opox bank extract duplicates`; do not edit. {len(pairs)} pair(s) of context",
        "crops found together in a group of duplicate questions.",
        "",
        f"Fill in `same` in `{path.with_suffix('.csv').name}`: `y` if both crops are the same",
        "context, `n` otherwise. Mandatory. A pair marked `n` splits every group listed;",
        "questions without context stay with the most recent context.",
        "",
    ]
    image_dir = f"../../processed/{opposition}"
    for line, ((a, b), tops) in enumerate(pairs.items(), start=2):
        lines += [f"## Line {line} — `{a}` ↔ `{b}`", ""]
        for top in tops:
            ids = ", ".join(f"`{m}`" for m in by_top[top].members)
            lines.append(f"- {ids}: {_md(questions[top].text)}")
        lines += ["", f"![{a}]({image_dir}/{a}) ![{b}]({image_dir}/{b})", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_check_guide(
    path: Path,
    opposition: str,
    questions: dict[str, Question],
    blocks: list[list[str]],
    rows: list[CheckRow],
    thresholds: tuple[float, float],
) -> None:
    block_of = {m: ids for ids in blocks for m in ids}
    lines = [
        f"# Possible duplicate questions — {opposition}",
        "",
        f"Generated by `opox bank extract duplicates`; do not edit. {len(rows)} pair(s) of groups",
        f"with key similarity >= {thresholds[0]:g}% and answer similarity >= {thresholds[1]:g}%,",
        "most similar first.",
        "",
        f"Optionally, fill in `same` in `{path.with_suffix('.csv').name}`: `y` if both are the",
        "same question, `n` otherwise; then run `opox bank add duplicates`. Blank rows are ignored.",
        "Words only in the first question are ~~struck~~, only in the second **bold**.",
        "",
    ]
    for line, r in enumerate(rows, start=2):
        qa, qb = (questions[i] for i in r.pair)
        lines += [
            f"## Line {line} — {r.score:.1f}% · answer {r.answer_score:.1f}%",
            "",
            f"- **Groups**: {', '.join(f'`{m}`' for m in block_of[qa.question_id])}"
            f" ↔ {', '.join(f'`{m}`' for m in block_of[qb.question_id])}",
            f"- **Stem**: {word_diff(qa.text, qb.text)}",
            f"- **Answer**: {word_diff(answer_text(qa), answer_text(qb))}",
        ]
        crops = [str(q.context) for q in (qa, qb) if q.context is not None]
        if crops:
            lines.append(f"- **Contexts**: {', '.join(f'`{c}`' for c in crops)}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


# --- Commands ----------------------------------------------------------------------------


@dataclass(frozen=True)
class State:
    """Manual work to keep: manual groups and sheet decisions."""

    manual: list[list[str]]
    context_decisions: dict[Pair, str]
    check_rows: list[CheckRow]
    thresholds: tuple[float, float] | None


def read_state(paths: DupPaths) -> tuple[State | None, list[str]]:
    """Manual work of a previous run; an empty state if there is none."""
    if not paths.duplicates.exists():
        return State([], {}, [], None), []
    try:
        collection = DuplicateCollection.model_validate_json(
            paths.duplicates.read_text(encoding="utf-8")
        )
    except ValidationError as e:
        return None, [f"invalid model in {paths.duplicates}\n{e}"]
    errors: list[str] = []
    context_rows: list[ContextRow] = []
    check_rows: list[CheckRow] = []
    if paths.contexts_sheet.exists():
        context_rows, errs = read_contexts_sheet(paths.contexts_sheet)
        errors += errs + repeated_rows(context_rows, paths.contexts_sheet.name)
    if paths.check_sheet.exists():
        check_rows, errs = read_check_sheet(paths.check_sheet)
        errors += errs + repeated_rows(check_rows, paths.check_sheet.name)
    if errors:
        return None, errors
    return State(
        manual=[g.members for g in collection.groups if g.origin == "manual"],
        context_decisions={r.pair: r.same for r in context_rows if r.same},
        check_rows=check_rows,
        thresholds=(collection.threshold, collection.answer_threshold),
    ), []


def rebuild(
    paths: DupPaths,
    opposition: str,
    questions: dict[str, Question],
    state: State,
    thresholds: tuple[float, float],
) -> list[str]:
    """Write the groups, both sheets and both guides from the questions and the state."""
    groups, notes = make_groups(questions, state.manual)
    collection = DuplicateCollection(
        threshold=thresholds[0], answer_threshold=thresholds[1], groups=groups
    )
    paths.duplicates.parent.mkdir(parents=True, exist_ok=True)
    paths.duplicates.write_text(collection.model_dump_json(indent=2) + "\n", encoding="utf-8")

    pairs = context_pairs(questions, groups)
    notes += [
        f"context decision dropped, pair no longer in a group: {a}, {b} ({d})"
        for (a, b), d in state.context_decisions.items()
        if (a, b) not in pairs
    ]
    write_contexts_sheet(paths.contexts_sheet, pairs, state.context_decisions)
    write_contexts_guide(paths.contexts_guide, opposition, questions, groups, pairs)

    blocks = blocks_of(questions, groups)
    block_of = {m: b for b, ids in enumerate(blocks) for m in ids}
    candidates = find_candidates(questions, blocks, *thresholds)
    rows, dropped = merge_check_rows(candidates, state.check_rows, block_of)
    notes += dropped
    write_check_sheet(paths.check_sheet, rows)
    write_check_guide(paths.check_guide, opposition, questions, blocks, rows, thresholds)

    n_grouped = sum(len(g.members) for g in groups)
    n_manual = sum(g.origin == "manual" for g in groups)
    pending_contexts = sum(p not in state.context_decisions for p in pairs)
    pending_check = sum(not r.same for r in rows)
    return notes + [
        f"{len(questions)} answered question(s): {len(groups)} group(s) ({n_manual} manual) "
        f"with {n_grouped} question(s), {len(blocks)} unique -> {paths.duplicates}",
        f"{len(pairs)} context pair(s), {pending_contexts} pending (mandatory) -> "
        f"{paths.contexts_sheet}",
        f"{len(rows)} possible duplicate(s), {pending_check} pending (optional) -> "
        f"{paths.check_sheet}",
    ]


def extract_duplicates(
    data_dir: Path,
    opposition: str,
    force: bool = False,
    threshold: float | None = None,
    answer_threshold: float | None = None,
) -> tuple[bool, list[str]]:
    """Identify duplicates and write or update the sheets. Return (success, notes)."""
    paths = DupPaths.of(data_dir, opposition)
    questions, errors = load_questions(paths.questions)
    if errors:
        return False, errors
    if force:
        state, notes = (
            State([], {}, [], None),
            [
                f"rebuilding {p}"
                for p in (paths.duplicates, paths.contexts_sheet, paths.check_sheet)
                if p.exists()
            ],
        )
    else:
        state, errors = read_state(paths)
        if errors or state is None:
            return False, [*errors, "fix the problems above, or rebuild everything with --force"]
        notes = []
    stored = state.thresholds or (THRESHOLD, ANSWER_THRESHOLD)
    thresholds = (
        threshold if threshold is not None else stored[0],
        answer_threshold if answer_threshold is not None else stored[1],
    )
    log.info("%d answered question(s), thresholds %s", len(questions), thresholds)
    return True, notes + rebuild(paths, opposition, questions, state, thresholds)
