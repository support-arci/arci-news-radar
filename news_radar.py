import os
import requests
from datetime import datetime, timezone

FINNHUB_API_KEY = os.environ["FINNHUB_API_KEY"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

FINNHUB_URL = "https://finnhub.io/api/v1/news"
SUPABASE_TABLE = f"{SUPABASE_URL}/rest/v1/news_articles"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

params = {
    "category": "general",
    "token": FINNHUB_API_KEY
}

response = requests.get(FINNHUB_URL, params=params, timeout=30)
response.raise_for_status()

articles = response.json()

new_articles = 0

for article in articles:

    article_id = str(article.get("id"))

    # Check if already stored
    check = requests.get(
        SUPABASE_TABLE,
        headers=headers,
        params={
            "article_id": f"eq.{article_id}",
            "select": "article_id"
        },
        timeout=30
    )

    if check.json():
        continue

    data = {
        "article_id": article_id,
        "headline": article.get("headline"),
        "source": article.get("source"),
        "url": article.get("url"),
        "published_at": datetime.fromtimestamp(
            article.get("datetime", 0),
            tz=timezone.utc
        ).isoformat()
    }

    insert = requests.post(
        SUPABASE_TABLE,
        headers=headers,
        json=data,
        timeout=30
    )

    insert.raise_for_status()

    new_articles += 1

print(f"Checked {len(articles)} articles")
print(f"New articles stored: {new_articles}")
