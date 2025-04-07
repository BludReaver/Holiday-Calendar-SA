# South Australia Holidays Calendar

A clean, automatically updating calendar of South Australian public holidays and school terms with simplified event names.

## Features

- Automatically fetches South Australian public holidays from [officeholidays.com](https://www.officeholidays.com/ics-all/australia/south-australia)
- Removes text in parentheses (like "Regional Holiday" or "Not a Public Holiday") for cleaner display
- Maintains the original format and technical specifications for Google Calendar compatibility
- Includes school terms and holiday periods from [education.sa.gov.au](https://www.education.sa.gov.au/students/term-dates-south-australian-state-schools)
- Standardized format across both calendars for consistent display in calendar apps
- Robust error handling with user-friendly notifications
- Updates quarterly via GitHub Actions
- Sends notifications on success/failure (optional via Pushover)

## Example Clean-ups

- "Adelaide Cup (Regional Holiday)" → "Adelaide Cup"
- "Mother's Day (Not a Public Holiday)" → "Mother's Day"
- "Easter Saturday (Regional Holiday)" → "Easter Saturday"
- "King's Birthday (Regional Holiday)" → "King's Birthday"

## Available Calendars

### Public Holidays Calendar

You can subscribe to the public holidays calendar in your preferred calendar application by using the raw URL:
```
https://raw.githubusercontent.com/BludReaver/Holiday-Calendar-SA/main/SA-Public-Holidays.ics
```

### School Terms and Holidays Calendar

You can subscribe to the school terms and holidays calendar using the raw URL:
```
https://raw.githubusercontent.com/BludReaver/Holiday-Calendar-SA/main/SA-School-Terms-Holidays.ics
```
This calendar includes:
- Term start dates
- Term end dates
- School holiday periods between terms

### Adding to Your Calendar App

#### In Google Calendar:
1. Click the "+" next to "Other calendars"
2. Choose "From URL"
3. Paste the raw URL for the calendar you want
4. Click "Add calendar"

#### In Outlook:
1. Go to Calendar
2. Click "Add calendar" > "Subscribe from web"
3. Paste the raw URL
4. Click "Import"

#### In Apple Calendar:
1. Click "File" > "New Calendar Subscription"
2. Paste the raw URL
3. Click "Subscribe"

## How It Works

The script runs automatically through GitHub Actions at the beginning of each quarter (January, April, July, October) at 10:30 AM Adelaide time, accounting for daylight saving time.

When it runs:
1. It downloads the latest public holidays from officeholidays.com
2. Cleans up the event names by removing text in parentheses
3. Downloads the latest school terms from education.sa.gov.au
4. Generates school holiday periods between terms
5. Creates ICS calendar files with consistent formatting for maximum compatibility
6. Commits the changes back to the repository

## Technical Details

This calendar is maintained by a Python script that:
1. Downloads the iCalendar files from official sources
2. Uses regular expressions to clean the event summaries
3. Preserves all original formatting, language attributes, and other properties
4. Ensures consistent formatting between calendars for maximum compatibility with Google Calendar and other applications
5. Handles errors intelligently with specific error messages for different failure modes
6. Processes each calendar independently, allowing partial success even if one calendar source fails
7. Provides detailed notifications to help troubleshoot any issues

## Error Handling Features

The script includes robust error handling for various scenarios:
- Connection issues to source websites
- 404 errors if calendar files are moved or renamed
- Permission errors when saving files
- Missing or empty school terms data
- General exceptions with user-friendly messages

## Setting Up Your Own Version

1. Fork this repository
2. (Optional) Set up Pushover API keys for notifications:
   - Create a [Pushover](https://pushover.net/) account
   - Create an application to get an API token
   - Add secrets to your repository:
     - `PUSHOVER_USER_KEY`
     - `PUSHOVER_API_TOKEN`

3. The GitHub Action will run automatically according to the schedule

## Local Development

To run this script locally:

```bash
# Install dependencies from requirements.txt
pip install -r requirements.txt

# Run the script
python update_sa_holidays.py

# Run tests with simulated errors (optional)
python -c "import update_sa_holidays; update_sa_holidays.TEST_MODE=True; update_sa_holidays.ERROR_SIMULATION='404'; update_sa_holidays.main()"
```

### Available Error Simulations

For testing, you can set `TEST_MODE` to `True` and `ERROR_SIMULATION` to one of:
- `"public_holidays"` - Simulate failure downloading public holidays
- `"school_terms"` - Simulate failure downloading school terms
- `"both"` - Simulate failure downloading both calendars
- `"connection"` - Simulate connection issues
- `"404"` - Simulate 404 errors
- `"permission"` - Simulate permission errors
- `"no_terms"` - Simulate missing school terms data

## License

This project is free to use for personal and educational purposes. 