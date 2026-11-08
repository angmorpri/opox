# `opox`

Core of "Project OPO", an initiative aimed at integrating Artificial
Intelligence into the preparation process for Spanish civil service examinations.

## Usage

```
uv run opox [--data-dir DIR] <command> ...
```

`--data-dir` sets the data root (default: `data`). `OPPOSITION` defaults to `C2_AGE`.
Every command accepts `-v`/`--verbose` to report its progress. Subcommands accept any
unambiguous prefix: `opox ext q` runs `opox extract questions`.

### `opox extract questions [OPPOSITION] [--force]`

Extracts the questions and answers of every exam in `raw/<opposition>/tests/`
(`<exam_id>T.pdf` plus its answer key `<exam_id>R.pdf`) into
`processed/<opposition>/questions.json`, following the `ExamCollection` model
(`opox.models.questions`).

Each exam is split into the parts and reserve lists set by its call rules
(`processed/<opposition>/rules.json`), on every numbering reset. Text shared by several
questions (tables, "Responda las siguientes preguntas...") is skipped. At the end, it
lists the points to review (`REVIEW`): shared preambles, section counts that do not
match the rules, questions without four options or without an answer. Then it lists
each exam added (`ADDED`) with its number of questions.

Running it again keeps the exams already in `questions.json` untouched (including their
assigned contexts) and only extracts the new ones; the review points and `ADDED` lines
refer to those alone. `--force` extracts every exam again and rewrites the file.

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
consecutive question on the same page, and listed for review (`REVIEW`). Then it lists
each context added (`ADDED`) with its questions.

Running it again leaves untouched every exam already covered, that is, with a row in the
sheet or a crop: manual fixes and removed false positives are kept. Only the other exams
are scanned, and their contexts are cropped and appended to the sheet; the review points
and `ADDED` lines refer to those alone. Exams without contexts are scanned again on every
run. `--force` scans every exam again and rewrites the sheet and crops, reporting each
file replaced.

### `opox extract duplicates [OPPOSITION] [--force] [--threshold T] [--answer-threshold A]`

Identifies the duplicate questions of `processed/<opposition>/questions.json` (D011) and
writes, in `interim/<opposition>/`:

- `duplicates.json`: groups of two or more duplicate questions, following the
  `DuplicateCollection` model (`opox.models.duplicates`). Each group lists its `members`
  and its `origin`: `exact` or `manual` (joined by `opox add duplicates`).
- `dup_contexts.csv`, columns `context_a, context_b, same, groups`: one pair of different
  context crops found together in a group per row. **Mandatory review**: fill in `same`
  with `y` (same context) or `n` (different; the groups are split, one per context).
- `dup_check.csv`, columns `question_a, question_b, score, answer_score, same`: one pair
  of similar groups per row, identified by their canonical questions, most similar
  first. **Optional review**: fill in `same` with `y` or `n`; blank rows are ignored.
- `dup_contexts.md` and `dup_check.md`: read-only guides for both sheets, with the crops,
  the questions and their word differences. The CSV files are the source of truth.

Only answered questions count, keyed as `"{extended stem} {base answer}"`; questions
with equal key form an `exact` group. Pairs of groups whose keys reach `T` (default 75)
and whose answers reach `A` (default 95) of normalized Levenshtein similarity go to
`dup_check.csv`. Both thresholds are stored in `duplicates.json` and reused afterwards.

Running it again recomputes the exact groups and keeps the `manual` ones and every
decided row of both sheets, adding only the new pairs; decisions whose questions or
crops no longer exist are dropped and reported. `--force` rebuilds everything from
scratch, discarding manual groups and decisions.

### `opox add contexts [OPPOSITION]`

Sets the `context` of each question in `processed/<opposition>/questions.json` from the
context sheet and crops (D005), after validating them as `opox check contexts` does;
questions outside the sheet get no context. The sheet is the source of truth: previous
assignments are always replaced. It reports how many questions have a context.

### `opox add duplicates [OPPOSITION]`

Joins into a `manual` group of `interim/<opposition>/duplicates.json` the two groups of
every pair marked `y` in `dup_check.csv`. Then it updates the outputs as
`opox extract duplicates` does with the stored thresholds: new context pairs are added
to `dup_contexts.csv`, and `dup_check.csv` is regenerated without the pairs already
joined, keeping the `n` decisions. Optional step.

### `opox check duplicates [OPPOSITION]`

Validates `interim/<opposition>/duplicates.json`, `dup_contexts.csv` and `dup_check.csv`
against `processed/<opposition>/questions.json`. Read-only. It fails if:

- The groups are out of date with the questions (rerun `opox extract duplicates`).
- A sheet has wrong columns, invalid or repeated rows, or unknown questions or crops.
- A context pair is pending, missing, or marked `n` while other pairs join both crops.
- A pair of `dup_check.csv` is marked `n` but both questions are in the same group.

It warns (`WARNING`) about pairs marked `y` not added yet, and reports how many pairs of
`dup_check.csv` are not reviewed (optional) and how many bank entries would result.

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

### `opox make bank [OPPOSITION]`

Builds the question bank `processed/<opposition>/bank.json`, following the
`QuestionBank` model (`opox.models.bank`, D010), from `questions.json` and the reviewed
duplicates. It first validates them as `opox check duplicates` does, and fails on any
error, such as pending context pairs; pairs of `dup_check.csv` marked `y` but not added
are only warned about.

There is one entry per group, after splitting the groups whose crops are marked as
different, plus one per unique answered question. The canonical question is the most
recent one (latest year, ties by `question_id`): it gives the entry its `bank_id`,
`text` and `answer`. The `context` is that of the most recent question with context.
The `distractors` are the wrong options of every source, joined when equal after the
base normalization, keeping the most recent text; each entry needs at least three.

The bank holds no manual work, so it is always rebuilt from scratch.

### `opox extract categories [OPPOSITION] [--force]`

Extracts the four official categories and their topics per call from
`processed/<opposition>/rules.json` into `processed/<opposition>/categories.json`,
following the `CategoryCollection` model (`opox.models.categories`). Each topic keeps its
reference to the rules (`block_id`, `number`) and its text, and belongs to one category:

| `category_id` | Name | Blocks |
|---|---|---|
| 1 | Organización pública | named "Organización pública" |
| 2 | Actividad administrativa | named "Actividad administrativa"; topics of other blocks before the split |
| 3 | Ofimática | named "Ofimática"; topics of other blocks from the split on |
| 4 | Psicotécnico | `PSICO`; its topics are the aptitudes |

Names are compared after the extended normalization. Any other block, named (such as
"Actividad administrativa y ofimática") or not (`U`), is split at its first topic with
the word "informática". It fails, writing nothing, if a block has no such topic.

Running it again keeps the calls already in the file and only adds the new ones, listed
as `ADDED` with their topics per category. `--force` rebuilds the file from scratch.
