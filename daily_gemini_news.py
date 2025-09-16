import os
import feedparser
import requests
from newspaper import Article
from jinja2 import Template
import google.generativeai as genai
from datetime import datetime

# --- CONFIG ---
DATE_STR = datetime.now().strftime("%Y-%m-%d")
OUT_HTML_LATEST = "index.html"
OUT_HTML_ARCHIVE = f"news_{DATE_STR}.html"
OUT_HTML_LIST = "archive.html"
FEEDS = [
    "https://blog.unity.com/rss",
    "https://www.roadtovr.com/feed/",
    "https://www.uploadvr.com/feed/",
    "https://export.arxiv.org/rss/cs.CV",
]
MAX_PER_FEED = 5

# --- Gemini ---
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("Set GEMINI_API_KEY in env")
genai.configure(api_key=API_KEY)

def fetch_article_text(url):
    try:
        art = Article(url)
        art.download()
        art.parse()
        return art.text or ""
    except:
        try:
            return requests.get(url, timeout=10).text
        except:
            return ""

def summarize(title, url, snippet):
    prompt = (
        f"Summarize for Unity/AI/VR developers in 2-3 sentences. "
        f"Then add one bullet: 'Why it matters'.\n\n"
        f"Title: {title}\nURL: {url}\nContent:\n{snippet[:500]}"
    )
    model = genai.GenerativeModel("gemini-1.5-flash")
    return model.generate_content(prompt).text

def build_html(items, date):
    tpl = Template("""
    <html>
      <head><meta charset="utf-8"><title>Unity AI VR Daily News</title></head>
      <body>
        <h1>Unity AI VR Daily News — {{date}}</h1>
        {% for it in items %}
          <section style="margin-bottom:18px;">
            <h3><a href="{{it.url}}" target="_blank">{{it.title}}</a></h3>
            <div>{{it.summary|safe}}</div>
            <small>Source: {{it.source}}</small>
          </section>
        {% endfor %}
        <hr>
        <p><a href="archive.html">View Archive</a></p>
      </body>
    </html>
    """)
    return tpl.render(items=items, date=date)

def update_archive():
    # find all news_YYYY-MM-DD.html files
    archive_files = sorted(
        [f for f in os.listdir(".") if f.startswith("news_") and f.endswith(".html")],
        reverse=True
    )
    tpl = Template("""
    <html>
      <head><meta charset="utf-8"><title>Unity AI VR News Archive</title></head>
      <body>
        <h1>Unity AI VR News Archive</h1>
        <ul>
          {% for file in files %}
            <li><a href="{{file}}">{{file.replace('news_', '').replace('.html','')}}</a></li>
          {% endfor %}
        </ul>
        <p><a href="index.html">Back to Latest</a></p>
      </body>
    </html>
    """)
    html = tpl.render(files=archive_files)
    with open(OUT_HTML_LIST, "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ Archive updated")

def main():
    collected = []
    for feed in FEEDS:
        d = feedparser.parse(feed)
        for e in d.entries[:MAX_PER_FEED]:
            title = e.get("title", "No title")
            url = e.get("link")
            text = fetch_article_text(url)[:1000]
            summary = summarize(title, url, text)
            collected.append({"title": title, "url": url, "summary": summary, "source": feed})

    html = build_html(collected, DATE_STR)

    # Write latest and archive file
    for path in [OUT_HTML_LATEST, OUT_HTML_ARCHIVE]:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)

    # Update archive list
    update_archive()

    print(f"✅ Wrote {OUT_HTML_LATEST}, {OUT_HTML_ARCHIVE}, and updated archive.html")

if __name__ == "__main__":
    main()
