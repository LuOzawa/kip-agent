# csv-to-excel

Turn a CSV into an `.xlsx` workbook: the raw table on sheet **Data**, per-numeric-column stats on sheet **Summary**.

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
node run.ts samples/sales.csv out/sales-report.xlsx
→ wrote out/sales-report.xlsx: 5 rows, 4 columns, 2 numeric column(s)
```

Sheets:

- **Data** — header row (bold, grey), all rows; columns that are numeric in *every* row are written as numbers, everything else stays text
- **Summary** — `rows`, `columns`, then `count / sum / mean / min / max` per numeric column

## Behaviour worth knowing

- Parsing is RFC4180-ish: quoted fields, `""` escapes and commas inside quotes survive (`"Zhang, Wei"` stays one cell).
- Cells that cannot be parsed as numbers stay text — `0`-prefixed IDs (`007`) and values overflowing to `Infinity` are deliberately **not** numeric, so IDs keep their form.
- Rows shorter than the header are padded and reported as a warning on stderr.
- Blank lines are skipped.

## Failure modes

| Symptom | Exit code | What the agent should do |
|---|---|---|
| file missing / not a `.csv` | 2 | check the path the user gave, do not retry blindly |
| empty file, no rows, or fewer than two columns | 3 | report the problem to the user; the input is not a usable table |

Nothing is written when the exit code is non-zero, so a failed run never leaves a half-built workbook behind.

## Verified on

- 2026-10-18 · Node 26 (`node run.ts`, types stripped natively) and CI Node 24 · `samples/sales.csv` → 5 rows, 4 columns, 2 numeric columns; workbook reopened and read back with openpyxl 3.1.5 (sheets `Data`, `Summary`; header bold; column widths applied)
- Edge cases exercised: quoted CSV with embedded commas/quotes, leading-zero IDs staying text, ragged row (padded + warning), empty file (exit 3), single-column CSV (exit 3), missing file (exit 2)

## Why zero dependencies

No openpyxl, no exceljs. The OOXML package is assembled by hand and compressed with the built-in `node:zlib`; the zip container (local headers, central directory, EOCD, CRC32) is written in `run.ts`.

`package.json` exists only to declare `"type": "module"` — there are no dependencies to install, so the skill runs in a container that has nothing but Node.
