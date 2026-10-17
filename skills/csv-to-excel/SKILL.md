# csv-to-excel

Turn a CSV into an `.xlsx` workbook: the raw table on sheet **Data**, and per-numeric-column stats on sheet **Summary**.

## When to use

Use it when the user hands you a `.csv` and wants a spreadsheet back — formatted, with totals, without opening Excel.

Do **not** use it when:

- the input is already `.xlsx` (nothing to convert — edit the workbook instead)
- the request needs formulas or charts; this skill writes values only
- the CSV has no header row: there is no way to name columns, so refuse and ask

## Inputs / outputs

| | |
|---|---|
| input | one `.csv` file, UTF-8 (BOM tolerated), comma-separated, header in the first row |
| output | `.xlsx` with two sheets; defaults to `<input>.xlsx` next to the input |

```
python3 run.py samples/sales.csv out/sales-report.xlsx
→ wrote out/sales-report.xlsx: 5 rows, 4 columns, 2 numeric column(s)
```

Sheets:

- **Data** — header row (bold, grey), all rows; columns that are numeric in *every* row are written as numbers, everything else stays text
- **Summary** — `rows`, `columns`, then `count / sum / mean / min / max` per numeric column

## Behaviour worth knowing

- Cells that cannot be fully parsed as numbers stay text — `0`-prefixed IDs (`007`) and `1e999` are deliberately **not** treated as numeric, so IDs keep their form.
- Rows shorter than the header are padded and reported as a warning on stderr.
- Blank lines are skipped.

## Failure modes

| Symptom | Exit code | What the agent should do |
|---|---|---|
| file missing / not a `.csv` | 2 | check the path the user gave, do not retry blindly |
| empty file, no rows, or fewer than two columns | 3 | report the problem to the user; the input is not a usable table |

Nothing is written when the exit code is non-zero, so a failed run never leaves a half-built workbook behind.

## Verified on

- 2026-10-18 · Python 3.9 (macOS) and 3.12 (CI) · `samples/sales.csv` → 5 rows, 4 columns, 2 numeric columns; workbook reopened and read back with openpyxl 3.1.5
- Edge cases exercised: single-column CSV (exit 3), empty file (exit 3), ragged row (padded + warning), missing file (exit 2)

## Why stdlib only

No `openpyxl`, no `pandas`. The OOXML package is written by hand so the skill runs inside a container that has nothing but Python — the same guarantee the product makes about sandboxed execution.
