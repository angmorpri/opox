"""Detect question contexts (images and tables) in exam PDFs and crop them (D005).

Inputs, for a given opposition:
- `raw/<opposition>/tests/<exam_id>T.pdf`: exams.
- `processed/<opposition>/rules.json`: expected parts and reserve lists of each call.

Outputs:
- `processed/<opposition>/contexts/<exam_id>_p<page>.png`: one crop per context.
- `interim/<opposition>/contexts.csv`: control sheet, `exam_id, page, first, last`.

Exams with a row or a crop are already covered and left as they are; only the other exams
are scanned and their contexts appended. Both are rebuilt from scratch only if forced (D006).

A page holds a context if it has a large embedded image or a drawn table (many edges).
The crop spans the page width, from the end of the previous question to the start of the
next one. `last` comes from an explicit "N a M." range; otherwise it is estimated as the
last consecutive question on the same page, and reported for review.
"""

import csv
import logging
import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber
from pdfplumber.page import Page

from opox.extract.questions import (
    FOOTER_ZONE,
    _Draft,
    expected_sections,
    parse_exam_lines,
    read_exam_lines,
)
from opox.models.questions import make_question_id
from opox.models.rules import CallRules, CallRulesCollection
from opox.pdf import Line

MIN_IMAGE_WIDTH = 200.0  # pt; smaller images are logos or decorations
MIN_TABLE_EDGES = 40  # rects + lines; cover and instruction pages have fewer
TOP_MARGIN = 20.0  # pt; crop start when no question precedes the context
LINE_HEIGHT = 12.0  # pt; space below the top of a question's last line
CROP_PADDING = 4.0  # pt
RESOLUTION = 200  # dpi
RANGE_RE = re.compile(r"^(\d+)\s+a\s+(\d+)\.")
SHEET_COLUMNS = ["exam_id", "page", "first", "last"]

log = logging.getLogger(__name__)


def crop_name(exam_id: str, page: int) -> str:
    """File name of a context crop (D005)."""
    return f"{exam_id}_p{page}.png"


@dataclass(frozen=True, slots=True)
class Context:
    exam_id: str
    page: int
    first: int
    last: int
    top: float  # crop box, in pt
    bottom: float

    @property
    def file_name(self) -> str:
        return crop_name(self.exam_id, self.page)


@dataclass(frozen=True, slots=True)
class QuestionPosition:
    page: int
    top: float
    number: int
    question_id: str


def question_positions(exam_pdf: Path, rules: CallRules) -> list[QuestionPosition]:
    """Start position of every question of an exam, in reading order."""
    exam_id = exam_pdf.stem[:-1]
    sections = expected_sections(rules)
    lines, _ = read_exam_lines(exam_pdf)
    drafts, _ = parse_exam_lines(lines, exam_id, sections)
    positions = [
        QuestionPosition(
            d.page, d.top, d.number, make_question_id(exam_id, s.part, s.is_reserve, d.number)
        )
        for s, section_drafts in zip(sections, drafts, strict=True)
        for d in section_drafts
    ]
    return sorted(positions, key=lambda p: (p.page, p.top))


def locate_context(
    positions: list[QuestionPosition], page: int, first: int, last: int
) -> list[str] | None:
    """Ids of questions `first` to `last`: the first ones found from `page` on (D005).

    Return None if they do not appear in a row.
    """
    start = next((i for i, p in enumerate(positions) if p.page >= page and p.number == first), None)
    if start is None:
        return None
    run = positions[start : start + last - first + 1]
    if [p.number for p in run] != list(range(first, last + 1)):
        return None
    return [p.question_id for p in run]


def _context_box(page: Page) -> tuple[float, float] | None:
    """Vertical extent of the context on a page, or None if there is none."""
    images = [i for i in page.images if i["x1"] - i["x0"] >= MIN_IMAGE_WIDTH]
    if images:
        return min(i["top"] for i in images), max(i["bottom"] for i in images)
    edges = page.rects + page.lines
    if len(edges) >= MIN_TABLE_EDGES:
        return min(e["top"] for e in edges), max(e["bottom"] for e in edges)
    return None


def _explicit_range(lines: list[Line], page: int, top: float, bottom: float) -> int | None:
    """Last question of an explicit "N a M." range inside the crop, if any."""
    for line in lines:
        if line.page == page and top <= line.top <= bottom:
            match = RANGE_RE.match(line.text.strip())
            if match:
                return int(match[2])
    return None


def detect_contexts(
    pdf: pdfplumber.PDF,
    exam_id: str,
    lines: list[Line],
    cover_pages: set[int],
    drafts: list[_Draft],
) -> tuple[list[Context], list[str]]:
    """Find the contexts of an exam. Drafts must be in reading order."""
    contexts: list[Context] = []
    notes: list[str] = []
    for number, page in enumerate(pdf.pages, start=1):
        if number in cover_pages:
            continue
        box = _context_box(page)
        if box is None:
            continue
        obj_top, obj_bottom = box
        where = f"{exam_id} p{number}"

        before = [d.last_top for d in drafts if d.last_page == number and d.last_top < obj_top]
        top = max(before) + LINE_HEIGHT if before else TOP_MARGIN
        after = [d for d in drafts if (d.page, d.top) > (number, obj_bottom)]
        if not after:
            notes.append(f"{where}: no question after the context, skipped")
            continue
        first = after[0]
        on_page = first.page == number
        bottom = first.top - CROP_PADDING if on_page else page.height * FOOTER_ZONE
        if bottom <= top:
            notes.append(f"{where}: empty crop box, skipped")
            continue

        last = _explicit_range(lines, number, top, bottom)
        if last is None:
            last = first.number
            for draft in after[1:]:
                if draft.page != first.page or draft.number != last + 1:
                    break
                last = draft.number
            notes.append(f"{where}: questions {first.number}-{last} estimated")
        elif last < first.number:
            notes.append(f"{where}: range ends at {last}, before question {first.number}")
        contexts.append(Context(exam_id, number, first.number, last, top, bottom))
    return contexts, notes


def read_sheet(path: Path) -> list[dict[str, str]]:
    """Rows of a control sheet, with stripped values."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def _covered_exams(sheet_path: Path, crops_dir: Path) -> set[str]:
    """Exams with a row in the sheet or a crop."""
    covered = {r["exam_id"] for r in read_sheet(sheet_path)} if sheet_path.exists() else set()
    return covered | {p.stem.rsplit("_p", 1)[0] for p in crops_dir.glob("*.png")}


def _write_sheet(path: Path, contexts: list[Context], append: bool) -> None:
    """Write the sheet, or append rows to an existing one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    append = append and path.exists()
    if append and not path.read_bytes().endswith(b"\n"):
        with path.open("a", encoding="utf-8", newline="") as f:
            f.write("\r\n")
    with path.open("a" if append else "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if not append:
            writer.writerow(SHEET_COLUMNS)
        for c in contexts:
            writer.writerow([c.exam_id, c.page, c.first, c.last])


def extract_contexts(
    data_dir: Path, opposition: str, force: bool = False
) -> tuple[list[str], list[Context], list[str]]:
    """Detect, crop and list the contexts of the exams not yet covered.

    Return (scanned exam ids, added contexts, review notes).
    """
    sheet_path = data_dir / "interim" / opposition / "contexts.csv"
    crops_dir = data_dir / "processed" / opposition / "contexts"
    rules_path = data_dir / "processed" / opposition / "rules.json"
    tests_dir = data_dir / "raw" / opposition / "tests"

    covered = set() if force else _covered_exams(sheet_path, crops_dir)

    rules = CallRulesCollection.model_validate_json(rules_path.read_text(encoding="utf-8"))
    rules_by_id = {r.call_id: r for r in rules.root}

    scanned: list[str] = []
    contexts: list[Context] = []
    notes: list[str] = []
    exam_pdfs = sorted(tests_dir.glob("*T.pdf"))
    log.info("%d exam(s) found in %s, %d covered", len(exam_pdfs), tests_dir, len(covered))
    for i, exam_pdf in enumerate(exam_pdfs, start=1):
        exam_id = exam_pdf.stem[:-1]
        if exam_id in covered:
            continue
        log.info("[%d/%d] %s", i, len(exam_pdfs), exam_id)
        call_rules = rules_by_id.get(exam_id[:5])
        if call_rules is None:
            notes.append(f"{exam_id}: call {exam_id[:5]} not found in {rules_path}")
            continue
        scanned.append(exam_id)
        lines, cover_pages = read_exam_lines(exam_pdf)
        sections, _ = parse_exam_lines(lines, exam_id, expected_sections(call_rules))
        drafts = sorted((d for s in sections for d in s), key=lambda d: (d.page, d.top))
        with pdfplumber.open(exam_pdf) as pdf:
            found, exam_notes = detect_contexts(pdf, exam_id, lines, cover_pages, drafts)
            notes += exam_notes
            for c in found:
                path = crops_dir / c.file_name
                if path.exists():
                    notes.append(f"overwriting {path}")
                crops_dir.mkdir(parents=True, exist_ok=True)
                page = pdf.pages[c.page - 1]
                page.crop((0, c.top, page.width, c.bottom)).to_image(resolution=RESOLUTION).save(
                    path
                )
        log.info("  %d context(s)", len(found))
        contexts += found

    if not scanned:
        return [], [], notes
    if force and sheet_path.exists():
        notes.insert(0, f"overwriting {sheet_path}")
    _write_sheet(sheet_path, contexts, append=not force)
    log.info("%d context(s) written to %s", len(contexts), sheet_path)
    return scanned, contexts, notes
