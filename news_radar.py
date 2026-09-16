import os
import requests
import gspread
from datetime import datetime, timezone, timedelta

# ----------------------
# 1️⃣ Finnhub
# ----------------------

FINNHUB_API_KEY = os.environ["FINNHUB_API_KEY"]

FINNHUB_URL = "https://finnhub.io/api/v1/news"

now = datetime.now(timezone.utc)
cutoff = now - timedelta(hours=24)

params = {
    "category": "general",
    "token": FINNHUB_API_KEY
}

response = requests.get(
    FINNHUB_URL,
    params=params,
    timeout=30
)

response.raise_for_status()

articles = response.json()

# ----------------------
# 2️⃣ Filter last 24h
# ----------------------

recent_articles = []

for article in articles:

    published = datetime.fromtimestamp(
        article.get("datetime", 0),
        tz=timezone.utc
    )

    if published >= cutoff:

        recent_articles.append([
            str(article.get("id")),
            article.get("headline"),
            article.get("source"),
            article.get("url"),
            published.isoformat()
        ])

# Newest first
recent_articles.sort(
    key=lambda x: x[4],
    reverse=True
)

print(f"Finnhub returned: {len(articles)}")
print(f"Last 24h: {len(recent_articles)}")

# ----------------------
# 3️⃣ Google Sheets
# ----------------------

import json

credentials = json.loads(
    os.environ["GOOGLE_SERVICE_ACCOUNT"]
)

gc = gspread.service_account_from_dict(credentials)

sheet = gc.open_by_key(
    "1E558JcLuLMyBqclmqrRhvlswMK9FS-NdJw_o3W1C7vI"
)

worksheet = sheet.worksheet("AI Test")

# ----------------------
# 4️⃣ Upload
# ----------------------

if recent_articles:

    worksheet.append_rows(
        recent_articles,
        value_input_option="RAW"
    )

print(f"Uploaded: {len(recent_articles)}")
