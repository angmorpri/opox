# `opox`

Core of "Project OPO", an initiative aimed at integrating Artificial
Intelligence into the preparation process for Spanish civil service examinations.

## Usage

```
uv run opox [--data-dir DIR] <command> ...
```

`--data-dir` sets the data root (default: `data`). `OPPOSITION` defaults to `C2_AGE`.
Every command accepts `-v`/`--verbose` to report its progress.

### `opox extract questions [OPPOSITION] [--force]`

Extracts the questions and answers of every exam in `raw/<opposition>/tests/`
(`<exam_id>T.pdf` plus its answer key `<exam_id>R.pdf`) into
`processed/<opposition>/questions.json`, following the `ExamCollection` model
(`opox.models.questions`). Refuses to overwrite an existing output unless `--force`.

Each exam is split into the parts and reserve lists set by its call rules
(`processed/<opposition>/rules.json`), on every numbering reset. Text shared by several
questions (tables, "Responda las siguientes preguntas...") is skipped. At the end, it
lists the points to review (`REVIEW`): shared preambles, section counts that do not
match the rules, questions without four options or without an answer.

### `opox extract contexts [OPPOSITION] [--force]`

Detects the contexts (images and tables) shared by several questions in each exam of
`raw/<opposition>/tests/`, and writes:

- One crop per context: `processed/<opposition>/contexts/<exam_id>_p<page>.png`.
- The control sheet `interim/<opposition>/contexts.csv`, with columns
  `exam_id, page, first, last`: the context page and the first and last questions that
  need it.

A page holds a context if it has an image wider than 200 pt or more than 40 drawn edges
(a table). The crop spans the page width, between the previous question and the next
one. `last` comes from an explicit "N a M." range; otherwise it is estimated as the last
consecutive question on the same page, and listed for review (`REVIEW`).

If the sheet or any crop already exists, nothing is written: it only lists the detected
contexts missing from the sheet. `--force` overwrites, reporting each file replaced.

### `opox add contexts [OPPOSITION] [--force]`

Sets the `context` of each question in `processed/<opposition>/questions.json` from the
context sheet and crops (D005), after validating them as `opox check contexts` does;
questions outside the sheet get no context. Running it again changes nothing.

Adding a context is always allowed. If an existing context would be replaced or cleared,
nothing is written and the affected questions are listed; `--force` applies the changes.

### `opox check contexts [OPPOSITION]`

Validates the context sheet `interim/<opposition>/contexts.csv` and its crops in
`processed/<opposition>/contexts/`. Read-only. It checks that:

- The sheet has the expected columns, valid values (`first <= last`) and no duplicate
  `exam_id, page` pairs.
- Every row has its PNG crop, and every file in the crops folder has its row.
- The page exists in the exam PDF, and questions `first` to `last` appear in a row from
  that page on (D005), exist in `processed/<opposition>/questions.json`, and belong to a
  single context.

Exits with code 1 and lists every problem found if any check fails.

### `opox check questions [OPPOSITION]`

Validates `processed/<opposition>/questions.json`. Read-only. It checks that:

- The JSON matches the `ExamCollection` model.
- There is one exam per exam PDF, and its sources exist in `raw/<opposition>/`.
- Each part and reserve list has the questions set by the call rules, numbered from 1.
- Every assigned context exists in `processed/<opposition>/`.

It warns (`WARNING`) when context assignment is pending. Exits with code 1 and lists
every problem found if any check fails.

### `opox check rules [OPPOSITION]`

Validates the call rules extracted to `processed/<opposition>/rules.json`. Read-only.
It checks that:

- The JSON matches the `CallRulesCollection` model (`opox.models.rules`).
- The calls in the JSON and in the reference are the same.
- For each call, its `source` exists in `raw/<opposition>/`.
- For each call, the number of topics per block matches the manual reference
  `interim/<opposition>/check_rules.csv`.

The reference has one row per call, with columns `call_id, n_topics_block_1,
n_topics_block_2, ...`. Columns follow the order of the syllabus blocks, ignoring the
psychotechnical block; `-` means the call has no such block.

Exits with code 1 and lists every problem found if any check fails.
