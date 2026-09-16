import os
import requests
from datetime import datetime, timezone

API_KEY = os.environ["FINNHUB_API_KEY"]

url = "https://finnhub.io/api/v1/news"

params = {
    "category": "general",
    "token": API_KEY
}

response = requests.get(url, params=params, timeout=30)
response.raise_for_status()

articles = response.json()

print(f"Checked: {datetime.now(timezone.utc)}")
print(f"Articles received: {len(articles)}")

for article in articles:
    print("\n" + "=" * 80)
    print(article.get("headline"))
    print(article.get("source"))
    print(article.get("url"))
