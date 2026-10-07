import os
import json
import gspread

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
if len(headers) < 8 or headers[7].lower() != "image":
    worksheet.update_cell(1, 8, "image")

# Ensure Column K (Live/Archived status) exists
if len(headers) < 11 or headers_lower[10] not in ["live/archived", "status", "state"]:
    worksheet.update_cell(1, 11, "Live/Archived")

pending_articles = []
updates = []

# Number of articles to keep "Live" on the front page
MAX_LIVE_ARTICLES = 15

# 3. Iterate over rows (starting from Row 2)
for idx, row in enumerate(records[1:], start=2):
    title = row[1] if len(row) > 1 else ""
    url = row[4] if len(row) > 4 else ""
    current_status = row[10].strip() if len(row) > 10 else ""
    
    # Determine Status: Newest items at the top get 'Live', older push down to 'Archived'
    expected_status = "Live" if (idx - 1) <= MAX_LIVE_ARTICLES else "Archived"

    if not title.strip():
        continue

    # Queue status update if necessary
    if current_status != expected_status:
        updates.append({
            'range': f'K{idx}',
            'values': [[expected_status]]
        })

    # Check for missing images to process
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

print(f"Found {len(pending_articles)} pending article(s) to process images.")

# 4. Save to pending_articles.json
output_file = "pending_articles.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(pending_articles, f, indent=2, ensure_ascii=False)

print(f"Successfully saved to '{output_file}'.")
