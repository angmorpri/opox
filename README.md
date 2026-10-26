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

### Deduplication: `opox dedup extract | add | check STAGE [OPPOSITION]`

Groups the answered questions of `processed/<opposition>/questions.json` that are the
same question (D011), in three chained stages: `answers`, `stems` and `contexts`. Each
stage `<s>` writes to `interim/<opposition>/`:

- `dedup_<s>.json`: the groups, following `DedupCollection` (`opox.models.dedup`).
  Each group has its canonical question (the most recent) and its members: questions
  with equal normalized key. Every answered question is in exactly one group.
- `dedup_<s>_review.csv`: the review sheet, the only source of manual decisions. UTF-8
  with BOM, `;`-separated.
- `dedup_<s>_review.md`: the review guide.

| Stage     | Key                                                   | Compared within       | Review at |
|-----------|-------------------------------------------------------|-----------------------|-----------|
| `answers` | answer, moderate normalization (no case)              | all answered          | >= 70%    |
| `stems`   | stem, aggressive normalization (no accents nor prose punctuation) | each group of `dedup_answers.json` | >= 75% |

In `answers` and `stems`, members with equal key are joined automatically. Members
whose keys are similar (normalized Levenshtein similarity), directly or chained, form a
review case. The sheet has one row per member, `case;member;group;max_similarity;
questions;text`, and the guide shows each case with the similarity of each pair and
word diffs against member A. Members sharing a `group` label are joined; labels are
global to the sheet but cannot span several cases. Blank labels are pending and leave
the member alone.

In `contexts`, every pair of context crops found together in a `stems` group is
reviewed once. The sheet has one row per pair, `context_a;context_b;same;groups`, and
the guide shows both crops with the questions that use them. `same` is `y`, `n` or
blank (pending, kept together). A pair marked `n` splits every group holding it, one per
context; questions without context stay with the most recent context. An `n`
contradicted by other `y` pairs is an error.

Each stage reads the JSON of the previous one: if a stage changes, repeat the next ones.

- `opox dedup extract STAGE [--force]`: writes the sheet, the guide and the groups. If
  the JSON or the sheet exist, nothing is written; `--force` regenerates them, keeping
  the decisions of the members (or pairs) that still exist and reporting the lost ones.
- `opox dedup add STAGE`: rebuilds the JSON from the sheet; running it again changes
  nothing. Fails on invalid or contradictory decisions and repeated rows, and warns
  about rows that no longer exist, members or pairs missing from the sheet and pending
  rows.
- `opox dedup check STAGE`: read-only. Checks that every answered question is in exactly
  one group, that `stems` groups stay within one answer group, that the sheet is
  complete and up to date, and that the JSON matches what `add` would produce. Exits
  with code 1 and lists every problem found if any check fails. `opox dedup check all`
  checks the three stages in order.

### `opox extract bank [OPPOSITION] [--force]`

Builds the question bank `processed/<opposition>/bank.json` (D010), following
`QuestionBank` (`opox.models.bank`), from `questions.json` and the groups of the last
deduplication stage, `interim/<opposition>/dedup_contexts.json`. Every deduplication
stage must pass its check; otherwise it reports the first incomplete stage, or points to
the documentation if none has been run.

Each group becomes an entry:

- `bank_id`: `B0001`, `B0002`... in the order of `canonical`; it may change when the
  bank is regenerated.
- `canonical`: the most recent source (latest year, ties by `question_id`); `text` and
  `answer` are its own.
- `sources`: every `question_id` of the group.
- `context`: that of the most recent source with context, if any.
- `distractors`: the wrong options of all sources, the canonical ones first and then by
  recency, joined only when equal after the moderate normalization. Options equal to an
  answer of the group are left out.

If the bank exists and is identical, nothing changes. If it differs, nothing is written
and the entries added, removed and changed are reported; `--force` overwrites it.

### `opox check bank [OPPOSITION]`

Validates `processed/<opposition>/bank.json` against `questions.json`. Read-only. The
grouping is taken as given (see `opox dedup check`). It checks that:

- The JSON matches the `QuestionBank` model.
- Every answered question is in exactly one entry.
- `bank_id` follows the order of `canonical`.
- Each entry's `canonical`, `text`, `context`, `answer` and `distractors` match what its
  sources produce, and its context crop exists.

Exits with code 1 and lists every problem found if any check fails.
