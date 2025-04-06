# South Australia Public Holiday Calendar

A comprehensive public holiday calendar for South Australia, including public holidays, school terms, and school holidays for the years 2025-2027.

## Features

- Complete list of public holidays for South Australia (2025-2027)
- School terms and holiday periods
- All events formatted as all-day events for maximum compatibility
- Regular automated updates via GitHub Actions
- Properly categorized events

## Quick Links

- [Download the Calendar File](Public-Holiday-Calendar-SA.ics)
- [Public Holiday Source Data](Public%20Holidays%20PDF%20Data/)

## Usage Instructions

### Adding to Google Calendar

1. Go to [Google Calendar](https://calendar.google.com/)
2. Click on the "+" button next to "Other calendars"
3. Select "Import"
4. Click "Select file from your computer" and choose the downloaded `.ics` file
5. Click "Import"

### Adding to Outlook

1. Open Outlook
2. Click on "Calendar" in the navigation bar
3. Click on "File" > "Open & Export" > "Import/Export"
4. Select "Import an iCalendar (.ics) or vCalendar file (.vcs)"
5. Click "Next" and browse to the downloaded `.ics` file
6. Click "Import"

### Adding to Apple Calendar

1. Open Calendar app
2. Click on "File" > "Import"
3. Select the downloaded `.ics` file
4. Click "Import"

## Maintenance and Updates

This calendar is updated quarterly through GitHub Actions automation that checks for new public holiday announcements from the South Australian government.

### Automated Updates

The calendar is automatically updated on the 1st day of:
- January
- April
- July
- October

Each update checks for any changes to the published public holiday schedule and updates the calendar accordingly.

### Manual Updates

If you need to manually update the calendar:

```bash
python update_calendar.py
```

This will download the latest public holiday data from the South Australian government website and update the calendar file.

### Updating School Term Dates

School term dates can be updated when new official dates are released using the included utility script:

```bash
python update_school_terms.py --year 2028 \
  --term1-begin 20280125 --term1-end 20280407 \
  --term2-begin 20280424 --term2-end 20280630 \
  --term3-begin 20280717 --term3-end 20280922 \
  --term4-begin 20281009 --term4-end 20281215 \
  --special-holiday 20280531
```

The script will update both the `create_calendar.py` and `update_calendar.py` scripts to ensure they have consistent term dates.

Arguments:
- `--year`: The year to update (required)
- `--term1-begin`, `--term1-end`: Start and end dates for Term 1
- `--term2-begin`, `--term2-end`: Start and end dates for Term 2
- `--term3-begin`, `--term3-end`: Start and end dates for Term 3
- `--term4-begin`, `--term4-end`: Start and end dates for Term 4
- `--special-holiday`: Date for any special school holiday (optional)

All dates should be in YYYYMMDD format.

### Verification

To verify that the calendar is correctly formatted and contains all expected events:

```bash
python final_verification_flexible.py
```

This will check:
- iCalendar format validity
- Event categories and counts
- Public holidays presence and dates
- School terms and holidays patterns
- Event formatting (all-day events, no brackets)

## Calendar Contents

### Public Holidays

The calendar includes all South Australian public holidays, including:
- New Year's Day
- Australia Day
- Adelaide Cup Day
- Good Friday and Easter holidays
- Anzac Day
- King's Birthday
- Labour Day
- Christmas Eve
- Christmas Day
- Proclamation Day
- New Year's Eve

### School Terms

School terms for 2025-2027 are included with:
- Term begin dates
- Term end dates
- School holiday periods between terms

## Data Sources

- Public holiday data is sourced from the [SafeWork SA website](https://www.safework.sa.gov.au/resources/public-holidays)
- School term dates are from the South Australian Department for Education

## Technical Details

### Files

- `Public-Holiday-Calendar-SA.ics`: The iCalendar file
- `create_calendar.py`: Script to create the initial calendar file
- `update_calendar.py`: Script to update the calendar with the latest data
- `update_school_terms.py`: Utility to update school term dates
- `final_verification.py`: Verification script for specific years
- `final_verification_flexible.py`: Flexible verification script for all years
- `Public Holidays PDF Data/`: Directory containing source PDF files

### GitHub Workflow

The `.github/workflows/update_holidays.yaml` file defines the automation that:

1. Runs quarterly to check for updates
2. Downloads the latest public holiday PDF
3. Parses the holiday dates
4. Updates the calendar file
5. Commits and pushes changes to the repository
6. Updates the GitHub Pages site

## License

This project is free to use for personal and educational purposes.

## Contact

For issues or suggestions, please open an issue on the GitHub repository.

Last updated: April 2024
