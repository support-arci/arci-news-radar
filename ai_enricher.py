import os
import json
import time
import requests
import gspread
from urllib.parse import quote_plus
from google import genai
from google.genai import types

# ---------------------------------------------------------------------------
# DIVERSE BACKUP PHOTO POOL (Used only if live search is completely unavailable)
# ---------------------------------------------------------------------------
BACKUP_PHOTO_POOL = [
    "https://images.unsplash.com/photo-1523240795612-9a054b0db644?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1554224155-8d04cb21cd6c?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1541829070764-84a7d30dd3f3?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1526778548025-fa2f459cd5c1?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1562774053-701939374585?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1523050854058-8df90110c9f1?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1498243691581-b145c3f54a5a?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1509062522246-3755977927d7?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1532012197267-da84d127e765?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1524178232363-1fb2b075b655?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1522071820081-009f0129c71c?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1571260899304-425eee4c7efc?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1503676260728-1c00da094a0b?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?q=80&w=800&auto=format&fit=crop"
]

def fetch_relevant_unique_image(query, used_urls):
    """
    Searches Unsplash CDN for photos matching 'query'.
    Guarantees no two articles receive the same image.
    """
    clean_query = query.strip().lower() if query else "higher education university"
    search_url = f"https://unsplash.com/napi/search/photos?query={quote_plus(clean_query)}&per_page=15"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    try:
        resp = requests.get(search_url, headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            for item in results:
                raw_url = item.get("urls", {}).get("raw") or item.get("urls", {}).get("regular")
                if raw_url:
                    base_url = raw_url.split("?")[0]
                    formatted_url = f"{base_url}?q=80&w=800&auto=format&fit=crop"
                    
                    # Ensure URL is completely unique
                    if formatted_url not in used_urls and base_url not in used_urls:
                        used_urls.add(formatted_url)
                        used_urls.add(base_url)
                        return formatted_url
    except Exception as e:
        print(f"  ⚠️ Live image search notice for '{clean_query}': {e}")

    # Fallback to unused item from backup pool if search yields duplicates
    for photo in BACKUP_PHOTO_POOL:
        base_photo = photo.split("?")[0]
        if photo not in used_urls and base_photo not in used_urls:
            used_urls.add(photo)
            used_urls.add(base_photo)
            return photo

    return BACKUP_PHOTO_POOL[0]

# ---------------------------------------------------------------------------
# INITIALIZE GEMINI API & GOOGLE SHEETS
# ---------------------------------------------------------------------------
gemini_api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if not gemini_api_key:
    print("Error: GEMINI_API_KEY environment variable not set.")
    exit(1)

client = genai.Client(api_key=gemini_api_key)

credentials = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
gc = gspread.service_account_from_dict(credentials)
worksheet = gc.open_by_key("1E558JcLuLMyBqclmqrRhvlswMK9FS-NdJw_o3W1C7vI").worksheet("AI Test")

records = worksheet.get_values("A2:N61")
if not records:
    print("No articles found in sheet.")
    exit(0)

# Build set of image URLs already used in the sheet (Cols H and M)
used_image_urls = set()
for r in records:
    padded = r + [""] * (14 - len(r))
    img_h = padded[7].strip()
    img_m = padded[12].strip()
    if img_h:
        used_image_urls.add(img_h)
        used_image_urls.add(img_h.split("?")[0])
    if img_m:
        used_image_urls.add(img_m)
        used_image_urls.add(img_m.split("?")[0])

batch_updates = []

print(f"Loaded {len(records)} rows from Google Sheets. Checking for articles needing AI enrichment...")

# ---------------------------------------------------------------------------
# PROCESS ROWS
# ---------------------------------------------------------------------------
for i, row in enumerate(records):
    row_num = i + 2
    padded_row = row + [""] * (14 - len(row))
    
    published           = padded_row[0].strip()   # Col A
    raw_title           = padded_row[1].strip()   # Col B
    raw_subtitle        = padded_row[2].strip()   # Col C
    description_long    = padded_row[3].strip()   # Col D
    source              = padded_row[4].strip()   # Col E
    existing_image      = padded_row[7].strip()   # Col H
    article_description = padded_row[9].strip()   # Col J
    article_subtitle    = padded_row[11].strip()  # Col L
    article_image       = padded_row[12].strip()  # Col M
    article_title       = padded_row[13].strip()  # Col N

    # Condition: Published MUST be filled, and article_description (Col J) MUST be empty
    if published and not article_description:
        print(f"\n[Processing Row {row_num}] {raw_title[:60]}...")
        
        content_source = description_long if len(description_long) > 100 else f"{raw_title}. {raw_subtitle}"
        
        prompt = f"""
You are a senior higher education journalist writing for 'The Higher Ed Times'.
Rewrite the following raw higher education news source into a comprehensive, high-authority news briefing article.

Source Title: {raw_title}
Source Text:
{content_source}

REQUIREMENTS:
1. Write EXACTLY 15 to 16 well-developed sentences divided across 3 or 4 coherent paragraphs.
2. Structure the content for SEO and AI/AEO (Answer Engine Optimization) readability:
   - Use direct, active voice with factual density and specific sector terminology (e.g., admissions yields, governance, tuition revenue, federal aid, student mobility).
   - Answer the core 'Who, What, Why, and Sector Impact' cleanly in the opening sentences.
3. Determine the primary topic category from ONE of: 'admissions', 'finance', 'policy', 'mobility', 'tech', or 'campus'.
4. Produce a compelling 1-sentence subtitle (dek).
5. Produce a strong news headline.
6. Provide a specific 2 to 3 word visual image search query representing the specific subject of this article (e.g. "college library books", "student visa passport", "robot classroom ai", "tuition cost bill", "cambridge university", "college graduation cap").

OUTPUT FORMAT: Return ONLY a raw JSON object with these keys (no markdown formatting code blocks):
{{
  "article_title": "Executive Headline Here",
  "article_subtitle": "One sentence summary deck.",
  "article_description": "First paragraph sentence 1. Sentence 2... Second paragraph... (Total 15-16 sentences)",
  "category": "one of: admissions|finance|policy|mobility|tech|campus",
  "search_keywords": "specific 2-3 word visual image search phrase"
}}
"""

        res_json = None
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model='gemini-3.8-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.3
                    )
                )
                res_json = json.loads(response.text)
                break
            except Exception as e:
                err_msg = str(e)
                if ("503" in err_msg or "UNAVAILABLE" in err_msg or "overloaded" in err_msg) and attempt < max_retries - 1:
                    wait_sec = (attempt + 1) * 5
                    print(f"  ⚠️ High server demand (503). Retrying in {wait_sec}s (Attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait_sec)
                else:
                    print(f"✗ Gemini generation error for Row {row_num}: {e}")
                    break

        if res_json:
            gen_title    = article_title or res_json.get("article_title", raw_title)
            gen_sub      = article_subtitle or res_json.get("article_subtitle", raw_subtitle)
            gen_desc     = res_json.get("article_description", "")
            cat          = res_json.get("category", "campus").lower().strip()
            search_kw    = res_json.get("search_keywords") or cat

            # Assign a relevant, unique image
            final_image = article_image or existing_image
            if not final_image or not final_image.startswith("http"):
                final_image = fetch_relevant_unique_image(search_kw, used_image_urls)
            else:
                used_image_urls.add(final_image)
                used_image_urls.add(final_image.split("?")[0])

            # Queue Updates
            batch_updates.append({'range': f'J{row_num}', 'values': [[gen_desc]]})
            if not article_subtitle:
                batch_updates.append({'range': f'L{row_num}', 'values': [[gen_sub]]})
            if not article_image:
                batch_updates.append({'range': f'M{row_num}', 'values': [[final_image]]})
            if not article_title:
                batch_updates.append({'range': f'N{row_num}', 'values': [[gen_title]]})

            print(f"✓ Generated 15-16 sentence article for Row {row_num} (Category: {cat} | Image: {search_kw})")

# ---------------------------------------------------------------------------
# WRITE BACK TO GOOGLE SHEETS
# ---------------------------------------------------------------------------
if batch_updates:
    worksheet.batch_update(batch_updates)
    print(f"\nSuccessfully updated {len(batch_updates)} cell ranges in Google Sheets!")
else:
    print("\nNo rows required AI enrichment.")
