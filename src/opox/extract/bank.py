"""Build the question bank from the extracted questions (D010).

Inputs, for a given opposition: `processed/<opposition>/questions.json`.

Outputs, never overwritten unless forced (D006):
- `processed/<opposition>/bank.json`: entries that need no manual decision.
- `interim/<opposition>/bank_merges.csv`: candidate merges between question groups,
  `question_a, question_b, reason, merge, note`.
- `interim/<opposition>/bank_contexts.csv`: candidate equivalent context crops,
  `context_a, context_b, same`.
- `interim/<opposition>/bank_review.md`: pending candidates, side by side, for review.

Questions are first grouped when text, answer, option set and context crop are equal:
the text after folding (`fold`), answer and options after a conservative normalization
(`normalize`). Groups whose text and answer are similar (folded and
compared with `rapidfuzz`) become candidates for manual review. Groups linked by any
candidate stay out of the bank until every candidate between them is decided; see
`resolve_bank`, shared with `opox add bank`.
"""

import csv
import difflib
import logging
import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from rapidfuzz import fuzz, process

from opox.models.bank import BankQuestion, QuestionBank
from opox.models.questions import ExamCollection, Question

SIMILARITY_THRESHOLD = 0.85
MERGE_COLUMNS = ["question_a", "question_b", "reason", "merge", "note"]
CONTEXT_COLUMNS = ["context_a", "context_b", "same"]
DECISIONS = {"y", "n", ""}

log = logging.getLogger(__name__)

_QUOTES = str.maketrans({"“": '"', "”": '"', "«": '"', "»": '"', "‘": "'", "’": "'"})
_DASHES = re.compile(r"[‐-―−]")


@dataclass(frozen=True)
class BankPaths:
    questions: Path
    bank: Path
    merges: Path
    contexts: Path
    review: Path

    @classmethod
    def of(cls, data_dir: Path, opposition: str) -> BankPaths:
        processed = data_dir / "processed" / opposition
        interim = data_dir / "interim" / opposition
        return cls(
            questions=processed / "questions.json",
            bank=processed / "bank.json",
            merges=interim / "bank_merges.csv",
            contexts=interim / "bank_contexts.csv",
            review=interim / "bank_review.md",
        )


def normalize(s: str) -> str:
    """Conservative normalization for equality: keeps case, accents and punctuation."""
    s = _DASHES.sub("-", unicodedata.normalize("NFKC", s).translate(_QUOTES))
    return re.sub(r"\s+", " ", s).strip().rstrip(".").rstrip()


def fold(s: str) -> str:
    """Aggressive normalization for similarity: no case, accents or punctuation."""
    s = unicodedata.normalize("NFKD", s.casefold())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s)).strip()


def recency(question_id: str) -> tuple[str, str, str]:
    """Sort key: call year, then exam_id, then question_id."""
    exam_id = question_id.split("-")[0]
    return exam_id[:4], exam_id, question_id


@dataclass(frozen=True)
class Group:
    """Questions equal after normalization; `rep` is the most recent one."""

    questions: tuple[Question, ...]

    @property
    def rep(self) -> Question:
        return max(self.questions, key=lambda q: recency(q.question_id))

    @property
    def content(self) -> tuple[str, str, frozenset[str]]:
        """The group key without context."""
        return content_key(self.rep)


def content_key(q: Question) -> tuple[str, str, frozenset[str]]:
    """Folded text, normalized answer and normalized option set.

    The text is folded because case, accents or punctuation in a statement do not change
    the question; options keep them, as they matter in spelling questions.
    """
    assert q.answer is not None
    return fold(q.text), normalize(q.options[q.answer]), frozenset(map(normalize, q.options))


def exact_groups(exams: ExamCollection) -> list[Group]:
    """Group answered questions by normalized content and context crop."""
    buckets: dict[tuple, list[Question]] = defaultdict(list)
    for exam in exams.root:
        for q in exam.questions:
            if q.answer is None:
                continue
            buckets[(*content_key(q), q.context)].append(q)
    groups = [Group(tuple(qs)) for qs in buckets.values()]
    return sorted(groups, key=lambda g: g.rep.question_id)


def find_candidates(
    groups: list[Group], threshold: float = SIMILARITY_THRESHOLD
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Return blank merge and context rows for groups with similar text and answer."""
    texts = [fold(g.rep.text) for g in groups]
    answers = [fold(g.rep.options[g.rep.answer]) for g in groups]  # type: ignore[index]
    cutoff = threshold * 100
    similar = (
        (i, j)
        for i, text in enumerate(texts)
        for _, _, j in process.extract(
            text, texts, scorer=fuzz.ratio, score_cutoff=cutoff, limit=None
        )
    )
    merges: dict[tuple[str, str], str] = {}
    contexts: set[tuple[str, str]] = set()
    for i, j in similar:
        if i >= j or fuzz.ratio(answers[i], answers[j]) < cutoff:
            continue
        a, b = groups[i], groups[j]
        (text_a, answer_a, options_a), (text_b, answer_b, options_b) = a.content, b.content
        ctx_a, ctx_b = a.rep.context, b.rep.context
        if (text_a, answer_a, options_a) == (text_b, answer_b, options_b) and ctx_a and ctx_b:
            contexts.add(tuple(sorted((str(ctx_a), str(ctx_b)))))  # type: ignore[arg-type]
            continue
        if text_a != text_b:
            reason = "text"
        elif answer_a != answer_b:
            reason = "answer"
        elif options_a != options_b:
            reason = "options"
        else:
            reason = "context"
        pair = tuple(sorted((a.rep.question_id, b.rep.question_id)))
        merges[pair] = reason  # type: ignore[index]
    merge_rows = [
        {"question_a": qa, "question_b": qb, "reason": r, "merge": "", "note": ""}
        for (qa, qb), r in sorted(merges.items())
    ]
    context_rows = [{"context_a": ca, "context_b": cb, "same": ""} for ca, cb in sorted(contexts)]
    return merge_rows, context_rows


def make_entry(questions: Iterable[Question]) -> BankQuestion:
    """Build a bank entry from all appearances of one question."""
    ordered = sorted(questions, key=lambda q: recency(q.question_id), reverse=True)
    rep = ordered[0]
    assert rep.answer is not None
    answers = {normalize(q.options[q.answer]) for q in ordered}  # type: ignore[index]
    seen: set[str] = set()
    distractors: list[str] = []
    for q in ordered:
        for i, option in enumerate(q.options):
            key = normalize(option)
            if i == q.answer or key in answers or key in seen:
                continue
            seen.add(key)
            distractors.append(option)
    return BankQuestion(
        bank_id=rep.question_id,
        sources=sorted(q.question_id for q in ordered),
        text=rep.text,
        context=rep.context,
        answer=rep.options[rep.answer],
        distractors=distractors,
    )


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


@dataclass
class Resolution:
    entries: list[BankQuestion]
    pending: int  # blank decisions in the sheets
    errors: list[str]


def resolve_bank(
    groups: list[Group], merge_rows: list[dict[str, str]], context_rows: list[dict[str, str]]
) -> Resolution:
    """Turn groups and sheet decisions into bank entries.

    Groups linked by sheet rows form components; a component yields entries only when
    all its rows are decided. Groups joined by `y` are merged; an `n` between groups
    that end up merged anyway is reported as a conflict.
    """
    errors: list[str] = []
    by_question = {q.question_id: i for i, g in enumerate(groups) for q in g.questions}
    by_context: dict[str, list[int]] = defaultdict(list)
    for i, g in enumerate(groups):
        if g.rep.context is not None:
            by_context[str(g.rep.context)].append(i)

    edges: list[tuple[int, int, str, str]] = []  # (group, group, decision, row label)
    pending = 0
    for line, row in enumerate(merge_rows, start=2):
        label = f"bank_merges.csv line {line}"
        decision = row["merge"].lower()
        if decision not in DECISIONS:
            errors.append(f"{label}: merge must be y, n or blank, got {row['merge']!r}")
            continue
        ends = [by_question.get(row[c]) for c in ("question_a", "question_b")]
        if None in ends:
            errors.append(
                f"{label}: unknown or annulled question in {row['question_a']}, {row['question_b']}"
            )
            continue
        pending += decision == ""
        edges.append((ends[0], ends[1], decision, label))  # type: ignore[arg-type]
    for line, row in enumerate(context_rows, start=2):
        label = f"bank_contexts.csv line {line}"
        decision = row["same"].lower()
        if decision not in DECISIONS:
            errors.append(f"{label}: same must be y, n or blank, got {row['same']!r}")
            continue
        linked = [
            (i, j)
            for i in by_context.get(row["context_a"], [])
            for j in by_context.get(row["context_b"], [])
            if groups[i].content == groups[j].content
        ]
        if not linked:
            errors.append(f"{label}: no questions differ only by these contexts")
            continue
        pending += decision == ""
        edges.extend((i, j, decision, label) for i, j in linked)

    components = _UnionFind(len(groups))
    for i, j, _, _ in edges:
        components.union(i, j)
    edges_by_component: dict[int, list[tuple[int, int, str, str]]] = defaultdict(list)
    for edge in edges:
        edges_by_component[components.find(edge[0])].append(edge)
    members: dict[int, list[int]] = defaultdict(list)
    for i in range(len(groups)):
        members[components.find(i)].append(i)

    entries: list[BankQuestion] = []
    for root, nodes in members.items():
        component_edges = edges_by_component.get(root, [])
        if any(d == "" for _, _, d, _ in component_edges):
            continue
        merged = _UnionFind(len(groups))
        for i, j, d, _ in component_edges:
            if d == "y":
                merged.union(i, j)
        conflicts = [
            label
            for i, j, d, label in component_edges
            if d == "n" and merged.find(i) == merged.find(j)
        ]
        if conflicts:
            errors.extend(f"{c}: marked n, but merged through other decisions" for c in conflicts)
            continue
        final: dict[int, list[Question]] = defaultdict(list)
        for i in nodes:
            final[merged.find(i)].extend(groups[i].questions)
        entries.extend(make_entry(qs) for qs in final.values())

    return Resolution(sorted(entries, key=lambda e: e.bank_id), pending, errors)


def read_rows(path: Path, columns: list[str]) -> tuple[list[dict[str, str]], list[str]]:
    """Rows of a control sheet with stripped values, or errors if malformed."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != columns:
            return [], [f"{path}: columns must be {', '.join(columns)}"]
        return [{k: (v or "").strip() for k, v in row.items()} for row in reader], []


def write_rows(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_bank(path: Path, entries: list[BankQuestion]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bank = QuestionBank(sorted(entries, key=lambda e: e.bank_id))
    path.write_text(bank.model_dump_json(indent=2) + "\n", encoding="utf-8")


def load_groups(questions_path: Path) -> list[Group]:
    exams = ExamCollection.model_validate_json(questions_path.read_text(encoding="utf-8"))
    return exact_groups(exams)


# --- Review report ---------------------------------------------------------------------


def _md(s: str) -> str:
    return re.sub(r"([\\`*_])", r"\\\1", s)


def _diff_words(a: str, b: str) -> tuple[str, str]:
    """Both strings with the words not shared with the other in bold."""
    wa, wb = a.split(), b.split()
    out_a: list[str] = []
    out_b: list[str] = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, wa, wb, autojunk=False).get_opcodes():
        chunk_a, chunk_b = _md(" ".join(wa[i1:i2])), _md(" ".join(wb[j1:j2]))
        if op == "equal":
            out_a.append(chunk_a)
            out_b.append(chunk_b)
        else:
            if chunk_a:
                out_a.append(f"**{chunk_a}**")
            if chunk_b:
                out_b.append(f"**{chunk_b}**")
    return " ".join(out_a), " ".join(out_b)


def _image(context: PurePosixPath | str | None, opposition: str) -> str:
    if context is None:
        return "_(sin contexto)_"
    return f"![{context}](../../processed/{opposition}/{context})"


def _question_block(g: Group, other: Group, opposition: str) -> list[str]:
    q, o = g.rep, other.rep
    text, _ = _diff_words(q.text, o.text)
    answer, _ = _diff_words(q.options[q.answer], o.options[o.answer])  # type: ignore[index]
    other_options = {normalize(x) for x in o.options}
    sources = ", ".join(sorted(x.question_id for x in g.questions))
    lines = [f"**{q.question_id}** ({sources})", "", text, "", f"- Respuesta: {answer}"]
    for i, option in enumerate(q.options):
        if i == q.answer:
            continue
        mark = "**" if normalize(option) not in other_options else ""
        lines.append(f"- {mark}{_md(option)}{mark}")
    lines += ["", _image(q.context, opposition), ""]
    return lines


def write_review(
    path: Path,
    opposition: str,
    groups: list[Group],
    merge_rows: list[dict[str, str]],
    context_rows: list[dict[str, str]],
) -> int:
    """Write the pending rows side by side; return how many were written."""
    by_question = {q.question_id: g for g in groups for q in g.questions}
    by_context: dict[str, list[Group]] = defaultdict(list)
    for g in groups:
        if g.rep.context is not None:
            by_context[str(g.rep.context)].append(g)

    lines = [
        f"# Revisión de la batería de {opposition}",
        "",
        "Generado por `opox`; no editar. Las decisiones se toman en `bank_merges.csv` y",
        "`bank_contexts.csv`. En negrita, lo que difiere entre ambas versiones.",
        "",
    ]
    pending_merges = [r for r in merge_rows if r["merge"] == ""]
    pending_contexts = [r for r in context_rows if r["same"] == ""]
    lines += [f"## Fusiones pendientes ({len(pending_merges)})", ""]
    for row in pending_merges:
        a, b = by_question.get(row["question_a"]), by_question.get(row["question_b"])
        lines += [f"### {row['question_a']} ↔ {row['question_b']} ({row['reason']})", ""]
        if a is None or b is None:
            lines += ["_(pregunta desconocida)_", ""]
            continue
        lines += _question_block(a, b, opposition) + _question_block(b, a, opposition)
    lines += [f"## Contextos pendientes ({len(pending_contexts)})", ""]
    for row in pending_contexts:
        ca, cb = row["context_a"], row["context_b"]
        lines += [f"### {ca} ↔ {cb}", ""]
        texts = sorted({g.rep.text for g in by_context.get(ca, [])})
        lines += [f"- {_md(t)}" for t in texts] + [""]
        lines += [_image(ca, opposition), "", _image(cb, opposition), ""]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return len(pending_merges) + len(pending_contexts)


# --- Command -----------------------------------------------------------------------------


def extract_bank(
    data_dir: Path, opposition: str, force: bool = False, threshold: float = SIMILARITY_THRESHOLD
) -> tuple[bool, list[str]]:
    """Build the bank, deferring doubtful cases to the control sheets. Return (written, notes)."""
    paths = BankPaths.of(data_dir, opposition)
    if not paths.questions.is_file():
        return False, [f"file not found: {paths.questions}"]
    existing = [p for p in (paths.merges, paths.contexts, paths.bank) if p.exists()]
    if existing and not force:
        return False, [f"{p} already exists" for p in existing] + [
            "use --force to overwrite them, losing any decision taken in the sheets"
        ]

    groups = load_groups(paths.questions)
    log.info("%d exact group(s); looking for candidates (threshold %.2f)", len(groups), threshold)
    merge_rows, context_rows = find_candidates(groups, threshold)
    resolution = resolve_bank(groups, merge_rows, context_rows)
    if resolution.errors:  # rows come from code, so this would be a bug
        return False, resolution.errors

    notes = [f"overwriting {p}" for p in existing]
    write_rows(paths.merges, MERGE_COLUMNS, merge_rows)
    write_rows(paths.contexts, CONTEXT_COLUMNS, context_rows)
    write_bank(paths.bank, resolution.entries)
    write_review(paths.review, opposition, groups, merge_rows, context_rows)
    deferred = sum(len(g.questions) for g in groups) - sum(
        len(e.sources) for e in resolution.entries
    )
    notes += [
        f"{len(resolution.entries)} entries written to {paths.bank}",
        f"{deferred} question(s) deferred: {len(merge_rows)} merge(s) in {paths.merges}, "
        f"{len(context_rows)} context pair(s) in {paths.contexts}",
        f"review them in {paths.review}, then run `opox add bank`",
    ]
    return True, notes
