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

# Get latest general news
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

# Get article IDs already stored in Supabase
existing_response = requests.get(
    SUPABASE_TABLE,
    headers=headers,
    params={
        "select": "article_id",
        "limit": 1000
    },
    timeout=30
)

existing_response.raise_for_status()

existing_ids = {
    row["article_id"]
    for row in existing_response.json()
}

new_articles = []

for article in articles:

    article_id = str(article.get("id"))

    if article_id in existing_ids:
        continue

    new_articles.append({
        "article_id": article_id,
        "headline": article.get("headline"),
        "source": article.get("source"),
        "url": article.get("url"),
        "published_at": datetime.fromtimestamp(
            article.get("datetime", 0),
            tz=timezone.utc
        ).isoformat()
    })

# Insert all new articles in one request
if new_articles:

    insert = requests.post(
        SUPABASE_TABLE,
        headers=headers,
        json=new_articles,
        timeout=30
    )

    insert.raise_for_status()

print(f"Checked {len(articles)} articles")
print(f"New articles stored: {len(new_articles)}")
