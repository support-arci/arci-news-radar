import os
import json
import gspread
from datetime import datetime, timezone, timedelta

# 1. Initialize Google Sheets Client
credentials = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
gc = gspread.service_account_from_dict(credentials)

sheet = gc.open_by_key("1E558JcLuLMyBqclmqrRhvlswMK9FS-NdJw_o3W1C7vI")
worksheet = sheet.worksheet("AI Test")

# 2. Fetch all records from the sheet
records = worksheet.get_all_values()

if len(records) <= 1:
    print("No articles found in sheet.")
    exit()

headers = records[0]
headers_lower = [h.strip().lower() for h in headers]

# Ensure Column H (Image) exists
if len(headers) < 8 or headers_lower[7] != "image":
    worksheet.update_cell(1, 8, "image")

# Ensure Column K (Live/Archived status) exists
if len(headers) < 11 or headers_lower[10] not in ["live/archived", "status", "state"]:
    worksheet.update_cell(1, 11, "Live/Archived")

# 3. Clean up the sheet - Hard Cap at 60 Articles (61 Rows including header)
if len(records) > 61:
    rows_to_delete = len(records) - 61
    worksheet.delete_rows(62, len(records))
    print(f"Deleted {rows_to_delete} excess rows to maintain the 60 article cap.")
    # Re-fetch records after deletion
    records = worksheet.get_all_values()

pending_articles = []
updates = []

# Time cutoffs for archiving
now_utc = datetime.now(timezone.utc)
five_days_ago = now_utc - timedelta(days=5)

# 4. Iterate over rows (starting from Row 2)
for idx, row in enumerate(records[1:], start=2):
    date_str = row[0] if len(row) > 0 else ""
    title = row[1] if len(row) > 1 else ""
    url = row[5] if len(row) > 5 else "" # URL is Column F
    current_status = row[10].strip() if len(row) > 10 else ""
    
    if not title.strip() or not date_str.strip():
        continue

    # Parse ISO Date and Check Age
    try:
        # Handles standard ISO 8601 formatting, replacing 'Z' with explicit UTC offset
        published_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        
        # If older than 5 days, Archive it. Otherwise, Live.
        expected_status = "Archived" if published_date < five_days_ago else "Live"
    except ValueError:
        expected_status = "Live" # Default fallback if date is manually malformed

    # Queue status update if necessary
    if current_status != expected_status:
        updates.append({
            'range': f'K{idx}',
            'values': [[expected_status]]
        })

    # Check for missing images to process (Column H, index 7)
    image = row[7] if len(row) > 7 else ""
    if not image.strip():
        pending_articles.append({
            "rowIndex": idx,
            "title": title.strip(),
            "url": url.strip()
        })

# Batch update live/archived statuses efficiently
if updates:
    worksheet.batch_update(updates)
    print(f"Updated {len(updates)} articles with Live/Archived statuses.")
else:
    print("All article statuses are already up to date.")

print(f"Found {len(pending_articles)} pending article(s) to process images.")

# 5. Save to pending_articles.json
output_file = "pending_articles.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(pending_articles, f, indent=2, ensure_ascii=False)

print(f"Successfully saved to '{output_file}'.")
