#!/usr/bin/env python3
"""
Anthropic News Notifier
Scrapes anthropic.com/news and /research for recent articles,
extracts and summarizes content, and sends a digest email.
Zero external dependencies - uses only Python standard library.

Conceived by Romuald Czlonkowski - www.aiadvisors.pl/en
"""

import json
import re
import sys
import smtplib
import logging
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from html.parser import HTMLParser
from pathlib import Path

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AnthropicNewsNotifier/1.0)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

# Month name to number mapping
MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def fetch_page(url):
    """Fetch a web page and return its HTML content."""
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        log.error("HTTP %d fetching %s", e.code, url)
        return ""
    except urllib.error.URLError as e:
        log.error("Network error fetching %s: %s", url, e.reason)
        return ""


def parse_date(date_str):
    """Parse date strings like 'Feb 5, 2026' or 'December 18, 2025'."""
    date_str = date_str.strip()
    # Try common formats
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d", "%b %d %Y", "%B %d %Y"):
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    # Try manual parse for abbreviated months with periods (e.g. "Feb. 5, 2026")
    cleaned = date_str.replace(".", "")
    for fmt in ("%b %d, %Y", "%b %d %Y"):
        try:
            return datetime.strptime(cleaned, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


class LinkExtractor(HTMLParser):
    """Extract article links, titles, and dates from Anthropic listing pages."""

    def __init__(self):
        super().__init__()
        self.articles = []
        self._in_link = False
        self._current_href = None
        self._texts = []
        self._all_text_segments = []
        self._capture = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "a":
            href = attrs_dict.get("href", "")
            if href.startswith("/news/") or href.startswith("/research/"):
                self._in_link = True
                self._current_href = href
                self._texts = []

    def handle_endtag(self, tag):
        if tag == "a" and self._in_link:
            text = " ".join(self._texts).strip()
            if text and self._current_href:
                self.articles.append({
                    "href": self._current_href,
                    "title": text,
                })
            self._in_link = False
            self._current_href = None

    def handle_data(self, data):
        if self._in_link:
            self._texts.append(data.strip())
        self._all_text_segments.append(data)


class ArticleExtractor(HTMLParser):
    """Extract main content from an Anthropic article page."""

    def __init__(self):
        super().__init__()
        self.texts = []
        self._skip_tags = {"script", "style", "nav", "footer", "header", "noscript"}
        self._skip_depth = 0
        self._tag_stack = []

    def handle_starttag(self, tag, attrs):
        self._tag_stack.append(tag)
        if tag in self._skip_tags:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if self._tag_stack and self._tag_stack[-1] == tag:
            self._tag_stack.pop()
        if tag in self._skip_tags and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            text = data.strip()
            if text:
                self.texts.append(text)


def extract_articles_from_listing(html, base_url):
    """Extract article entries from a listing page."""
    parser = LinkExtractor()
    parser.feed(html)

    # Deduplicate by href
    seen_hrefs = set()
    unique = []
    for art in parser.articles:
        if art["href"] not in seen_hrefs:
            seen_hrefs.add(art["href"])
            unique.append(art)

    # Try to find dates in the full page text
    full_text = " ".join(parser._all_text_segments)

    # Find all date patterns in the page
    date_pattern = re.compile(
        r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})',
        re.IGNORECASE
    )
    found_dates = date_pattern.findall(full_text)

    # Build full URLs
    base = base_url.rstrip("/")
    origin = "/".join(base.split("/")[:3])  # https://www.anthropic.com

    for art in unique:
        if art["href"].startswith("/"):
            art["url"] = origin + art["href"]
        else:
            art["url"] = art["href"]
        art["date"] = None

    # Try to match dates to articles by proximity in the HTML
    # Assign dates found near article links
    for date_str in found_dates:
        dt = parse_date(date_str)
        if dt is None:
            continue
        # Find the article that appears closest after this date in the text
        date_pos = full_text.find(date_str)
        if date_pos < 0:
            continue
        for art in unique:
            if art["date"] is not None:
                continue
            title_pos = full_text.find(art["title"][:30])
            if title_pos >= 0 and abs(title_pos - date_pos) < 500:
                art["date"] = dt
                break

    return unique


def fetch_article_content(url, max_chars):
    """Fetch and extract text content from an article page."""
    html = fetch_page(url)
    if not html:
        return ""

    parser = ArticleExtractor()
    parser.feed(html)

    # Join all text, clean up whitespace
    full_text = "\n".join(parser.texts)
    # Remove excessive whitespace
    full_text = re.sub(r'\n{3,}', '\n\n', full_text)
    full_text = re.sub(r' {2,}', ' ', full_text)

    return full_text[:max_chars]


def summarize_text(text, max_sentences=5):
    """Extract a simple summary: first N meaningful sentences."""
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)

    # Filter out very short lines (navigation, labels, etc.)
    meaningful = [s.strip() for s in sentences if len(s.strip()) > 40]

    summary = " ".join(meaningful[:max_sentences])
    if len(meaningful) > max_sentences:
        summary += " ..."

    return summary if summary else text[:500]


def build_email_html(articles):
    """Build an HTML digest email."""
    html_parts = [
        """
        <html><body style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 700px;
                          margin: 0 auto; padding: 20px; color: #333;">
        <h1 style="color: #d97706; border-bottom: 3px solid #d97706; padding-bottom: 12px;">
            Anthropic Weekly Digest
        </h1>
        <p style="color: #666; font-size: 14px;">
            {count} article(s) from the past week &middot; {date}
        </p>
        """.format(
            count=len(articles),
            date=datetime.now().strftime("%B %d, %Y"),
        )
    ]

    for i, art in enumerate(articles, 1):
        date_str = art["date"].strftime("%b %d, %Y") if art.get("date") else "Recent"
        html_parts.append(
            """
            <div style="border-left: 4px solid #d97706; padding: 15px 20px;
                        margin: 20px 0; background: #fffbeb; border-radius: 0 8px 8px 0;">
                <h2 style="margin: 0 0 8px 0; font-size: 18px;">
                    <a href="{url}" style="color: #92400e; text-decoration: none;">
                        {num}. {title}
                    </a>
                </h2>
                <p style="color: #b45309; font-size: 12px; margin: 0 0 10px 0;">
                    {date} &middot; <a href="{url}" style="color: #d97706;">Read full article</a>
                </p>
                <p style="color: #444; font-size: 14px; line-height: 1.6; margin: 0;">
                    {summary}
                </p>
            </div>
            """.format(
                url=art["url"],
                title=art["title"],
                date=date_str,
                summary=art.get("summary", ""),
                num=i,
            )
        )

    html_parts.append(
        """
        <hr style="margin-top: 30px; border: 1px solid #e5e7eb;">
        <p style="color: #9ca3af; font-size: 11px; text-align: center;">
            Anthropic News Notifier &middot; {time}<br>
            Sources: anthropic.com/news, anthropic.com/research
        </p>
        </body></html>
        """.format(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )

    return "".join(html_parts)


def send_email(config, articles):
    """Send digest email."""
    email_cfg = config["email"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Anthropic Weekly: {count} new article(s) - {date}".format(
        count=len(articles),
        date=datetime.now().strftime("%b %d"),
    )
    msg["From"] = email_cfg["sender_email"]
    msg["To"] = email_cfg["recipient_email"]

    html = build_email_html(articles)
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(email_cfg["smtp_server"], email_cfg["smtp_port"]) as server:
            server.starttls()
            server.login(email_cfg["sender_email"], email_cfg["sender_password"])
            server.send_message(msg)
        log.info("Digest sent to %s (%d articles)", email_cfg["recipient_email"], len(articles))
        return True
    except Exception as e:
        log.error("Failed to send email: %s", e)
        return False


def run(config):
    """Main: scrape, filter, summarize, email."""
    lookback = config.get("lookback_days", 7)
    max_chars = config.get("max_article_chars", 5000)
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback)
    all_articles = []

    for source_url in config["sources"]:
        log.info("Fetching listing: %s", source_url)
        html = fetch_page(source_url)
        if not html:
            continue

        articles = extract_articles_from_listing(html, source_url)
        log.info("  Found %d article links", len(articles))

        for art in articles:
            # Filter: only articles within lookback period
            if art["date"] and art["date"] < cutoff:
                continue
            all_articles.append(art)

    if not all_articles:
        log.info("No articles from the past %d days found.", lookback)
        return 0

    # Deduplicate across sources
    seen_urls = set()
    unique = []
    for art in all_articles:
        if art["url"] not in seen_urls:
            seen_urls.add(art["url"])
            unique.append(art)

    # Sort by date (newest first)
    unique.sort(key=lambda a: a.get("date") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    log.info("Processing %d recent article(s)...", len(unique))

    # Fetch and summarize each article
    for art in unique:
        log.info("  Fetching: %s", art["title"])
        content = fetch_article_content(art["url"], max_chars)
        art["summary"] = summarize_text(content)

    # Send email
    if config["email"]["sender_password"] == "YOUR_APP_PASSWORD":
        log.warning("Gmail password not set - printing digest to console instead.")
        print("\n" + "=" * 60)
        print("ANTHROPIC WEEKLY DIGEST")
        print("=" * 60)
        for i, art in enumerate(unique, 1):
            date_str = art["date"].strftime("%b %d, %Y") if art.get("date") else "Recent"
            print(f"\n--- [{i}] {art['title']} ({date_str}) ---")
            print(f"URL: {art['url']}")
            print(f"Summary: {art['summary']}\n")
        print("=" * 60)
    else:
        send_email(config, unique)

    return len(unique)


def main():
    if not CONFIG_PATH.exists():
        log.error("config.json not found at %s", CONFIG_PATH)
        sys.exit(1)

    config = load_config()

    log.info("Anthropic News Notifier starting...")
    count = run(config)
    log.info("Done. Processed %d article(s).", count)


if __name__ == "__main__":
    main()
