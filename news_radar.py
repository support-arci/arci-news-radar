import os
import json
import gspread
import feedparser

from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta

RSS_FEEDS = {
    "Inside Higher Ed": "https://www.insidehighered.com/rss.xml",
    "Higher Ed Dive": "https://www.highereddive.com/feeds/news/",
    "The PIE News": "https://thepienews.com/feed/",
}

cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
extracted_at = datetime.now(timezone.utc).isoformat()

recent_articles = []


def clean_description(raw_html):
    """Convert RSS HTML description into clean readable text."""

    soup = BeautifulSoup(raw_html or "", "html.parser")

    # Remove images
    for tag in soup.find_all(["img", "picture", "figure"]):
        tag.decompose()

    # Remove links
    for tag in soup.find_all("a"):
        tag.replace_with(tag.get_text(" ", strip=True))

    text = soup.get_text(" ", strip=True)

    # Clean excessive whitespace
    text = " ".join(text.split())

    return text


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

        description = clean_description(
            article.get("description", "")
        )

        recent_articles.append([
            published.isoformat(),
            article.get("title", ""),
            description,
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

    worksheet.update(
        range_name=f"A1:F{len(recent_articles)}",
        values=recent_articles
    )

print(f"Uploaded: {len(recent_articles)}")
