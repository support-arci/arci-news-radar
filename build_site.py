import os
import json
import re
import gspread
from datetime import datetime

# 1. Connect to Google Sheets
credentials = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
gc = gspread.service_account_from_dict(credentials)
worksheet = gc.open_by_key("1E558JcLuLMyBqclmqrRhvlswMK9FS-NdJw_o3W1C7vI").worksheet("AI Test")

records = worksheet.get("A2:N")
if not records:
    print("No records found to build static pages.")
    exit(0)

def slugify(text):
    text = str(text or "").lower()
    text = re.sub(r"['\"]", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "article"

articles = []
for idx, r in enumerate(records):
    pad = r + [""] * (14 - len(r))
    published   = pad[0].strip()
    raw_title   = pad[1].strip()
    raw_sub     = pad[2].strip()
    raw_desc    = pad[3].strip()
    source      = pad[4].strip()
    url         = pad[5].strip()
    image       = pad[12].strip() or pad[7].strip()
    desc        = pad[9].strip() or raw_desc
    status      = pad[10].strip() or "Live"
    subtitle    = pad[11].strip() or raw_sub
    title       = pad[13].strip() or raw_title

    if title and desc:
        slug = slugify(title)
        articles.append({
            "slug": slug,
            "title": title,
            "subtitle": subtitle,
            "description": desc,
            "source": source,
            "url": url,
            "image": image,
            "published": published,
            "status": status
        })

print(f"Building static pages for {len(articles)} articles in infinite archive...")

os.makedirs("article", exist_ok=True)

ARTICLE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{title} | The Higher Ed Times</title>
<meta name="description" content="{meta_desc}" />
<link rel="canonical" href="https://thehigheredtimes.com/#article/{slug}" />
<meta property="og:title" content="{title}" />
<meta property="og:description" content="{meta_desc}" />
<meta property="og:type" content="article" />
<meta property="og:url" content="https://thehigheredtimes.com/#article/{slug}" />
<meta property="og:image" content="{image}" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=Source+Sans+3:wght@400;500;600;700&display=swap" rel="stylesheet" />
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-9745764356791505" crossorigin="anonymous"></script>
<style>
  :root {{ --paper: #f4f6f8; --ink: #0e1525; --ink-soft: #2a3446; --muted: #5c6778; --line: #e2e6ee; --navy: #0b1f3a; --blue: #1d4ed8; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--paper); color: var(--ink); font-family: "Source Sans 3", sans-serif; }}
  .wrap {{ max-width: 860px; margin: 0 auto; padding: 0 24px; }}
  header {{ background: #fff; border-bottom: 1px solid var(--line); padding: 16px 0; }}
  header .wrap {{ display: flex; justify-content: space-between; align-items: center; }}
  header a.brand {{ font-family: "Source Serif 4", Georgia, serif; font-size: 24px; font-weight: 700; color: var(--ink); text-decoration: none; }}
  .article-back {{ display: inline-flex; align-items: center; gap: 6px; font-size: 13.5px; font-weight: 600; color: var(--blue); margin: 24px 0 16px; text-decoration: none; }}
  h1 {{ font-family: "Source Serif 4", Georgia, serif; font-size: clamp(2rem, 3.5vw, 2.5rem); line-height: 1.2; color: var(--navy); margin: 8px 0 12px; }}
  .dek {{ font-size: 1.2rem; line-height: 1.4; color: var(--muted); font-weight: 500; margin-bottom: 16px; }}
  .meta {{ font-size: 13px; font-weight: 600; color: var(--muted); margin-bottom: 24px; }}
  .hero-img {{ width: 100%; aspect-ratio: 16/9; object-fit: cover; border-radius: 8px; margin-bottom: 32px; background: var(--navy); }}
  .article-body {{ font-family: "Source Serif 4", Georgia, serif; font-size: 19px; line-height: 1.75; color: var(--ink-soft); }}
  .article-body p {{ margin-bottom: 22px; }}
  .source-card {{ background: #fff; border: 1px solid var(--line); border-radius: 8px; padding: 18px; margin-top: 40px; font-size: 14px; }}
  footer {{ border-top: 1px solid var(--line); margin-top: 60px; padding: 40px 0; text-align: center; font-size: 13px; color: var(--muted); background: #fff; }}
  footer a {{ color: var(--ink); text-decoration: none; margin: 0 10px; font-weight: 600; }}
</style>
</head>
<body>
<header>
  <div class="wrap">
    <a href="/" class="brand">The Higher Ed Times</a>
    <nav>
      <a href="/" style="text-decoration:none; color:var(--blue); font-weight:600;">Latest Briefings</a>
    </nav>
  </div>
</header>
<main class="wrap">
  <a href="/#article/{slug}" class="article-back">&larr; Read inside dashboard</a>
  <article>
    <h1>{title}</h1>
    {subtitle_html}
    <div class="meta">{date} &bull; Published by The Higher Ed Times</div>
    {image_html}
    <div class="article-body">
      {paragraphs_html}
    </div>
    <div class="source-card">
      <strong>Editorial Sourcing & Methodology:</strong> This sector analysis was produced by The Higher Ed Times analyzing verified data, institutional statements, and initial reporting from <em>{source}</em>.
    </div>
  </article>
</main>
<footer>
  <div class="wrap">
    <p>&copy; 2026 The Higher Ed Times &bull; Higher Ed Insights</p>
    <p style="margin-top:10px;">
      <a href="/about.html">About</a> &bull; 
      <a href="/privacy.html">Privacy Policy</a> &bull; 
      <a href="/contact.html">Contact Us</a>
    </p>
  </div>
</footer>
</body>
</html>
"""

for art in articles:
    paras = art["description"].split("\n\n")
    p_html = "".join(f"<p>{p.strip()}</p>" for p in paras if p.strip())
    sub_html = f'<p class="dek">{art["subtitle"]}</p>' if art["subtitle"] else ""
    img_html = f'<img src="{art["image"]}" alt="{art["title"]}" class="hero-img" />' if art["image"] else ""
    meta_desc = art["subtitle"] or art["description"][:155].rsplit(" ", 1)[0] + "..."

    page_content = ARTICLE_TEMPLATE.format(
        title=art["title"],
        subtitle_html=sub_html,
        meta_desc=meta_desc.replace('"', '&quot;'),
        date=art["published"][:10] if art["published"] else "October 2026",
        source=art["source"] or "Higher Education Sector Dispatch",
        image=art["image"],
        image_html=img_html,
        paragraphs_html=p_html,
        slug=art["slug"]
    )
    with open(f"article/{art['slug']}.html", "w", encoding="utf-8") as f:
        f.write(page_content)

print(f"Generated {len(articles)} individual static article pages in /article/!")

# 5. Bake static content into index.html
if os.path.exists("index.html"):
    with open("index.html", "r", encoding="utf-8") as f:
        idx_content = f.read()

    crawlable_stories = []
    # Only put the top 15 in the index.html so it doesn't get too large
    for art in articles[:15]:
        crawlable_stories.append(f"""
        <article style="margin-bottom: 24px; border-bottom: 1px solid #e2e6ee; padding-bottom: 16px;">
          <h3 style="font-family:'Source Serif 4',serif; font-size:18px; margin:0 0 6px;">
            <a href="/article/{art['slug']}.html" style="text-decoration:none; color:#0b1f3a;">{art['title']}</a>
          </h3>
          <p style="font-size:13.5px; color:#5c6778; margin:0 0 8px;">{art['subtitle']}</p>
          <a href="/article/{art['slug']}.html" style="font-size:12.5px; font-weight:600; color:#1d4ed8; text-decoration:none;">Read full briefing &rarr;</a>
        </article>
        """)

    static_block = f"""
    <!-- STATIC PRE-RENDERED BRIEFS FOR SEARCH & ADSENSE CRAWLERS -->
    <noscript>
      <div class="wrap" style="padding: 24px 0;">
        <h2>Current Higher Education Briefings</h2>
        {''.join(crawlable_stories)}
      </div>
    </noscript>
    """

    if "STATIC PRE-RENDERED BRIEFS" not in idx_content:
        idx_content = idx_content.replace('<main id="home-view">', '<main id="home-view">\n' + static_block)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(idx_content)
    print("Updated index.html with crawlable noscript content.")
