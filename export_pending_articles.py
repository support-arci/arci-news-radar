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

# 3. Hard Cap at 60 Articles (61 Rows including header)
MAX_TOTAL_ARTICLES = 60
if len(records) > (MAX_TOTAL_ARTICLES + 1):
    rows_to_delete = len(records) - (MAX_TOTAL_ARTICLES + 1)
    worksheet.delete_rows(MAX_TOTAL_ARTICLES + 2, len(records))
    print(f"Pruned {rows_to_delete} older rows to maintain the 60-article maximum limit.")
    records = worksheet.get_all_values()

pending_articles = []
updates = []

now_utc = datetime.now(timezone.utc)
five_days_ago = now_utc - timedelta(days=5)

# 4. Process Statuses Based on 5-Day Rule
for idx, row in enumerate(records[1:], start=2):
    date_str = row[0] if len(row) > 0 else ""
    title = row[13] if len(row) > 13 else (row[1] if len(row) > 1 else "") # Prefers N (article_title), falls back to B
    url = row[5] if len(row) > 5 else "" # URL is Column F
    current_status = row[10].strip() if len(row) > 10 else "" # Column K
    
    if not title.strip():
        continue

    # Determine status: Live if <= 5 days old, Archived if > 5 days old
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

    # Check for missing images to process (Column M, index 12 - falling back to H, index 7)
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
    print(f"Updated status for {len(updates)} article(s) in Column K.")
else:
    print("All article statuses in Column K are up to date.")

print(f"Found {len(pending_articles)} pending article(s) needing image processing.")

# 5. Save pending articles to JSON for GPT processing
output_file = "pending_articles.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(pending_articles, f, indent=2, ensure_ascii=False)

print(f"Successfully saved to '{output_file}'.")
