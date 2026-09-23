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

# Ensure Column H has a header ("AI Output")
headers = records[0]
if len(headers) < 8 or headers[7] != "AI Output":
    worksheet.update_cell(1, 8, "AI Output")

pending_articles = []

# 3. Iterate over rows (starting from Row 2) to find unprocessed articles
for idx, row in enumerate(records[1:], start=2):
    title = row[1] if len(row) > 1 else ""
    description = row[2] if len(row) > 2 else ""
    source = row[3] if len(row) > 3 else ""
    url = row[4] if len(row) > 4 else ""
    ai_output = row[7] if len(row) > 7 else ""

    # Skip if title is missing or if AI Output is already filled
    if not title.strip() or ai_output.strip():
        continue

    pending_articles.append({
        "rowIndex": idx,
        "title": title.strip(),
        "description": description.strip(),
        "source": source.strip(),
        "url": url.strip()
    })

print(f"Found {len(pending_articles)} pending article(s) to process.")

# 4. Save to pending_articles.json
output_file = "pending_articles.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(pending_articles, f, indent=2, ensure_ascii=False)

print(f"Successfully saved to '{output_file}'.")
