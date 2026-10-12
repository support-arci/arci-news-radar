import os
import json
import gspread
from google import genai
from google.genai import types

# ---------------------------------------------------------------------------
# LIGHTWEIGHT FREE-TO-USE HIGHER-ED IMAGE CDN DICTIONARY (Optimized WebP)
# ---------------------------------------------------------------------------
TOPIC_IMAGE_MAP = {
    "admissions": "https://images.unsplash.com/photo-1523240795612-9a054b0db644?q=80&w=800&auto=format&fit=crop", # Students / Enrollment
    "finance":    "https://images.unsplash.com/photo-1554224155-8d04cb21cd6c?q=80&w=800&auto=format&fit=crop", # Tuition / Economy / Debt
    "policy":     "https://images.unsplash.com/photo-1541829070764-84a7d30dd3f3?q=80&w=800&auto=format&fit=crop", # University Hall / Governance
    "mobility":   "https://images.unsplash.com/photo-1526778548025-fa2f459cd5c1?q=80&w=800&auto=format&fit=crop", # Global Map / International
    "tech":       "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?q=80&w=800&auto=format&fit=crop", # AI / Digital Learning
    "campus":     "https://images.unsplash.com/photo-1562774053-701939374585?q=80&w=800&auto=format&fit=crop"  # College Quad / Clocktower
}

DEFAULT_IMAGE_URL = "https://images.unsplash.com/photo-1523050854058-8df90110c9f1?q=80&w=800&auto=format&fit=crop"

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

# Fetch rows A2:N61
records = worksheet.get_values("A2:N61")
if not records:
    print("No articles found in sheet.")
    exit(0)

batch_updates = []

print(f"Loaded {len(records)} rows from Google Sheets. Checking for articles needing AI enrichment...")

# ---------------------------------------------------------------------------
# PROCESS ROWS
# ---------------------------------------------------------------------------
for i, row in enumerate(records):
    row_num = i + 2  # Row index in Google Sheet
    
    # Pad row to 14 columns if needed
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
        
        # Prepare context text for Gemini
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
3. Determine the primary topic category from ONE of these choices: 'admissions', 'finance', 'policy', 'mobility', 'tech', or 'campus'.
4. Produce a compelling 1-sentence subtitle (dek).
5. Produce a strong news headline.

OUTPUT FORMAT: Return ONLY a raw JSON object with these keys (no markdown formatting code blocks):
{{
  "article_title": "Executive Headline Here",
  "article_subtitle": "One sentence summary deck.",
  "article_description": "First paragraph sentence 1. Sentence 2... Second paragraph... (Total 15-16 sentences)",
  "category": "one of: admissions|finance|policy|mobility|tech|campus"
}}
"""

        try:
            # Generate content using Gemini 3.8 Flash
            response = client.models.generate_content(
                model='gemini-3.8-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3
                )
            )

            res_json = json.loads(response.text)
            
            gen_title    = article_title or res_json.get("article_title", raw_title)
            gen_sub      = article_subtitle or res_json.get("article_subtitle", raw_subtitle)
            gen_desc     = res_json.get("article_description", "")
            cat          = res_json.get("category", "campus").lower().strip()

            # Image Assignment
            final_image = article_image or existing_image
            if not final_image or not final_image.startswith("http"):
                final_image = TOPIC_IMAGE_MAP.get(cat, DEFAULT_IMAGE_URL)

            # Queue Updates
            batch_updates.append({'range': f'J{row_num}', 'values': [[gen_desc]]})
            if not article_subtitle:
                batch_updates.append({'range': f'L{row_num}', 'values': [[gen_sub]]})
            if not article_image:
                batch_updates.append({'range': f'M{row_num}', 'values': [[final_image]]})
            if not article_title:
                batch_updates.append({'range': f'N{row_num}', 'values': [[gen_title]]})

            print(f"✓ Generated 15-16 sentence article for Row {row_num} (Category: {cat})")

        except Exception as e:
            print(f"✗ Gemini generation error for Row {row_num}: {e}")

# ---------------------------------------------------------------------------
# WRITE BACK TO GOOGLE SHEETS
# ---------------------------------------------------------------------------
if batch_updates:
    worksheet.batch_update(batch_updates)
    print(f"\nSuccessfully updated {len(batch_updates)} cell ranges in Google Sheets!")
else:
    print("\nNo rows required AI enrichment.")
