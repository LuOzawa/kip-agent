#!/usr/bin/env node
/**
 * csv-to-excel — turn a CSV into an .xlsx workbook with a summary sheet.
 *
 * Zero npm dependencies: the OOXML package is written by hand and compressed with the
 * built-in node:zlib, so the skill runs in a container that only has Node.
 *
 * Usage:
 *   node run.ts <input.csv> [output.xlsx]
 *
 * Exit codes:
 *   0 ok
 *   2 bad arguments / input file
 *   3 empty or unusable CSV
 */

import { deflateRawSync } from "node:zlib";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, extname, resolve } from "node:path";

// ------------------------------------------------------------------ csv parsing

/** RFC4180-ish parser: handles quoted fields, escaped quotes and CRLF. */
function parseCsv(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let quoted = false;
  let hasContent = false;

  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i++;
        } else {
          quoted = false;
        }
      } else {
        field += ch;
      }
      continue;
    }
    if (ch === '"' && field === "") {
      quoted = true;
      hasContent = true;
    } else if (ch === ",") {
      row.push(field);
      field = "";
      hasContent = true;
    } else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
      hasContent = false;
    } else {
      field += ch;
      hasContent = true;
    }
  }
  if (hasContent || field !== "" || row.length > 0) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}

function readCsv(path: string): { header: string[]; body: string[][] } {
  const raw = readFileSync(path, "utf8").replace(/^\uFEFF/, "");
  const rows = parseCsv(raw).filter((row) => row.some((cell) => cell.trim() !== ""));
  if (rows.length === 0) fail(`error: ${path} has no rows`);
  const header = rows[0].map((cell) => cell.trim());
  const body = rows.slice(1);
  if (header.length < 2) fail(`error: ${path} needs at least two columns, got ${header.length}`);
  if (body.length === 0) fail(`error: ${path} has a header but no data rows`);

  for (let i = 0; i < body.length; i++) {
    if (body[i].length !== header.length) {
      console.error(
        `warning: line ${i + 2} has ${body[i].length} cells, expected ${header.length} — padded`,
      );
      body[i] = [...body[i], ...Array(header.length - body[i].length).fill("")];
    }
  }
  return { header, body };
}

// ---------------------------------------------------------------- value helpers

/**
 * Returns a number when the cell is unambiguously numeric, else null.
 * Leading-zero IDs ("007") and values that overflow to Infinity stay text on purpose.
 */
function toNumber(value: string): number | null {
  const text = value.trim().replace(/,/g, "");
  if (text === "") return null;
  if (!/^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$/.test(text)) return null;
  if (/^[+-]?0\d/.test(text)) return null;
  const num = Number(text);
  return Number.isFinite(num) ? num : null;
}

function colLetter(index: number): string {
  let letters = "";
  let n = index;
  while (n > 0) {
    const rem = (n - 1) % 26;
    letters = String.fromCharCode(65 + rem) + letters;
    n = Math.floor((n - 1) / 26);
  }
  return letters;
}

function escapeXml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

type CellValue = string | number | null;

function cellXml(ref: string, value: CellValue, style: number): string {
  const s = style ? ` s="${style}"` : "";
  if (value === null || value === "") return `<c r="${ref}"${s}/>`;
  if (typeof value === "number") return `<c r="${ref}"${s}><v>${value}</v></c>`;
  return `<c r="${ref}" t="inlineStr"${s}><is><t xml:space="preserve">${escapeXml(value)}</t></is></c>`;
}

function columnWidths(rows: CellValue[][]): number[] {
  const width = rows[0].length;
  const widths: number[] = [];
  for (let c = 0; c < width; c++) {
    const longest = Math.max(...rows.map((row) => String(row[c] ?? "").length));
    widths.push(Math.max(10, Math.min(60, longest + 2)));
  }
  return widths;
}

function sheetXml(rows: CellValue[][], header: boolean): string {
  const widths = columnWidths(rows);
  const cols = widths
    .map((w, i) => `<col min="${i + 1}" max="${i + 1}" width="${w}" customWidth="1"/>`)
    .join("");
  const body = rows
    .map((row, r) => {
      const style = header && r === 0 ? 1 : 0;
      const cells = row
        .map((value, c) => cellXml(`${colLetter(c + 1)}${r + 1}`, value, style))
        .join("");
      return `<row r="${r + 1}">${cells}</row>`;
    })
    .join("");
  return (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' +
    `<cols>${cols}</cols><sheetData>${body}</sheetData></worksheet>`
  );
}

// ------------------------------------------------------------------ sheet logic

function buildDataSheet(header: string[], body: string[][]) {
  const numericCols = header
    .map((_, c) => c)
    .filter((c) => body.length > 0 && body.every((row) => toNumber(row[c]) !== null));
  const rows: CellValue[][] = [header];
  for (const row of body) {
    rows.push(
      row.map((value, c) => (numericCols.includes(c) ? (toNumber(value) as number) : value.trim())),
    );
  }
  return { rows, numericCols };
}

function buildSummarySheet(header: string[], body: string[][], numericCols: number[]) {
  const rows: CellValue[][] = [
    ["metric", "column", "value"],
    ["rows", "-", body.length],
    ["columns", "-", header.length],
  ];
  const round = (n: number) => Number(n.toFixed(6));
  for (const c of numericCols) {
    const values = body.map((row) => toNumber(row[c])).filter((n): n is number => n !== null);
    const name = header[c];
    rows.push(["count", name, values.length]);
    rows.push(["sum", name, round(values.reduce((a, b) => a + b, 0))]);
    rows.push(["mean", name, round(values.reduce((a, b) => a + b, 0) / values.length)]);
    rows.push(["min", name, round(Math.min(...values))]);
    rows.push(["max", name, round(Math.max(...values))]);
  }
  return rows;
}

// ------------------------------------------------------------------- zip writer

const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[i] = c >>> 0;
  }
  return table;
})();

function crc32(data: Buffer): number {
  let crc = 0xffffffff;
  for (const byte of data) crc = CRC_TABLE[(crc ^ byte) & 0xff]! ^ (crc >>> 8);
  return (crc ^ 0xffffffff) >>> 0;
}

/** Builds a deflate-compressed zip package from in-memory files. */
function zip(files: { name: string; data: string }[]): Buffer {
  const locals: Buffer[] = [];
  const centrals: Buffer[] = [];
  let offset = 0;

  for (const file of files) {
    const nameBytes = Buffer.from(file.name, "utf8");
    const raw = Buffer.from(file.data, "utf8");
    const packed = deflateRawSync(raw, { level: 9 });
    const crc = crc32(raw);

    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4);
    local.writeUInt16LE(0, 6);
    local.writeUInt16LE(8, 8);
    local.writeUInt16LE(0, 10); // mod time
    local.writeUInt16LE(0x2821, 12); // mod date (2000-01-01, fixed so builds are reproducible)
    local.writeUInt32LE(crc, 14);
    local.writeUInt32LE(packed.length, 18);
    local.writeUInt32LE(raw.length, 22);
    local.writeUInt16LE(nameBytes.length, 26);
    local.writeUInt16LE(0, 28);
    locals.push(local, nameBytes, packed);

    const central = Buffer.alloc(46);
    central.writeUInt32LE(0x02014b50, 0);
    central.writeUInt16LE(20, 4);
    central.writeUInt16LE(20, 6);
    central.writeUInt16LE(0, 8);
    central.writeUInt16LE(8, 10);
    central.writeUInt16LE(0, 12);
    central.writeUInt16LE(0x2821, 14);
    central.writeUInt32LE(crc, 16);
    central.writeUInt32LE(packed.length, 20);
    central.writeUInt32LE(raw.length, 24);
    central.writeUInt16LE(nameBytes.length, 28);
    central.writeUInt16LE(0, 30);
    central.writeUInt16LE(0, 32);
    central.writeUInt16LE(0, 34);
    central.writeUInt16LE(0, 36);
    central.writeUInt32LE(0, 38);
    central.writeUInt32LE(offset, 42);
    centrals.push(central, nameBytes);

    offset += local.length + nameBytes.length + packed.length;
  }

  const centralSize = centrals.reduce((sum, buf) => sum + buf.length, 0);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(0, 4);
  end.writeUInt16LE(0, 6);
  end.writeUInt16LE(files.length, 8);
  end.writeUInt16LE(files.length, 10);
  end.writeUInt32LE(centralSize, 12);
  end.writeUInt32LE(offset, 16);
  end.writeUInt16LE(0, 20);

  return Buffer.concat([...locals, ...centrals, end]);
}

// --------------------------------------------------------------- package parts

const STYLES = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
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
</styleSheet>`;

const CONTENT_TYPES = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>`;

const ROOT_RELS = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>`;

const WORKBOOK_RELS = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>`;

const WORKBOOK = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets>
  <sheet name="Data" sheetId="1" r:id="rId1"/>
  <sheet name="Summary" sheetId="2" r:id="rId2"/>
</sheets>
</workbook>`;

// ------------------------------------------------------------------------ main

function fail(message: string, code = 3): never {
  console.error(message);
  process.exit(code);
}

function main(argv: string[]): number {
  const [source, explicitTarget] = argv.slice(2);
  if (!source) {
    console.log("usage: node run.ts <input.csv> [output.xlsx]");
    return 2;
  }
  if (!existsSync(source)) {
    console.error(`error: no such file: ${source}`);
    return 2;
  }
  if (extname(source).toLowerCase() !== ".csv") {
    console.error(`error: expected a .csv input, got ${source}`);
    return 2;
  }

  const { header, body } = readCsv(source);
  const { rows: dataRows, numericCols } = buildDataSheet(header, body);
  const summaryRows = buildSummarySheet(header, body, numericCols);

  const target = explicitTarget ?? source.replace(/\.csv$/i, ".xlsx");
  const packageBytes = zip([
    { name: "[Content_Types].xml", data: CONTENT_TYPES },
    { name: "_rels/.rels", data: ROOT_RELS },
    { name: "xl/workbook.xml", data: WORKBOOK },
    { name: "xl/_rels/workbook.xml.rels", data: WORKBOOK_RELS },
    { name: "xl/styles.xml", data: STYLES },
    { name: "xl/worksheets/sheet1.xml", data: sheetXml(dataRows, true) },
    { name: "xl/worksheets/sheet2.xml", data: sheetXml(summaryRows, true) },
  ]);

  mkdirSync(dirname(resolve(target)), { recursive: true });
  writeFileSync(target, packageBytes);
  console.log(
    `wrote ${target}: ${body.length} rows, ${header.length} columns, ${numericCols.length} numeric column(s)`,
  );
  return 0;
}

process.exit(main(process.argv));
