import os
import requests
from datetime import datetime, timezone, timedelta

FINNHUB_API_KEY = os.environ["FINNHUB_API_KEY"]

FINNHUB_URL = "https://finnhub.io/api/v1/news"

# Last 24 hours
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

# Keep only last 24 hours
recent_articles = []

for article in articles:

    published = datetime.fromtimestamp(
        article.get("datetime", 0),
        tz=timezone.utc
    )

    if published >= cutoff:
        recent_articles.append({
            "article_id": str(article.get("id")),
            "headline": article.get("headline"),
            "source": article.get("source"),
            "url": article.get("url"),
            "published_at": published.isoformat()
        })

# Sort newest first
recent_articles.sort(
    key=lambda x: x["published_at"],
    reverse=True
)

print(f"Finnhub returned: {len(articles)}")
print(f"Articles from last 24h: {len(recent_articles)}")

for article in recent_articles[:10]:
    print(
        article["published_at"],
        "|",
        article["source"],
        "|",
        article["headline"]
    )
