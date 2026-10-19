from opox.extract.questions import (
    AnswerMark,
    Section,
    _ExamParser,
    _join,
    order_by_columns,
    split_answers,
)
from opox.pdf import Line, Segment

SECTIONS = [Section(1, False, 2), Section(1, True, 1)]


def line(top: float, *segments: tuple[float, str], page: int = 1) -> Line:
    return Line(page, top, 842.0, tuple(Segment(x, t) for x, t in segments))


def parse(lines: list[Line]) -> _ExamParser:
    parser = _ExamParser("2025L0A", SECTIONS)
    for ln in lines:
        parser.feed(ln)
    parser.finish()
    return parser


def test_options_one_per_line_and_two_columns() -> None:
    parser = parse(
        [
            line(10, (28, "1. ¿Pregunta uno?")),
            line(20, (50, "a) A1")),
            line(30, (50, "b) B1")),
            line(40, (50, "c) C1")),
            line(50, (50, "d) D1")),
            line(70, (28, "2."), (57, "¿Pregunta dos?")),
            line(80, (57, "a) A2"), (312, "b) B2")),
            line(90, (57, "c) C2"), (312, "d) D2")),
        ]
    )
    first, second = parser.results[0]
    assert first.options == [["A1"], ["B1"], ["C1"], ["D1"]]
    assert second.text == ["¿Pregunta dos?"]
    assert [_join(o) for o in second.options] == ["A2", "B2", "C2", "D2"]


def test_continuations_and_preamble() -> None:
    parser = parse(
        [
            line(10, (28, "1. Texto que sigue")),
            line(20, (50, "en otra línea:")),
            line(30, (50, "a) A")),
            line(40, (50, "b) B")),
            line(50, (50, "c) C")),
            line(60, (50, "d) Opción larga")),
            line(70, (71, "que continúa.")),
            line(90, (28, "Responda las siguientes preguntas según la imagen.")),
            line(100, (28, "2. Siguiente")),
            line(110, (50, "a) A")),
            line(120, (50, "b) B")),
            line(130, (50, "c) C")),
            line(140, (50, "d) D")),
        ]
    )
    first, second = parser.results[0]
    assert _join(first.text) == "Texto que sigue en otra línea:"
    assert _join(first.options[3]) == "Opción larga que continúa."
    assert second.number == 2
    assert len(parser.notes) == 1 and "Responda las siguientes" in parser.notes[0]


def options(top: float) -> list[Line]:
    return [line(top + 10 * i, (50, f"{c}) x")) for i, c in enumerate("abcd")]


def test_reset_starts_next_section_and_headers_are_not_preambles() -> None:
    parser = parse(
        [
            line(10, (28, "1. Uno")),
            *options(20),
            line(70, (28, "2. Dos")),
            *options(80),
            line(140, (28, "Preguntas de reserva")),
            line(160, (28, "1 Una reserva sin punto no reinicia")),
            line(170, (28, "1. Reserva")),
            *options(180),
        ]
    )
    assert [d.number for d in parser.results[0]] == [1, 2]
    assert [d.text for d in parser.results[1]] == [["Reserva"]]
    assert parser.notes == []


def test_number_without_dot_only_continues_a_section() -> None:
    parser = parse(
        [
            line(10, (28, "1. Uno")),
            line(20, (50, "a) x")),
            line(30, (50, "b) x")),
            line(40, (50, "c) x")),
            line(50, (50, "d) x")),
            line(70, (28, "2"), (50, "Dos sin punto")),
            line(80, (50, "a) x")),
            line(90, (50, "b) x")),
            line(100, (50, "c) x")),
            line(110, (50, "d) x")),
        ]
    )
    assert [d.number for d in parser.results[0]] == [1, 2]


def test_answer_key_columns_and_sections() -> None:
    marks = [
        AnswerMark(1, 50, 10, 1, 0),
        AnswerMark(1, 50, 20, 2, None),
        AnswerMark(1, 300, 10, 1, 3),
        AnswerMark(1, 300, 20, 9, 1),
    ]
    answers, unexpected = split_answers(order_by_columns(marks), SECTIONS)
    assert answers == [[0, None], [3]]
    assert unexpected == [9]


def test_join_keeps_hyphenated_words() -> None:
    assert (
        _join(["contencioso-", "administrativo", " y  más "]) == "contencioso-administrativo y más"
    )
