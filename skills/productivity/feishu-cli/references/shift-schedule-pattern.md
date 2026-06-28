# Reading Shift Schedules from Feishu Sheets

Pattern for extracting a user's work shift schedule from a Feishu/Lark
spreadsheet, mapping dates correctly, and building a local JSON cache
that cron jobs can read without hitting the API.

## Step 1: Find the right sheet

Workbooks often have one sheet per month (e.g. `May. 2026`, `June. 2026`,
`July. 2026`). List all sheets:

```bash
lark-cli sheets +workbook-info --spreadsheet-token <token>
```

**Pitfall**: Sheet month labels can be misleading. The "June." sheet may
actually start from late May. Always verify with weekday alignment.

## Step 2: Read the header and target row

The user's schedule row is typically fixed (e.g. Row 11 for @zuojiajie).
Read the full range with `+csv-get` for cleaner output:

```bash
lark-cli sheets +csv-get \
  --spreadsheet-token <token> \
  --sheet-id <sheetId> \
  --range "A1:AU43"
```

Column layout:
- Column A: metadata (是否接单)
- Column B: month label or @name
- Columns C+: dates (day-of-month numbers like 27,28,29,30,31,1,2,...)

Row 1 = dates, Row 2 = weekdays (周三,周四,...), Row N = user's shifts.

## Step 3: Find shift time legend

Shift times are often in the spreadsheet itself, not something to guess.
Check rows 30-45 near the bottom of the sheet. In this case, B34-H40:

| B35 | H35 |
|-----|-----|
| Shift Name | Duration(GMT+8) |
| 早 | 9:00-18:00 |
| 正 | 10:00-19:00 |
| 晚 | 15:00-23:59 |
| 夜 | 23:59-9:00⁺¹ |
| 假 | Day-off |

Read with `+cells-get` focused on the legend area:
```bash
lark-cli sheets +cells-get --spreadsheet-token <token> --sheet-id <id> --range "A34:H40"
```

## Step 4: Date mapping (CRITICAL — most errors happen here)

The header contains day-of-month numbers spanning two months. The FIRST
few values (27,28,29,30,31) are from the PREVIOUS month, and the
subsequent values (1,2,3,...) are from the current month.

**The anchoring technique:**

1. Identify a cell the user confirms is correct (e.g. "AD11 is today's shift")
2. Read that specific cell: `lark-cli sheets +cells-get ... --range "AD1:AD11"`
3. Verify: Row 1 = date number, Row 2 = weekday, Row 11 = shift
4. Cross-check: does the date number + weekday match the calendar?
5. Work backward from the confirmed cell to find the anchor date

**Common failure mode**: Assuming the sheet starts on the 1st of the
labeled month. The "June." sheet actually started at May 27 because
columns C-G held May 27-31 before rolling into June 1 at column H.

In code, the anchor is `date(2026, 5, 27)` (May 27), not `date(2026, 6, 1)`.

## Step 5: Build the local cache

```python
from datetime import date, timedelta

anchor = date(2026, 5, 27)  # verified against calendar weekdays
schedule = {}
for i, shift in enumerate(shifts_list):
    if shift in ('早','正','晚','夜','休','假'):
        schedule[(anchor + timedelta(days=i)).isoformat()] = shift
```

Save as JSON with shift time metadata:

```json
{
  "updated": "2026-06-23",
  "source": "June (5rz4Zy) + July (LUGRPP)",
  "shift_times": { "早": "9:00-18:00", ... },
  "schedule": { "2026-06-23": "晚", ... }
}
```

## Step 6: Merge overlapping sheets

Adjacent month sheets typically overlap by 3-4 days (e.g. June sheet
covers May 27-June 30, July sheet covers June 27-July 31). When merging,
prefer the newer sheet for overlapping dates.

## Cron integration pattern

Instead of reading the Feishu API daily (slow, unreliable), have the
cron read the local JSON file. Refresh the cache manually every 2 weeks
or when a new month's sheet is published.

Cron prompt pattern:
```
Read /path/to/shift-schedule.json. Find today's date in the "schedule"
field. If missing, report "cache expired — ask user to refresh".
Then output shift-appropriate daily plan based on "shift_times" mapping.
```

## Pitfalls

1. **Don't guess the anchor date** — verify with a known cell the user
   confirms (e.g. "AD11 is today"). Weekday labels in Row 2 are your
   cross-reference.
2. **Don't use the May sheet when the June sheet is current** — old
   sheets have outdated data even if they overlap date ranges.
3. **Don't build cron automation before verifying one cell** — get ONE
   cell right first, then build the system.
4. **Date labels in headers are day-of-month only** — you must figure
   out which month from context and weekday alignment.
5. **`+csv-get` is better for bulk reads; `+cells-get` is better for
   verification** of specific cells.
