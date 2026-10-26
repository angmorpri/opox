"""Members, review cases and resolution of the deduplication stages (D011).

A stage compares the answered questions within blocks: a single block in `answers`,
one per answer group of `dedup_answers.json` in `stems`. Within a block, questions with
equal key form a member; members whose keys are similar (>= the stage threshold) are
linked, and linked members, directly or through others, form a review case. The review
sheet labels the members of each case; members sharing a label are joined into a group.
"""

import logging
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from itertools import combinations

from rapidfuzz import process
from rapidfuzz.distance import Levenshtein

from opox.dedup.normalize import base_key, extended_key, similarity
from opox.models.dedup import DedupCollection, DedupGroup, DedupMember
from opox.models.questions import ExamCollection, Question

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Stage:
    name: str
    threshold: float  # minimum similarity for review, 0-100
    key: Callable[[Question], str]
    text: Callable[[Question], str]  # shown in the sheet and the guide


def answer_text(q: Question) -> str:
    assert q.answer is not None
    return q.options[q.answer]


ANSWERS = Stage("answers", 70, lambda q: base_key(answer_text(q)), answer_text)
STEMS = Stage("stems", 75, lambda q: extended_key(q.text), lambda q: q.text)
STAGES = {s.name: s for s in (ANSWERS, STEMS)}


def recency(q: Question) -> tuple[int, str]:
    """Sort key, most recent first: latest year, ties by `question_id`."""
    return -int(q.question_id[:4]), q.question_id


def canonical(questions: Iterable[Question]) -> Question:
    """Most recent question (D011)."""
    return min(questions, key=recency)


@dataclass(frozen=True)
class Member:
    """Questions of a block with equal key, sorted by `question_id`."""

    key: str
    block: int
    questions: tuple[Question, ...]

    @property
    def ids(self) -> str:
        """Identity in the review sheet."""
        return ", ".join(q.question_id for q in self.questions)


@dataclass(frozen=True)
class Case:
    """Members linked by similarity; `similarities` maps index pairs (i < j) to 0-100."""

    members: tuple[Member, ...]
    similarities: dict[tuple[int, int], float]

    def best(self, i: int) -> float:
        """Highest similarity of member `i` to any other."""
        return max(s for pair, s in self.similarities.items() if i in pair)


def answered(exams: ExamCollection) -> list[Question]:
    return [q for e in exams.root for q in e.questions if q.answer is not None]


def answer_blocks(questions: list[Question], answers: DedupCollection) -> list[list[Question]]:
    """One block per answer group, assuming both cover the same questions."""
    by_id = {q.question_id: q for q in questions}
    return [[by_id[s] for s in g.sources] for g in answers.root]


def build_members(blocks: list[list[Question]], stage: Stage) -> list[Member]:
    """Members of every block, sorted by their first question."""
    members = []
    for b, block in enumerate(blocks):
        by_key: dict[str, list[Question]] = defaultdict(list)
        for q in block:
            by_key[stage.key(q)].append(q)
        members += [
            Member(k, b, tuple(sorted(qs, key=lambda q: q.question_id))) for k, qs in by_key.items()
        ]
    return sorted(members, key=lambda m: m.questions[0].question_id)


def find_cases(members: list[Member], stage: Stage) -> list[Case]:
    """Review cases, least similar first; members by size, then first question."""
    by_block: dict[int, list[Member]] = defaultdict(list)
    for m in members:
        by_block[m.block].append(m)

    cases = []
    for block in by_block.values():
        keys = [m.key for m in block]
        links = _UnionFind(len(block))
        for i, key in enumerate(keys):
            for _, _, j in process.extract(
                key,
                keys,
                scorer=Levenshtein.normalized_similarity,
                score_cutoff=stage.threshold / 100,
                limit=None,
            ):
                if j > i:
                    links.union(i, j)
        for component in links.components():
            if len(component) < 2:
                continue
            case_members = sorted(
                (block[i] for i in component),
                key=lambda m: (-len(m.questions), m.questions[0].question_id),
            )
            pairs = {
                (i, j): similarity(a.key, b.key)
                for (i, a), (j, b) in combinations(enumerate(case_members), 2)
            }
            cases.append(Case(tuple(case_members), pairs))
    log.info("%d %s member(s), %d case(s) to review", len(members), stage.name, len(cases))
    return sorted(cases, key=lambda c: (min(c.similarities.values()), c.members[0].ids))


class _UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, i: int) -> int:
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, i: int, j: int) -> None:
        self.parent[self.find(i)] = self.find(j)

    def components(self) -> list[list[int]]:
        groups: dict[int, list[int]] = defaultdict(list)
        for i in range(len(self.parent)):
            groups[self.find(i)].append(i)
        return list(groups.values())


# --- Resolution --------------------------------------------------------------------------


@dataclass(frozen=True)
class Row:
    """A review sheet row; `line` is its line number in the file."""

    line: int
    case: str
    member: str
    group: str
    questions: str


@dataclass
class Resolution:
    collection: DedupCollection | None  # None if there are errors
    pending: int = 0  # rows without label
    stale: list[str] = field(default_factory=list)  # rows whose member no longer exists
    missing: list[str] = field(default_factory=list)  # case members without row
    errors: list[str] = field(default_factory=list)


def make_collection(groups: Iterable[Iterable[Member]]) -> DedupCollection:
    """Collection from sets of joined members, sorted as the model requires."""
    result = []
    for group in groups:
        members = sorted(group, key=lambda m: m.questions[0].question_id)
        result.append(
            DedupGroup(
                canonical=canonical(q for m in members for q in m.questions).question_id,
                members=[
                    DedupMember(key=m.key, sources=[q.question_id for q in m.questions])
                    for m in members
                ],
            )
        )
    return DedupCollection(sorted(result, key=lambda g: g.canonical))


def resolve(members: list[Member], cases: list[Case], rows: list[Row]) -> Resolution:
    """Join the members sharing a label in the sheet; the rest stay alone.

    Labels are global to the sheet, but a label cannot span several cases nor, in
    `stems`, several answer groups.
    """
    res = Resolution(None)
    by_ids = {m.ids: i for i, m in enumerate(members)}
    seen: dict[str, int] = {}
    labels: dict[str, list[tuple[Row, int]]] = defaultdict(list)
    for row in rows:
        if row.questions in seen:
            res.errors.append(
                f"line {row.line}: member {row.questions} repeated (line {seen[row.questions]})"
            )
            continue
        seen[row.questions] = row.line
        if row.questions not in by_ids:
            res.stale.append(f"line {row.line}: no member with questions {row.questions}")
            continue
        if not row.group:
            res.pending += 1
            continue
        labels[row.group].append((row, by_ids[row.questions]))

    in_case = {m.ids for c in cases for m in c.members}
    res.missing = sorted(in_case - set(seen))

    joined = _UnionFind(len(members))
    for label, entries in labels.items():
        lines = ", ".join(str(r.line) for r, _ in entries)
        if len({r.case for r, _ in entries}) > 1:
            res.errors.append(f"group {label!r} spans several cases (lines {lines})")
        elif len({members[i].block for _, i in entries}) > 1:
            res.errors.append(f"group {label!r} spans several answer groups (lines {lines})")
        else:
            for _, i in entries[1:]:
                joined.union(entries[0][1], i)
    if not res.errors:
        res.collection = make_collection(
            [members[i] for i in component] for component in joined.components()
        )
    return res
