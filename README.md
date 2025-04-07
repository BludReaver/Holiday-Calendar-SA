# South Australia Public Holidays Calendar

A clean, automatically updating calendar of South Australian public holidays with simplified event names.

## Features

- Automatically fetches South Australian public holidays from [officeholidays.com](https://www.officeholidays.com/ics-all/australia/south-australia)
- Removes text in parentheses (like "Regional Holiday" or "Not a Public Holiday") for cleaner display
- Maintains the original format and technical specifications
- Updates quarterly via GitHub Actions
- Sends notifications on success/failure (optional via Pushover)

## Example Clean-ups

- "Adelaide Cup (Regional Holiday)" → "Adelaide Cup"
- "Mother's Day (Not a Public Holiday)" → "Mother's Day"
- "Easter Saturday (Regional Holiday)" → "Easter Saturday"
- "King's Birthday (Regional Holiday)" → "King's Birthday"

## Using the Calendar

You can subscribe to this calendar in your preferred calendar application by using the raw URL:
```
https://raw.githubusercontent.com/BludReaver/Public-Holiday-Calendar-SA/main/SA-Public-Holidays.ics
```

### In Google Calendar:
1. Click the "+" next to "Other calendars"
2. Choose "From URL"
3. Paste the raw URL above
4. Click "Add calendar"

### In Outlook:
1. Go to Calendar
2. Click "Add calendar" > "Subscribe from web"
3. Paste the raw URL above
4. Click "Import"

### In Apple Calendar:
1. Click "File" > "New Calendar Subscription"
2. Paste the raw URL above
3. Click "Subscribe"

## How It Works

The script runs automatically through GitHub Actions at the beginning of each quarter (January, April, July, October) at 10:30 AM Adelaide time, accounting for daylight saving time.

When it runs:
1. It downloads the latest calendar from officeholidays.com
2. Cleans up the event names by removing text in parentheses
3. Saves the updated ICS file
4. Commits the changes back to the repository

## Technical Details

This calendar is maintained by a Python script that:
1. Downloads the iCalendar file from officeholidays.com
2. Uses regular expressions to clean the event summaries
3. Preserves all original formatting, language attributes, and other properties
4. Updates the calendar file in this repository

## Setting Up Your Own Version

1. Fork this repository
2. (Optional) Set up Pushover API keys for notifications:
   - Create a [Pushover](https://pushover.net/) account
   - Create an application to get an API token
   - Add secrets to your repository:
     - `PUSHOVER_USER_KEY`
     - `PUSHOVER_APP_TOKEN`

3. The GitHub Action will run automatically according to the schedule

## Local Development

To run this script locally:

```bash
# Install dependencies
pip install requests httpx

# Run the script
python update_sa_holidays.py
```

## License

This project is free to use for personal and educational purposes. 