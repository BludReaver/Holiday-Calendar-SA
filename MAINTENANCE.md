# Maintenance Guide

This document provides guidance for maintaining the South Australia Public Holiday Calendar, including known issues, troubleshooting steps, and future enhancement opportunities.

## Calendar Maintenance Cycle

The calendar follows a quarterly update cycle:

1. **January 1st**: Update to check for any changes to Q1 and Q2 holidays
2. **April 1st**: Update to check for any changes to Q2 and Q3 holidays
3. **July 1st**: Update to check for any changes to Q3 and Q4 holidays
4. **October 1st**: Update to check for any changes to Q4 and next year's Q1 holidays

## Common Issues and Troubleshooting

### PDF Download Issues

If the automated PDF download fails:

1. Check if the URL in `update_calendar.py` is still valid
2. Manually download the PDF from the [SafeWork SA website](https://www.safework.sa.gov.au/resources/public-holidays)
3. Place the PDF in the `Public Holidays PDF Data` folder
4. Run `python update_calendar.py` manually

### PDF Parsing Issues

If the PDF format changes and can't be parsed correctly:

1. Open the PDF manually and examine its structure
2. Update the regex patterns in `update_calendar.py` to match the new format
3. Test the parsing with `python test_pdf_parsing.py`

### School Term Date Updates

When school term dates for a new year are released:

1. Use the `update_school_terms.py` utility to update both calendar scripts
2. Run verification to confirm the changes were applied correctly
3. Run `python create_calendar.py` to regenerate the calendar

## Known Issues

1. **Part-Day Holidays**: The calendar treats all holidays as all-day events, even those that are legally part-day holidays (Christmas Eve, New Year's Eve, etc.)

2. **Date Substitution Logic**: Some public holidays "observed on" dates for holidays falling on weekends may need manual verification, as the rules can change.

3. **Additional School Holidays**: One-off school holidays announced by the Department for Education might not be automatically captured and may require manual addition.

4. **PDF Format Dependency**: The calendar updater relies on the PDF format remaining consistent. If the SafeWork SA significantly changes their PDF format, the parser will need updates.

## Future Enhancement Opportunities

1. **Web Scraping Alternative**: Implement a web scraping option as a fallback if the PDF download or parsing fails.

2. **Email Notifications**: Add notifications for successful/failed updates or when manual intervention is needed.

3. **Improved Verification**: Enhance the verification scripts to check against official government websites for confirmation.

4. **Multi-Regional Support**: Expand the calendar to include other Australian states and territories.

5. **Mobile App Integration**: Create direct integration options for popular mobile calendar apps.

6. **Documentation Website**: Create a simple website with instructions for using the calendar and reporting issues.

7. **Add Event Descriptions**: Include more detailed descriptions for each holiday, including historical context or relevant information.

8. **Support for Different Calendar Formats**: Add support for other calendar formats beyond iCalendar.

## PDF Source Documentation

The public holidays are sourced from SafeWork SA's official PDF publications. Current and historical PDFs are stored in the `Public Holidays PDF Data` directory.

The PDF format typically includes:
- Table of public holidays with dates
- Notes about substitution days
- Part-day holiday information

If the PDF format changes, you may need to update the regular expressions in `update_calendar.py`.

## Verification Process

Always run the verification scripts after making changes:

```bash
python final_verification_flexible.py
```

This script performs the following checks:
- iCalendar format validity
- Event categorization
- Total event counts
- Event distribution by year
- Proper event formatting
- School term consistency

## Contact Information

If you encounter issues that aren't covered in this guide, please:

1. Check the [GitHub Issues](https://github.com/yourusername/Public-Holiday-Calendar-SA/issues) for similar problems
2. Create a new issue with detailed information about the problem
3. Include relevant log files or screenshots to help with debugging

## Version History

Maintain a record of significant updates to the calendar:

- **April 2024**: Initial calendar creation with holidays for 2025-2027
- **July 2024**: Update with latest school term dates (hypothetical)
- **January 2025**: Update with any revised 2025 holiday dates (hypothetical) 