import os
import json
import requests
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


def get_article_description(url):

    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            },
            timeout=15
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        article = soup.find("article")

        if not article:
            article = soup.find(
                class_=lambda x: x and "article" in str(x).lower()
            )

        if not article:
            return ""

        # Remove unwanted elements
        for tag in article.find_all([
            "script",
            "style",
            "nav",
            "figure",
            "img",
            "aside"
        ]):
            tag.decompose()

        paragraphs = []

        for p in article.find_all("p"):

            text = p.get_text(" ", strip=True)

            if len(text) > 40:
                paragraphs.append(text)

        # First 5 useful paragraphs
        description = " ".join(paragraphs[:5])

        return description

    except Exception as e:

        print(f"Could not extract {url}: {e}")

        return ""


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

        description = get_article_description(
            article.get("link", "")
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
