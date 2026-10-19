"""Text-line reconstruction from PDFs, based on word positions (pdfplumber)."""

from dataclasses import dataclass
from pathlib import Path

import pdfplumber

LINE_TOLERANCE = 3.0  # max vertical distance (pt) between words of the same line
SEGMENT_GAP = 15.0  # min horizontal gap (pt) that splits a line into segments


@dataclass(frozen=True, slots=True)
class Segment:
    """Run of words on a line, separated from its neighbours by a wide gap."""

    x0: float
    text: str


@dataclass(frozen=True, slots=True)
class Line:
    page: int  # 1-based
    top: float
    page_height: float
    segments: tuple[Segment, ...]

    @property
    def x0(self) -> float:
        return self.segments[0].x0

    @property
    def text(self) -> str:
        return " ".join(s.text for s in self.segments)


@dataclass(frozen=True, slots=True)
class Word:
    page: int
    page_height: float
    x0: float
    x1: float
    top: float
    text: str


def read_words(path: Path) -> list[list[Word]]:
    """Return the words of each page, in reading order (top to bottom, left to right)."""
    pages: list[list[Word]] = []
    with pdfplumber.open(path) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            raw = page.extract_words(x_tolerance=1.5, y_tolerance=LINE_TOLERANCE)
            words = [Word(number, page.height, w["x0"], w["x1"], w["top"], w["text"]) for w in raw]
            words.sort(key=lambda w: (round(w.top), w.x0))
            pages.append(words)
    return pages


def group_lines(words: list[Word]) -> list[list[Word]]:
    """Group words of a page into lines, each sorted left to right."""
    lines: list[list[Word]] = []
    for word in words:
        if lines and abs(lines[-1][0].top - word.top) < LINE_TOLERANCE:
            lines[-1].append(word)
        else:
            lines.append([word])
    for line in lines:
        line.sort(key=lambda w: w.x0)
    return lines


def to_line(words: list[Word]) -> Line:
    """Build a line, splitting it into segments at wide horizontal gaps."""
    segments: list[Segment] = []
    current = [words[0]]
    for prev, word in zip(words, words[1:], strict=False):
        if word.x0 - prev.x1 > SEGMENT_GAP:
            segments.append(Segment(current[0].x0, " ".join(w.text for w in current)))
            current = [word]
        else:
            current.append(word)
    segments.append(Segment(current[0].x0, " ".join(w.text for w in current)))
    return Line(words[0].page, words[0].top, words[0].page_height, tuple(segments))


def read_lines(path: Path) -> list[Line]:
    """Return all text lines of a PDF, page by page."""
    return [to_line(ws) for page in read_words(path) for ws in group_lines(page)]
