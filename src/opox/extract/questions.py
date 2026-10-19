"""Extract exam questions and answers from the exam and answer key PDFs (D009).

Inputs, for a given opposition:
- `raw/<opposition>/tests/<exam_id>T.pdf` and `<exam_id>R.pdf`: exam and answer key.
- `processed/<opposition>/rules.json`: expected parts and reserve lists of each call.

Output: `processed/<opposition>/questions.json`. Never overwritten unless forced (D006).

Numbering restarts at 1 in each part and each reserve list, so both PDFs are split into
the sections expected by the call rules on every numbering reset, instead of relying on
headers. Text shared by several questions (e.g. "44 a 49. En la siguiente tabla...",
"Responda las siguientes preguntas...") is skipped and reported as a preamble.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from opox.models.questions import Exam, ExamCollection, Question, make_question_id
from opox.models.rules import CallRules, CallRulesCollection
from opox.pdf import Line, Segment, Word, group_lines, read_lines, read_words

QUESTION_RE = re.compile(r"^(\d+)(\.)?(?(2)(?!\d)\s*|\s+)(.*)$")
OPTION_RE = re.compile(r"^([a-d])\)\s*(.*)$")
GROUP_INTRO_RE = re.compile(r"^\d+\s+a\s+\d+\.")
HEADER_RE = re.compile(r"^(primera|segunda)\s+parte$|^(preguntas\s+de\s+)?reserva$", re.IGNORECASE)
FOOTER_RE = re.compile(r"p[áa]gina\s+\d+\s+de\s+\d+|\bAUX\s*[-–]", re.IGNORECASE)
FOOTER_ZONE = 0.9  # footers lie below this fraction of the page height
COVER_MARKER = "No abra este cuestionario"
ANSWER_NUMBER_RE = re.compile(r"^(\d+)\.([A-Da-d])?$")
ANSWER_RE = re.compile(r"^([A-Da-d]|anulada)$", re.IGNORECASE)
OPTION_LETTERS = "abcd"
INDENT_TOLERANCE = 2.0  # pt; deeper indentation marks a continuation line
CONTINUATION_GAP = 13.0  # pt; max vertical step to a continuation line (questions are ~16 apart)
COLUMN_GAP = 40.0  # pt; min horizontal distance between answer key columns


@dataclass(frozen=True, slots=True)
class Section:
    part: int
    is_reserve: bool
    size: int


@dataclass(slots=True)
class _Draft:
    page: int
    number: int
    text: list[str]
    options: list[list[str]] = field(default_factory=list)
    option_x0: float = 0.0
    last_page: int = 0
    last_top: float = 0.0


def expected_sections(rules: CallRules) -> list[Section]:
    """Sections of an exam, in order: each part followed by its reserve list."""
    sections = []
    for part in rules.parts:
        sections.append(Section(part.number, False, part.n_questions))
        if part.n_reserve:
            sections.append(Section(part.number, True, part.n_reserve))
    return sections


def _join(parts: list[str]) -> str:
    text = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        text = f"{text}{part}" if text.endswith("-") or not text else f"{text} {part}"
    return re.sub(r"\s+", " ", text).strip()


def _merge_number(line: Line) -> list[Segment]:
    """Join a lone question number ("37.") with the text segment that follows it."""
    segs = list(line.segments)
    if len(segs) > 1 and re.fullmatch(r"\d+\.?", segs[0].text):
        segs[:2] = [Segment(segs[0].x0, f"{segs[0].text} {segs[1].text}")]
    return segs


class _ExamParser:
    """State machine over the lines of an exam PDF."""

    def __init__(self, exam_id: str, sections: list[Section]) -> None:
        self.exam_id = exam_id
        self.sections = sections
        self.section_index = -1
        self.last_number = 0  # last question number started in the current section
        self.results: list[list[_Draft]] = [[] for _ in sections]
        self.current: _Draft | None = None
        self.skipping = True  # before the first question, or inside a preamble
        self.notes: list[str] = []
        self.preamble: list[str] | None = None
        self.preamble_page = 0

    def _target_section(self, number: int) -> int | None:
        """Section a question number belongs to: the current one, the next one, or None."""
        if self.section_index >= 0 and number == self.last_number + 1:
            return self.section_index
        has_next = self.section_index + 1 < len(self.sections)
        if number == 1 and has_next and (self.section_index < 0 or self.last_number > 0):
            return self.section_index + 1
        return None

    def _close_question(self) -> None:
        if self.current is not None:
            self.results[self.section_index].append(self.current)
            self.current = None

    def _close_preamble(self) -> None:
        if self.preamble:
            text = _join(self.preamble)
            self.notes.append(f"{self.exam_id} p{self.preamble_page}: shared preamble: {text[:90]}")
        self.preamble = None

    def _start_preamble(self, line: Line) -> None:
        self._close_question()
        self.skipping = True
        if HEADER_RE.match(line.text.strip()):
            return
        self.preamble = [line.text]
        self.preamble_page = line.page

    def feed(self, line: Line) -> None:
        segs = _merge_number(line)
        first = segs[0].text.strip()

        if GROUP_INTRO_RE.match(first):
            self._close_preamble()
            self._start_preamble(line)
            return

        match = QUESTION_RE.match(first)
        target = self._target_section(int(match[1])) if match else None
        # A number without its dot is only trusted when it continues the current section.
        if match and target is not None and (match[2] or target == self.section_index):
            self._close_question()
            self._close_preamble()
            self.section_index = target
            self.last_number = int(match[1])
            self.skipping = False
            self.current = _Draft(
                line.page, self.last_number, [match[3]], last_page=line.page, last_top=line.top
            )
            segs = segs[1:]
            if not segs:
                return

        if self.skipping:
            if self.preamble is not None:
                self.preamble.append(line.text)
            return

        draft = self.current
        assert draft is not None
        if len(draft.options) == 4 and not self._continues_last_option(draft, line):
            self._start_preamble(line)
            return
        for seg in segs:
            option = OPTION_RE.match(seg.text.strip())
            if (
                option
                and len(draft.options) < 4
                and option[1] == OPTION_LETTERS[len(draft.options)]
            ):
                draft.options.append([option[2]])
                draft.option_x0 = seg.x0
            elif draft.options:
                draft.options[-1].append(seg.text)
            else:
                draft.text.append(seg.text)
        draft.last_page, draft.last_top = line.page, line.top

    @staticmethod
    def _continues_last_option(draft: _Draft, line: Line) -> bool:
        """Whether a line after option d) still belongs to it: indented, close and same page."""
        return (
            line.page == draft.last_page
            and line.top - draft.last_top < CONTINUATION_GAP
            and line.x0 > draft.option_x0 + INDENT_TOLERANCE
            and not HEADER_RE.match(line.text.strip())
        )

    def finish(self) -> list[list[_Draft]]:
        self._close_question()
        self._close_preamble()
        return self.results


def parse_exam(
    path: Path, exam_id: str, sections: list[Section]
) -> tuple[list[list[_Draft]], list[str]]:
    """Split an exam PDF into question drafts per section."""
    lines = read_lines(path)
    cover_pages = {ln.page for ln in lines if COVER_MARKER in ln.text}
    parser = _ExamParser(exam_id, sections)
    for line in lines:
        is_footer = line.top > line.page_height * FOOTER_ZONE and FOOTER_RE.search(line.text)
        if line.page in cover_pages or is_footer:
            continue
        parser.feed(line)
    return parser.finish(), parser.notes


@dataclass(frozen=True, slots=True)
class AnswerMark:
    """A "number. letter" pair found in an answer key, with its position."""

    page: int
    x0: float
    top: float
    number: int
    answer: int | None  # None = annulled


def read_answer_marks(words: list[Word]) -> list[AnswerMark]:
    """Find answer pairs ("12. b", "12.b", "12. ANULADA") among the words of a page."""
    marks: list[AnswerMark] = []
    for line in group_lines(words):
        for i, word in enumerate(line):
            match = ANSWER_NUMBER_RE.match(word.text)
            if not match:
                continue
            letter = match[2]
            if letter is None:
                if i + 1 >= len(line) or not ANSWER_RE.match(line[i + 1].text):
                    continue
                letter = line[i + 1].text
            answer = None if letter.lower() == "anulada" else OPTION_LETTERS.index(letter.lower())
            marks.append(AnswerMark(word.page, word.x0, word.top, int(match[1]), answer))
    return marks


def order_by_columns(marks: list[AnswerMark]) -> list[AnswerMark]:
    """Reading order of a multi-column answer key: page, column left to right, top to bottom."""
    ordered: list[AnswerMark] = []
    for page in sorted({m.page for m in marks}):
        columns: list[list[AnswerMark]] = []
        for mark in sorted((m for m in marks if m.page == page), key=lambda m: m.x0):
            if columns and mark.x0 - columns[-1][-1].x0 < COLUMN_GAP:
                columns[-1].append(mark)
            else:
                columns.append([mark])
        for column in columns:
            ordered.extend(sorted(column, key=lambda m: m.top))
    return ordered


def split_answers(
    marks: list[AnswerMark], sections: list[Section]
) -> tuple[list[list[int | None]], list[int]]:
    """Assign ordered answers to sections on each numbering reset; return unexpected numbers."""
    result: list[list[int | None]] = [[] for _ in sections]
    unexpected: list[int] = []
    index = -1
    for mark in marks:
        if mark.number == 1 and index + 1 < len(sections):
            index += 1
        elif index < 0 or mark.number != len(result[index]) + 1:
            unexpected.append(mark.number)
            continue
        result[index].append(mark.answer)
    return result, unexpected


def parse_answer_key(
    path: Path, sections: list[Section]
) -> tuple[list[list[int | None]], list[str]]:
    """Read the answers of each section from an answer key PDF (None = annulled)."""
    marks = [m for page in read_words(path) for m in read_answer_marks(page)]
    answers, unexpected = split_answers(order_by_columns(marks), sections)
    return answers, [f"{path.stem}: unexpected answer number {n}" for n in unexpected]


def build_exam(exam_id: str, rules: CallRules, tests_dir: Path) -> tuple[Exam | None, list[str]]:
    """Parse one exam and its answer key into an Exam, plus review notes."""
    sections = expected_sections(rules)
    exam_pdf = tests_dir / f"{exam_id}T.pdf"
    key_pdf = tests_dir / f"{exam_id}R.pdf"
    if not key_pdf.is_file():
        return None, [f"{exam_id}: missing answer key {key_pdf.name}"]

    drafts, notes = parse_exam(exam_pdf, exam_id, sections)
    answers, key_notes = parse_answer_key(key_pdf, sections)
    notes += key_notes

    questions: list[Question] = []
    for section, section_drafts, section_answers in zip(sections, drafts, answers, strict=True):
        label = f"part {section.part}{' reserve' if section.is_reserve else ''}"
        if len(section_drafts) != section.size:
            notes.append(
                f"{exam_id}: {label}: {len(section_drafts)} questions, expected {section.size}"
            )
        if len(section_answers) != section.size:
            notes.append(
                f"{exam_id}: {label}: {len(section_answers)} answers, expected {section.size}"
            )
        for i, draft in enumerate(section_drafts):
            qid = make_question_id(exam_id, section.part, section.is_reserve, draft.number)
            if len(draft.options) != 4:
                notes.append(f"{qid} (p{draft.page}): {len(draft.options)} options found, skipped")
                continue
            if i >= len(section_answers):
                notes.append(f"{qid}: no answer found, skipped")
                continue
            questions.append(
                Question(
                    question_id=qid,
                    part=section.part,
                    is_reserve=section.is_reserve,
                    number=draft.number,
                    text=_join(draft.text),
                    options=[_join(o) for o in draft.options],
                    answer=section_answers[i],
                )
            )

    if not questions:
        return None, notes + [f"{exam_id}: no questions extracted"]
    exam = Exam(
        exam_id=exam_id,
        call_id=rules.call_id,
        model=exam_id[-1],
        source=PurePosixPath("tests", exam_pdf.name),
        key_source=PurePosixPath("tests", key_pdf.name),
        questions=questions,
    )
    return exam, notes


def extract_questions(
    data_dir: Path, opposition: str, force: bool = False
) -> tuple[bool, list[str]]:
    """Extract all exams of an opposition. Return (written, review notes)."""
    out_path = data_dir / "processed" / opposition / "questions.json"
    if out_path.exists() and not force:
        return False, [f"{out_path} already exists; use --force to overwrite it"]

    rules_path = data_dir / "processed" / opposition / "rules.json"
    rules = CallRulesCollection.model_validate_json(rules_path.read_text(encoding="utf-8"))
    rules_by_id = {r.call_id: r for r in rules.root}
    tests_dir = data_dir / "raw" / opposition / "tests"

    exams: list[Exam] = []
    notes: list[str] = []
    for exam_pdf in sorted(tests_dir.glob("*T.pdf")):
        exam_id = exam_pdf.stem[:-1]
        call_rules = rules_by_id.get(exam_id[:5])
        if call_rules is None:
            notes.append(f"{exam_id}: call {exam_id[:5]} not found in {rules_path}")
            continue
        exam, exam_notes = build_exam(exam_id, call_rules, tests_dir)
        notes += exam_notes
        if exam is not None:
            exams.append(exam)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    if force and out_path.exists():
        notes.insert(0, f"overwriting {out_path}")
    out_path.write_text(ExamCollection(exams).model_dump_json(indent=2) + "\n", encoding="utf-8")
    return True, notes
