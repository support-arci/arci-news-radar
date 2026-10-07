import os
import json
import requests
import gspread
import feedparser

from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin

# 18 distinct, high-quality Higher Education RSS feeds
RSS_FEEDS = {
    "Inside Higher Ed": "https://www.insidehighered.com/rss.xml",
    "Higher Ed Dive": "https://www.highereddive.com/feeds/news/",
    "The PIE News": "https://thepienews.com/feed/",
    "Chronicle of Higher Education": "https://www.chronicle.com/rss",
    "University World News": "https://www.universityworldnews.com/rss.php",
    "EdSurge": "https://www.edsurge.com/articles_rss",
    "The Hechinger Report": "https://hechingerreport.org/category/higher-education/feed/",
    "Diverse: Issues In Higher Ed": "https://www.diverseeducation.com/feed/",
    "Times Higher Education": "https://www.timeshighereducation.com/rss/news.xml",
    "Campus Technology": "https://campustechnology.com/rss-feeds/all-articles.aspx",
    "Educause": "https://er.educause.edu/rss/er-rss",
    "Open Campus": "https://www.opencampusmedia.org/feed/",
    "Wonkhe": "https://wonkhe.com/feed/",
    "Forbes Education": "https://www.forbes.com/education/feed/",
    "Erudera News": "https://erudera.com/news/rss/",
    "University Business": "https://universitybusiness.com/feed/",
    "FE News (Higher Ed)": "https://www.fenews.co.uk/category/sector-news/higher-education/feed/",
    "Research Professional News": "https://www.researchprofessionalnews.com/feed/"
}

# Look back 72 hours
cutoff = datetime.now(timezone.utc) - timedelta(hours=72)
extracted_at = datetime.now(timezone.utc).isoformat()
recent_articles = []

# Limits articles per source
MAX_ARTICLES_PER_SOURCE = 5

def clean_text(raw_html):
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(" ", strip=True)

def extract_rss_image(entry):
    if "media_content" in entry and entry.media_content:
        for media in entry.media_content:
            if media.get("url"): return media["url"]
    if "media_thumbnail" in entry and entry.media_thumbnail:
        for media in entry.media_thumbnail:
            if media.get("url"): return media["url"]
    if "enclosures" in entry and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get("type", "").startswith("image") and enc.get("href"):
                return enc["href"]
    return ""

def get_article_details(url, entry, source_name):
    description_long = ""
    subtitle = ""
    image_url = extract_rss_image(entry)

    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            },
            timeout=12
        )
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            # 1. Image
            if not image_url or "fenews" in url.lower():
                og_image = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
                if og_image and og_image.get("content") and "default" not in og_image["content"].lower():
                    image_url = og_image["content"]

            if image_url:
                image_url = urljoin(url, image_url)

            # 2. Subtitle
            subtitle_selectors = [
                ".field--name-field-summary", ".field--name-field-subtitle",
                ".subtitle", ".sub-title", ".dek", ".article-subtitle", 
                ".entry-subtitle", ".teaser", "[class*='subtitle']", "[class*='dek']"
            ]
            for selector in subtitle_selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(" ", strip=True)
                    if text and len(text) > 15:
                        subtitle = text
                        break

            if not subtitle:
                og_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
                if og_desc and og_desc.get("content"):
                    subtitle = og_desc["content"].strip()

            # 3. Main Body
            possible_containers = (
                soup.find_all(['article', 'main']) + 
                soup.find_all('div', class_=lambda c: c and any(sub in str(c).lower() for sub in [
                    'article-body', 'post-content', 'entry-content', 'content-body', 
                    'story-content', 'field--name-body', 'pf-content', 'single-post-content', 'td-post-content'
                ]))
            )
            
            target_container = None
            max_p_count = 0
            for container in possible_containers:
                p_count = len(container.find_all("p"))
                if p_count > max_p_count:
                    max_p_count = p_count
                    target_container = container

            if not target_container:
                target_container = soup

            for tag in target_container.find_all(["script", "style", "nav", "figure", "aside", "form", "footer", "header", "div.related"]):
                tag.decompose()

            paragraphs = []
            for p in target_container.find_all("p"):
                text = p.get_text(" ", strip=True)
                if len(text) > 35 and not any(skip in text.lower() for skip in ["subscribe", "rights reserved", "cookie", "sign up"]):
                    paragraphs.append(text)

            description_long = "\n\n".join(paragraphs)

            if not image_url and target_container:
                first_img = target_container.find("img")
                if first_img and first_img.get("src"):
                    image_url = urljoin(url, first_img["src"])

    except Exception as e:
        print(f"Scrape notice for {url}: {e}")

    # Fallbacks
    if not subtitle or len(subtitle) < 10:
        rss_summary = clean_text(entry.get("summary", "") or entry.get("description", ""))
        if rss_summary:
            subtitle = rss_summary[:220].rsplit(' ', 1)[0] + "..." if len(rss_summary) > 220 else rss_summary

    if len(description_long) < 120:
        feed_body = ""
        if "content" in entry and entry.content:
            feed_body = clean_text(entry.content[0].value)
        if len(feed_body) < 120:
            feed_body = clean_text(entry.get("summary", "") or entry.get("description", ""))
        
        if feed_body:
            description_long = feed_body

    return description_long, subtitle, image_url


for source, feed_url in RSS_FEEDS.items():
    try:
        feed = feedparser.parse(feed_url)
        print(f"{source}: {len(feed.entries)} entries parsed")
        
        added_for_source = 0

        for article in feed.entries:
            if added_for_source >= MAX_ARTICLES_PER_SOURCE:
                break

            if hasattr(article, "published_parsed") and article.published_parsed:
                published = datetime(*article.published_parsed[:6], tzinfo=timezone.utc)
            elif hasattr(article, "updated_parsed") and article.updated_parsed:
                published = datetime(*article.updated_parsed[:6], tzinfo=timezone.utc)
            else:
                published = datetime.now(timezone.utc)

            if published < cutoff:
                continue

            link = article.get("link", "")
            description_long, subtitle, image_url = get_article_details(link, article, source)
            raw_title = article.get("title", "").strip()

            if description_long and raw_title:
                # MAP STRICTLY TO A-N (14 Columns)
                row_data = [
                    published.isoformat(),     # A: published
                    raw_title,                 # B: title (legacy)
                    subtitle.strip(),          # C: subtitle (legacy)
                    description_long.strip(),  # D: description_long (legacy)
                    source,                    # E: source
                    link,                      # F: url
                    extracted_at,              # G: extracted_at
                    image_url,                 # H: image (legacy)
                    "",                        # I: hero
                    description_long.strip(),  # J: article_description
                    "Live",                    # K: Live/Archived
                    subtitle.strip(),          # L: article_subtitle
                    image_url,                 # M: article_image
                    raw_title                  # N: article_title
                ]
                recent_articles.append(row_data)
                added_for_source += 1

    except Exception as e:
        print(f"Failed parsing feed {source}: {e}")

recent_articles.sort(key=lambda x: x[0], reverse=True)
print(f"Total newly gathered articles across all sources: {len(recent_articles)}")

# Upload to Google Sheets
credentials = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
gc = gspread.service_account_from_dict(credentials)
worksheet = gc.open_by_key("1E558JcLuLMyBqclmqrRhvlswMK9FS-NdJw_o3W1C7vI").worksheet("AI Test")

if recent_articles:
    existing_records = worksheet.get_all_values()
    existing_urls = [row[5] for row in existing_records if len(row) > 5] # Column F
    
    new_unique_articles = [art for art in recent_articles if art[5] not in existing_urls]
    
    if new_unique_articles:
        worksheet.insert_rows(new_unique_articles, 2)
        print(f"Successfully inserted {len(new_unique_articles)} new unique articles at the top.")
    else:
        print("No new unique articles to upload.")
else:
    print("No recent articles found in 72h window.")
