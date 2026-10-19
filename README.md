# `opox`

Core of "Project OPO", an initiative aimed at integrating Artificial
Intelligence into the preparation process for Spanish civil service examinations.

## Usage

```
uv run opox [--data-dir DIR] <command> ...
```

`--data-dir` sets the data root (default: `data`). `OPPOSITION` defaults to `C2_AGE`.

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
