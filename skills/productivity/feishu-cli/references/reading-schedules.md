# Reading Shift Schedules and Monthly Calendars from Feishu Sheets

When a user points you to a Feishu sheet containing a monthly shift schedule
or calendar-style layout, the date mapping is the most common source of bugs.
Follow this pattern.

## 1. Always verify with a known reference cell first

Before bulk-reading the sheet, ask the user for one known data point:
"今天的排班是什么？在哪个单元格？"

Or read a single confirmed cell:
```
lark-cli sheets +cells-get --spreadsheet-token <token> --sheet-id <id> --range "AD11:AD11"
```

Match the returned value against the user's confirmed shift. If they don't
match, your date mapping is wrong — stop and fix it before bulk reading.

## 2. Date mapping: sheets often span month boundaries

Monthly sheets labeled e.g. "June. 2026" may actually start from the PREVIOUS
month. Example: a "June" sheet with header `27,28,29,30,31,1,2,3,...` started
from May 27, not June 27.

**How to verify**: check the weekday of column C against the actual calendar.
If column C = `27` and `周三`, but June 27 is a Saturday, then column C is
May 27 (which IS a Wednesday).

Anchor formula:
```
anchor = date(year, month_of_first_verified_date, first_date_value)
# e.g., date(2026, 5, 27) for a "June" sheet starting May 27
```

## 3. Always check the legend / metadata cells

Shift schedules often have a legend row explaining what each value means.
Example: cells B34-H40 contained:

| B35 | H35 |
|-----|-----|
| Shift Name | Duration(GMT+8) |
| 早 | 9:00-18:00 |
| 正 | 10:00-19:00 |
| 晚 | 15:00-23:59 |
| 夜 | 23:59-9:00⁺¹ |

Never assume shift times. Read the legend from the sheet.

## 4. User row is usually fixed

If the user says "我的排班永远在第11行", hard-code the row number.
Don't search for their name every time.

## 5. Prefer local cache over repeated API calls

If the schedule is stable (published a month in advance), read once,
save to a local JSON file, and read from there. This avoids:
- API rate limits
- Token bloat from re-parsing
- Auth expiry mid-read

Save format:
```json
{
  "updated": "2026-06-23",
  "source": "June.2026 sheet (5rz4Zy) — Row 11",
  "shift_times": { "早": "9:00-18:00", ... },
  "schedule": { "2026-06-23": "晚", "2026-06-24": "晚", ... }
}
```

## 6. Multi-sheet merging

When a schedule workbook has monthly sheets (May, June, July...):
- Each sheet's anchor must be independently verified
- Later sheets take precedence for overlapping dates
- The "month label" is unreliable — always verify via weekday alignment

## Common Pitfalls

- **Trusting the sheet's month label**: "June. 2026" may start May 27. Verify.
- **Assuming date 31 exists**: June has 30 days; the "31" in a header may be
  July 1 or a display artifact.
- **Using `+csv-get` without `+cells-get` verification**: csv-get is faster
  but can hide date mapping issues. Verify one known cell with cells-get first.
- **Reading the wrong sheet**: workbooks have multiple sheets (May, June, July).
  Ask the user which sheet is current, or read the sheet they linked to.
