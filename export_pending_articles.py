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

# Ensure Column H has a header
headers = records[0]
if len(headers) < 8 or headers[7] != "AI Output":
    worksheet.update_cell(1, 8, "AI Output")

pending_articles = []

# 3. Iterate over rows (starting from Row 2) to find unprocessed articles
for idx, row in enumerate(records[1:], start=2):
    article_date = row[0] if len(row) > 0 else ""
    title = row[1] if len(row) > 1 else ""
    description = row[2] if len(row) > 2 else ""
    source = row[3] if len(row) > 3 else ""
    url = row[4] if len(row) > 4 else ""
    image_url = row[6] if len(row) > 6 else ""
    ai_output = row[7] if len(row) > 7 else ""

    # Skip if title is missing or if AI output has already been filled in
    if not title or ai_output.strip():
        continue

    # Format the prompt/text ready for your GPT automation
    prompt_text = f"Source: {source}\nTitle: {title}\nDescription: {description}\nURL: {url}"

    pending_articles.append({
        "rowIndex": idx,
        "articleDate": article_date,
        "title": title,
        "description": description,
        "source": source,
        "url": url,
        "imageUrl": image_url,
        "gptPromptInput": prompt_text
    })

# 4. Output the pending articles
print(f"Found {len(pending_articles)} pending article(s) to process.\n")

for item in pending_articles:
    print(f"--- Row {item['rowIndex']} ---")
    print(f"Title:  {item['title']}")
    print(f"URL:    {item['url']}")
    print(f"Prompt:\n{item['gptPromptInput']}\n")

# 5. Save to a JSON file for easy integration with external scripts/automations
output_file = "pending_articles.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(pending_articles, f, indent=2, ensure_ascii=False)

print(f"Successfully saved {len(pending_articles)} article(s) to '{output_file}'.")
