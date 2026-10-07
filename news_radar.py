import os
import json
import requests
import gspread
import feedparser

from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta

# Expanded to 16 distinct, high-quality Higher Education feeds
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
    "University Business": "https://universitybusiness.com/feed/"
}

cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
extracted_at = datetime.now(timezone.utc).isoformat()
recent_articles = []

# Limits how many articles we fetch per source to ensure diversity
MAX_ARTICLES_PER_SOURCE = 7

def get_article_details(url):
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            },
            timeout=15
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # 1. Extract image URL
        image_url = ""
        og_image = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
        if og_image and og_image.get("content"):
            image_url = og_image["content"]
        else:
            twitter_image = soup.find("meta", property="twitter:image") or soup.find("meta", attrs={"name": "twitter:image"})
            if twitter_image and twitter_image.get("content"):
                image_url = twitter_image["content"]

        # 2. Find main article container (Intelligent Fallback Method)
        # Search for tags that typically contain the article body
        possible_containers = soup.find_all(['article', 'main']) + soup.find_all('div', class_=lambda c: c and any(sub in c.lower() for sub in ['article-body', 'post-content', 'entry-content', 'content-body', 'story-content', 'article-content']))
        
        article = None
        max_p_count = 0

        # Pick the container that has the highest number of paragraph tags
        for container in possible_containers:
            p_count = len(container.find_all("p"))
            if p_count > max_p_count:
                max_p_count = p_count
                article = container

        if not article:
            return "", "", image_url

        if not image_url:
            first_img = article.find("img")
            if first_img and first_img.get("src"):
                image_url = first_img["src"]

        # 3. Extract subtitle
        subtitle = ""
        subtitle_selectors = [".subtitle", ".sub-title", ".dek", ".article-subtitle", ".entry-subtitle", "[class*='subtitle']", "[class*='dek']"]
        for selector in subtitle_selectors:
            element = article.select_one(selector)
            if element:
                text = element.get_text(" ", strip=True)
                if text:
                    subtitle = text
                    break

        if not subtitle:
            og_desc = soup.find("meta", property="og:description")
            if og_desc and og_desc.get("content"): subtitle = og_desc["content"].strip()

        # 4. Remove unwanted elements
        for tag in article.find_all(["script", "style", "nav", "figure", "img", "aside", "form", "footer", "div.related"]):
            tag.decompose()

        # 5. Extract ENTIRE article content safely
        paragraphs = []
        for p in article.find_all("p"):
            text = p.get_text(" ", strip=True)
            if len(text) > 40:  # Filters out random social links or tags
                paragraphs.append(text)

        description_long = "\n\n".join(paragraphs)

        return description_long, subtitle, image_url

    except Exception as e:
        print(f"Could not extract {url}: {e}")
        return "", "", ""

# Fetch articles
for source, feed_url in RSS_FEEDS.items():
    try:
        feed = feedparser.parse(feed_url)
        print(f"{source}: {len(feed.entries)} entries found")
        
        added_for_source = 0

        for article in feed.entries:
            if added_for_source >= MAX_ARTICLES_PER_SOURCE:
                break # Move to the next news source once cap is hit

            if hasattr(article, "published_parsed") and article.published_parsed:
                published = datetime(*article.published_parsed[:6], tzinfo=timezone.utc)
            elif hasattr(article, "updated_parsed") and article.updated_parsed:
                published = datetime(*article.updated_parsed[:6], tzinfo=timezone.utc)
            else:
                continue

            if published < cutoff:
                continue

            link = article.get("link", "")
            description_long, subtitle, image_url = get_article_details(link)
            
            # Only count it if we actually retrieved a description
            if description_long:
                recent_articles.append([
                    published.isoformat(),
                    article.get("title", ""),
                    subtitle,
                    description_long,
                    source,
                    link,
                    extracted_at,
                    image_url,
                    "", # Col I empty
                    "", # Col J empty
                    "Live" # Col K (Status)
                ])
                added_for_source += 1

    except Exception as e:
        print(f"Failed parsing {source}: {e}")

recent_articles.sort(key=lambda x: x[0], reverse=True)
print(f"Total newly fetched articles: {len(recent_articles)}")

# Upload to Google Sheets
credentials = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
gc = gspread.service_account_from_dict(credentials)
worksheet = gc.open_by_key("1E558JcLuLMyBqclmqrRhvlswMK9FS-NdJw_o3W1C7vI").worksheet("AI Test")

if recent_articles:
    # 1. Fetch existing URLs to avoid duplicate uploads
    existing_records = worksheet.get_all_values()
    existing_urls = [row[5] for row in existing_records if len(row) > 5] # URL is in column F (index 5)
    
    new_unique_articles = [art for art in recent_articles if art[5] not in existing_urls]
    
    if new_unique_articles:
        # INSERT at row 2, pushing all old articles down
        worksheet.insert_rows(new_unique_articles, 2)
        print(f"Successfully inserted {len(new_unique_articles)} new articles at the top.")
    else:
        print("No new unique articles to upload.")
else:
    print("No recent articles found.")
