import os
import json
import gspread
from datetime import datetime, timezone, timedelta

# 1. Initialize Google Sheets Client
credentials = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
gc = gspread.service_account_from_dict(credentials)

sheet = gc.open_by_key("1E558JcLuLMyBqclmqrRhvlswMK9FS-NdJw_o3W1C7vI")
worksheet = sheet.worksheet("AI Test")

# 2. Fetch all records infinitely from Columns A through N
records = worksheet.get("A1:N")

if not records or len(records) <= 1:
    print("No articles found in sheet.")
    exit()

pending_articles = []
updates = []

now_utc = datetime.now(timezone.utc)
five_days_ago = now_utc - timedelta(days=5)

# 3. Process Statuses Based on 5-Day Rule for ALL rows
for idx, row in enumerate(records[1:], start=2):
    date_str = row[0] if len(row) > 0 else ""
    title = row[13] if len(row) > 13 else (row[1] if len(row) > 1 else "") 
    url = row[5] if len(row) > 5 else "" 
    current_status = row[10].strip() if len(row) > 10 else "" 
    
    if not title.strip():
        continue

    # Live if <= 5 days old, Archived if > 5 days old
    expected_status = "Live"
    if date_str.strip():
        try:
            published_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            if published_date < five_days_ago:
                expected_status = "Archived"
        except ValueError:
            expected_status = "Live"

    # Queue Column K update if status changed
    if current_status != expected_status:
        updates.append({
            'range': f'K{idx}',
            'values': [[expected_status]]
        })

    # Check for missing images
    image = row[12] if len(row) > 12 else (row[7] if len(row) > 7 else "")
    if not image.strip():
        pending_articles.append({
            "rowIndex": idx,
            "title": title.strip(),
            "url": url.strip()
        })

# Batch update live/archived statuses in Column K
if updates:
    worksheet.batch_update(updates)
    print(f"Updated status for {len(updates)} article(s) to Live/Archived.")
else:
    print("All article statuses are up to date.")

# 4. Save pending articles to JSON
output_file = "pending_articles.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(pending_articles, f, indent=2, ensure_ascii=False)

print(f"Successfully saved pending articles to '{output_file}'.")
