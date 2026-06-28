# Reading Feishu Spreadsheets with lark-cli

Patterns for reading and extracting data from Feishu/Lark spreadsheets 
programmatically via `lark-cli`. Builds on the setup in `feishu-cli` SKILL.md.

## Quick Reference

```bash
# Best for data extraction: annotated CSV with row/col tracking
lark-cli sheets +csv-get --spreadsheet-token <TOKEN> --sheet-id <SHEET> --range "A1:Z50"

# For rich data (styles, validation, merges):
lark-cli sheets +cells-get --spreadsheet-token <TOKEN> --sheet-id <SHEET> --range "A1:Z50"

# List all sheets in a workbook:
lark-cli sheets +workbook-info --spreadsheet-token <TOKEN>
```

## Flag Conventions

All flags use **kebab-case** (hyphens), NOT camelCase:
```bash
--spreadsheet-token   # ✓ correct
--sheet-id            # ✓ correct
--spreadsheetToken    # ✗ wrong — will error with a hint
```

## Extracting Token and Sheet ID from URL

URL: `https://bytedance.larkoffice.com/sheets/EhxnsaYIahyTekttmBocmILQnEc?sheet=5rz4Zy`

- `spreadsheetToken`: `EhxnsaYIahyTekttmBocmILQnEc` (the segment after `/sheets/`)
- `sheetId`: `5rz4Zy` (the `?sheet=` query param)

## Parsing +csv-get Output

The `+csv-get` output wraps each row with `[row=N]` prefix:

```json
{
  "annotated_csv": "[row=1] ColA,ColB,ColC\n[row=2] val1,val2,val3\n...",
  "row_indices": [1, 2, 3, ...],
  "col_indices": ["A", "B", "C", ...]
}
```

**Critical**: Use `[row=N]` prefix to get the REAL row number. Do NOT count 
rows yourself — hidden rows, merged cells, and truncation will shift your count.
The `row_indices` array maps positions back to actual spreadsheet row numbers.

## Finding a Person's Row

Multi-person schedule sheets have one row per person with an @mention in column B.
To find a specific person:

```bash
lark-cli sheets +csv-get ... | python3 -c "
import sys, json
d = json.load(sys.stdin)
csv = d['data']['annotated_csv']
for line in csv.split('\n'):
    if 'zuojiajie' in line.lower():  # search by name
        print(line)
"
```

## Multi-Sheet Month Workbooks

Schedule workbooks often have one sheet per month (e.g., "May. 2026", "June. 2026").
When a date falls near a month boundary:

1. First call `+workbook-info` to list all sheets
2. Identify the correct sheet by date range (check header row values)
3. Each sheet's header row contains the dates it covers

**Pitfall**: Dates spanning month boundaries. A "June" sheet may start at June 27 
(continuing from a May sheet that ends at June 26). Month names on sheets are 
approximate — always check the actual date range in the header.

**Pitfall (high-cost)**: Multi-sheet overlap. May sheet may cover 5/26-6/30 while 
June sheet covers 6/27-7/30 — 4 days appear in BOTH sheets. If the user points 
to a specific sheet (e.g., "use the June sheet"), use THAT sheet. Don't second-guess 
by reading the "earlier" sheet that also covers the date. When the user gives a URL 
with `?sheet=<id>`, that sheet ID is the authoritative source.

**Pitfall (highest-cost)**: Date-header mapping errors. If you read a value from 
a date column and the user says it's wrong, do NOT try to debug by reasoning about 
month boundaries or May-has-31-days. Immediately re-read the sheet with a targeted 
`+cells-get` query on just the header row, and verify with the user which column 
maps to which date. Never argue with the user about their own schedule.

## Parsing Date Headers

Date headers use bare numbers (27, 28, 29, 30, 31, 1, 2, 3...). The transition 
from e.g. 30→1 indicates a month boundary. Row 2 typically has weekday labels 
(周一, 周二, ...) for verification.

**Pitfall**: May has 31 days but some sheets skip May 31 and go 30 → June 1. 
Always match against the weekday row (Row 2) to verify date alignment.

## Output Size and Truncation

`+cells-get` may truncate large outputs (500K+ chars). Watch for:
- `"truncated": true` in range objects
- `"has_more": true` at top level
- `warning_message` with truncation details

If truncated, narrow the `--range` and make multiple calls. Prefer `+csv-get` 
for data extraction — it handles larger ranges more efficiently.

## Example: Full Pipeline

```bash
# 1. Find the right sheet
lark-cli sheets +workbook-info --spreadsheet-token <TOKEN> | \
  python3 -c "import sys,json; [print(s['sheet_name'], s['sheet_id']) for s in json.load(sys.stdin)['data']['sheets']]"

# 2. Read header + target person row
lark-cli sheets +csv-get --spreadsheet-token <TOKEN> --sheet-id <ID> --range "A1:AU43" | \
  python3 -c "
import sys, json
d = json.load(sys.stdin)
for line in d['data']['annotated_csv'].split('\n'):
    if 'zuojiajie' in line.lower() or '[row=1]' in line or '[row=2]' in line:
        print(line)
"

# 3. Map date to shift value using header row positions
```

## Cron Integration Pattern

When building adaptive cron jobs that read Feishu schedules:

- Use `enabled_toolsets: ["terminal"]` to keep cron light
- The cron prompt must be self-contained with the spreadsheet token and sheet IDs
- Include instructions for handling both month sheets near boundaries
- Fall back gracefully if `lark-cli` auth has expired (token auto-refresh usually works)

## Finding Metadata / Lookup Tables Within Sheets

Schedule sheets often contain metadata below the data rows — shift time definitions,
legend keys, or lookup tables. These are NOT in column headers; they're in body rows
well below the schedule data.

**Pattern**: The user says "the shift times are in the sheet at B34". Query that area:
```bash
lark-cli sheets +cells-get ... --range "A34:H40"
```
In this case B34-H40 contained a mini lookup table:
- B35="Shift Name", H35="Duration(GMT+8)"
- B36="早", H36="9:00-18:00"
- B37="正", H37="10:00-19:00"
- B38="晚", H38="15:00-23:59"
- B39="夜", H39="23:59-9:00⁺¹"
- B40="假", H40="Day-off"

**Takeaway**: When you see coded values in cells (早, 正, 晚, 夜, 休), do NOT guess
their meaning. Search the sheet for a legend or lookup table. The user often knows
exactly where it is — ask "where in the sheet are these defined?" before inventing
time mappings.

## Targeted Range Queries

Avoid reading entire sheets (A1:AU43) when you only need specific data. Use narrow ranges:

```bash
# Just the header to verify date columns
lark-cli sheets +cells-get ... --range "C1:AL1"

# Just one person's row
lark-cli sheets +cells-get ... --range "C12:AL12"

# A specific metadata block
lark-cli sheets +cells-get ... --range "A34:H40"
```

This reduces output by 90%+ and avoids truncation. Use `+csv-get` with broader
ranges for initial discovery, then switch to `+cells-get` with narrow ranges when
you know exactly which rows/columns you need.
