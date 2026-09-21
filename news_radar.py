import os
import json
import gspread
import feedparser

from datetime import datetime, timezone, timedelta

RSS_FEEDS = {
    "Inside Higher Ed": "https://www.insidehighered.com/rss.xml",
    "Higher Ed Dive": "https://www.highereddive.com/feeds/news/",
    "The PIE News": "https://thepienews.com/feed/",
}

cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
extracted_at = datetime.now(timezone.utc).isoformat()

recent_articles = []

for source, feed_url in RSS_FEEDS.items():

    feed = feedparser.parse(feed_url)

    print(f"{source}: {len(feed.entries)} entries")

    for article in feed.entries:

        if hasattr(article, "published_parsed"):
            published = datetime(
                *article.published_parsed[:6],
                tzinfo=timezone.utc
            )
        elif hasattr(article, "updated_parsed"):
            published = datetime(
                *article.updated_parsed[:6],
                tzinfo=timezone.utc
            )
        else:
            continue

        if published < cutoff:
            continue

        recent_articles.append([
            published.isoformat(),
            article.get("title", ""),
            article.get("description", ""),
            source,
            article.get("link", ""),
            extracted_at
        ])

recent_articles.sort(
    key=lambda x: x[0],
    reverse=True
)

print(f"Articles from last 24h: {len(recent_articles)}")

credentials = json.loads(
    os.environ["GOOGLE_SERVICE_ACCOUNT"]
)

gc = gspread.service_account_from_dict(credentials)

sheet = gc.open_by_key(
    "1E558JcLuLMyBqclmqrRhvlswMK9FS-NdJw_o3W1C7vI"
)

worksheet = sheet.worksheet("AI Test")

if recent_articles:
    worksheet.append_rows(
        recent_articles,
        value_input_option="RAW"
    )

print(f"Uploaded: {len(recent_articles)}")
