# `opox`

Core of "Project OPO", an initiative aimed at integrating Artificial
Intelligence into the preparation process for Spanish civil service examinations.

## Usage

```
uv run opox [--data-dir DIR] <command> ...
```

`--data-dir` sets the data root (default: `data`).

### `opox check rules [OPPOSITION]`

Validates the call rules extracted to `processed/<opposition>/rules.json` (default
opposition: `C2_AGE`). Read-only. It checks that:

- The JSON matches the `CallRulesCollection` model (`opox.models.rules`).
- The calls in the JSON and in the reference are the same.
- For each call, its `source` exists in `raw/<opposition>/`.
- For each call, the number of topics per block matches the manual reference
  `interim/<opposition>/check_rules.csv`.

The reference has one row per call, with columns `call_id, n_topics_block_1,
n_topics_block_2, ...`. Columns follow the order of the syllabus blocks, ignoring the
psychotechnical block; `-` means the call has no such block.

Exits with code 1 and lists every problem found if any check fails.
