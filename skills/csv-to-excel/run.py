#!/usr/bin/env python3
"""csv-to-excel — turn a CSV into an .xlsx workbook with a summary sheet.

Stdlib only: no openpyxl, no pandas, no install step. Writes the OOXML package directly
so the skill runs inside a sandbox container that has nothing but Python.

Usage:
    python3 run.py <input.csv> [output.xlsx]

Exit codes:
    0 ok
    2 bad arguments / input file
    3 empty or unusable CSV
"""

from __future__ import annotations

import csv
import os
import sys
import zipfile
from xml.sax.saxutils import escape

MAX_COL_WIDTH = 60
MIN_COL_WIDTH = 10


# ---------------------------------------------------------------- value helpers


def to_number(value: str):
    """Return a float when the CSV cell is unambiguously numeric, else None."""
    text = value.strip().replace(",", "")
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    # Reject things like "1e999" that become inf, and IDs with leading zeros.
    if number != number or number in (float("inf"), float("-inf")):
        return None
    if text.isdigit() and len(text) > 1 and text.startswith("0"):
        return None
    return number


def fail(message: str, code: int = 3) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def col_letter(index: int) -> str:
    """1 -> A, 27 -> AA."""
    letters = ""
    while index > 0:
        index, rem = divmod(index - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def style_attr(style: int) -> str:
    return f' s="{style}"' if style else ""


def cell(ref: str, value, style: int = 0) -> str:
    if value is None or value == "":
        return f'<c r="{ref}"{style_attr(style)}/>'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{ref}"{style_attr(style)}><v>{value}</v></c>'
    text = escape(str(value))
    return f'<c r="{ref}" t="inlineStr"{style_attr(style)}><is><t xml:space="preserve">{text}</t></is></c>'


def sheet_xml(rows: list[list], header: bool = True, widths: list[int] | None = None) -> str:
    parts = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>']
    parts.append('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">')
    if widths:
        cols = "".join(
            f'<col min="{i + 1}" max="{i + 1}" width="{w}" customWidth="1"/>' for i, w in enumerate(widths)
        )
        parts.append(f"<cols>{cols}</cols>")
    parts.append("<sheetData>")
    for r, row in enumerate(rows, start=1):
        style = 1 if (header and r == 1) else 0
        cells = "".join(cell(f"{col_letter(c)}{r}", value, style) for c, value in enumerate(row, start=1))
        parts.append(f'<row r="{r}">{cells}</row>')
    parts.append("</sheetData></worksheet>")
    return "".join(parts)


STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="2">
  <font><sz val="11"/><name val="Calibri"/></font>
  <font><b/><sz val="11"/><name val="Calibri"/></font>
</fonts>
<fills count="3">
  <fill><patternFill patternType="none"/></fill>
  <fill><patternFill patternType="gray125"/></fill>
  <fill><patternFill patternType="solid"><fgColor rgb="FFEDEDED"/><bgColor indexed="64"/></patternFill></fill>
</fills>
<borders count="1"><border/></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="2">
  <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
  <xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

WORKBOOK_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

WORKBOOK = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets>
  <sheet name="Data" sheetId="1" r:id="rId1"/>
  <sheet name="Summary" sheetId="2" r:id="rId2"/>
</sheets>
</workbook>"""


# ---------------------------------------------------------------- core logic


def read_csv(path: str):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        rows = [row for row in reader]
    rows = [row for row in rows if any(cell_value.strip() for cell_value in row)]
    if not rows:
        fail(f"error: {path} has no rows")
    header, body = rows[0], rows[1:]
    if len(header) < 2:
        fail(f"error: {path} needs at least two columns, got {len(header)}")
    if not body:
        fail(f"error: {path} has a header but no data rows")
    width = len(header)
    for i, row in enumerate(body, start=2):
        if len(row) != width:
            print(f"warning: line {i} has {len(row)} cells, expected {width} — padded", file=sys.stderr)
            body[i - 2] = row + [""] * (width - len(row))
    return header, body


def build_data_sheet(header: list[str], body: list[list]):
    rows = [header]
    numeric_cols: list[int] = []
    for col in range(len(header)):
        if body and all(to_number(row[col]) is not None for row in body):
            numeric_cols.append(col)
    for row in body:
        cooked = []
        for col, value in enumerate(row):
            number = to_number(value) if col in numeric_cols else None
            cooked.append(number if number is not None else value.strip())
        rows.append(cooked)
    return rows, numeric_cols


def build_summary_sheet(header: list[str], body: list[list], numeric_cols: list[int]):
    rows = [["metric", "column", "value"]]
    rows.append(["rows", "-", len(body)])
    rows.append(["columns", "-", len(header)])
    for col in numeric_cols:
        values = [to_number(row[col]) for row in body]
        values = [v for v in values if v is not None]
        name = header[col]
        rows.append(["count", name, len(values)])
        rows.append(["sum", name, round(sum(values), 6)])
        rows.append(["mean", name, round(sum(values) / len(values), 6)])
        rows.append(["min", name, round(min(values), 6)])
        rows.append(["max", name, round(max(values), 6)])
    return rows


def column_widths(rows: list[list]) -> list[int]:
    widths = []
    for col in range(len(rows[0])):
        longest = max(len(str(row[col])) for row in rows if col < len(row))
        widths.append(max(MIN_COL_WIDTH, min(MAX_COL_WIDTH, longest + 2)))
    return widths


def write_xlsx(path: str, data_rows: list[list], summary_rows: list[list]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", CONTENT_TYPES)
        package.writestr("_rels/.rels", ROOT_RELS)
        package.writestr("xl/workbook.xml", WORKBOOK)
        package.writestr("xl/_rels/workbook.xml.rels", WORKBOOK_RELS)
        package.writestr("xl/styles.xml", STYLES)
        package.writestr("xl/worksheets/sheet1.xml", sheet_xml(data_rows, True, column_widths(data_rows)))
        package.writestr("xl/worksheets/sheet2.xml", sheet_xml(summary_rows, True, column_widths(summary_rows)))


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__.strip())
        return 2
    source = argv[1]
    target = argv[2] if len(argv) > 2 else os.path.splitext(source)[0] + ".xlsx"
    if not os.path.isfile(source):
        print(f"error: no such file: {source}", file=sys.stderr)
        return 2
    if not source.lower().endswith(".csv"):
        print(f"error: expected a .csv input, got {source}", file=sys.stderr)
        return 2

    header, body = read_csv(source)
    data_rows, numeric_cols = build_data_sheet(header, body)
    summary_rows = build_summary_sheet(header, body, numeric_cols)
    write_xlsx(target, data_rows, summary_rows)

    print(f"wrote {target}: {len(body)} rows, {len(header)} columns, {len(numeric_cols)} numeric column(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
