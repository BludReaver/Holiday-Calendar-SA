import requests
from bs4 import BeautifulSoup

# URL of the page with future term dates
url = "https://www.education.sa.gov.au/students/term-dates-south-australian-state-schools"

# Make the request
print(f"Requesting {url}...")
response = requests.get(url)
response.raise_for_status()

# Parse the HTML
soup = BeautifulSoup(response.text, 'html.parser')

# Look for headings related to future term dates
print("\n=== HEADINGS CONTAINING 'FUTURE TERM' ===")
for heading in soup.find_all(['h1', 'h2', 'h3', 'h4']):
    text = heading.get_text().strip()
    if 'future term' in text.lower():
        print(f"Found heading: {text}")
        print(f"HTML: {heading}")

# Look for tables
print("\n=== TABLES ON THE PAGE ===")
tables = soup.find_all('table')
print(f"Found {len(tables)} tables")

for i, table in enumerate(tables):
    print(f"\nTable {i+1}:")
    
    # Print table headers if they exist
    headers = table.find_all('th')
    if headers:
        print("Headers:", [h.get_text().strip() for h in headers])
    
    # Print first few rows of data
    rows = table.find_all('tr')
    print(f"Total rows: {len(rows)}")
    
    for j, row in enumerate(rows[:3]):  # Print only first 3 rows
        cells = row.find_all(['td', 'th'])
        if cells:
            print(f"  Row {j+1}: {[cell.get_text().strip() for cell in cells]}")
    
    if len(rows) > 3:
        print("  ...")

# Now look specifically for the future term dates section
print("\n=== LOOKING FOR FUTURE TERM DATES SECTION ===")

# First, try to find the heading
future_term_heading = None
for heading in soup.find_all(['h2', 'h3']):
    if 'future term dates' in heading.get_text().lower():
        future_term_heading = heading
        print(f"Found heading: {heading.get_text().strip()}")
        break

if future_term_heading:
    # Look for the nearest table after this heading
    future_table = future_term_heading.find_next('table')
    
    if future_table:
        print("\nFound future term dates table!")
        print("Table HTML structure:", future_table)
        
        # Print all rows in the table to understand its structure
        rows = future_table.find_all('tr')
        print(f"\nTotal rows in future terms table: {len(rows)}")
        
        for i, row in enumerate(rows):
            cells = row.find_all(['td', 'th'])
            print(f"Row {i+1}: {[cell.get_text().strip() for cell in cells]}")
    else:
        print("Could not find a table after the future term dates heading")
else:
    print("Could not find a heading for future term dates") 