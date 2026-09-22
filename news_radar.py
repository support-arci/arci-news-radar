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


def get_article_details(url):
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

        # 1. Extract image URL (Check Open Graph & Twitter meta tags first)
        image_url = ""
        og_image = (
            soup.find("meta", property="og:image") 
            or soup.find("meta", attrs={"name": "og:image"})
        )
        if og_image and og_image.get("content"):
            image_url = og_image["content"]
        else:
            twitter_image = (
                soup.find("meta", property="twitter:image") 
                or soup.find("meta", attrs={"name": "twitter:image"})
            )
            if twitter_image and twitter_image.get("content"):
                image_url = twitter_image["content"]

        # 2. Find main article container
        article = soup.find("article")

        if not article:
            article = soup.find(
                class_=lambda x: x and "article" in str(x).lower()
            )

        if not article:
            return "", image_url

        # Fallback image extraction from the article body if meta tags weren't present
        if not image_url:
            first_img = article.find("img")
            if first_img and first_img.get("src"):
                image_url = first_img["src"]

        # Remove unwanted elements for paragraph extraction
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

        return description, image_url

    except Exception as e:
        print(f"Could not extract {url}: {e}")
        return "", ""


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

        description, image_url = get_article_details(
            article.get("link", "")
        )

        recent_articles.append([
            published.isoformat(),
            article.get("title", ""),
            description,
            source,
            article.get("link", ""),
            extracted_at,
            image_url  # Column G
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
    # Starts at row 2 (A2) to leave the header row untouched
    end_row = len(recent_articles) + 1
    worksheet.update(
        range_name=f"A2:G{end_row}",
        values=recent_articles
    )

print(f"Uploaded: {len(recent_articles)}")
