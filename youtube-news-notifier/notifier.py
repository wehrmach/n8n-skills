#!/usr/bin/env python3
"""
YouTube News Notifier
Monitors YouTube for new videos matching specified keywords and sends email notifications.

Conceived by Romuald Czlonkowski - www.aiadvisors.pl/en
"""

import json
import os
import sys
import smtplib
import time
import signal
import logging
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
SEEN_VIDEOS_PATH = BASE_DIR / "seen_videos.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def load_seen_videos():
    if SEEN_VIDEOS_PATH.exists():
        with open(SEEN_VIDEOS_PATH, "r") as f:
            return json.load(f)
    return {}


def save_seen_videos(seen):
    with open(SEEN_VIDEOS_PATH, "w") as f:
        json.dump(seen, f, indent=2)


def search_youtube(api_key, keyword, max_results, published_after_hours, language):
    """Search YouTube for videos matching a keyword."""
    youtube = build("youtube", "v3", developerKey=api_key)

    after = datetime.now(timezone.utc) - timedelta(hours=published_after_hours)
    published_after = after.strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        request = youtube.search().list(
            q=keyword,
            part="snippet",
            type="video",
            order="date",
            maxResults=max_results,
            publishedAfter=published_after,
            relevanceLanguage=language,
        )
        response = request.execute()
    except HttpError as e:
        log.error("YouTube API error for keyword '%s': %s", keyword, e)
        return []

    videos = []
    for item in response.get("items", []):
        video = {
            "id": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "channel": item["snippet"]["channelTitle"],
            "published": item["snippet"]["publishedAt"],
            "description": item["snippet"].get("description", ""),
            "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
            "thumbnail": item["snippet"]["thumbnails"].get("high", {}).get("url", ""),
            "keyword": keyword,
        }
        videos.append(video)

    return videos


def build_email_html(new_videos):
    """Build an HTML email body from a list of new videos."""
    grouped = {}
    for v in new_videos:
        grouped.setdefault(v["keyword"], []).append(v)

    html_parts = [
        """
        <html><body style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto;">
        <h1 style="color: #cc0000; border-bottom: 2px solid #cc0000; padding-bottom: 10px;">
            YouTube News Alert
        </h1>
        <p style="color: #666;">Found <strong>{count}</strong> new video(s)</p>
        """.format(count=len(new_videos))
    ]

    for keyword, videos in grouped.items():
        html_parts.append(
            '<h2 style="color: #333; margin-top: 25px;">'
            'Keyword: <span style="color: #cc0000;">{keyword}</span> '
            '({count})</h2>'.format(keyword=keyword, count=len(videos))
        )

        for v in videos:
            html_parts.append(
                """
                <div style="border: 1px solid #ddd; border-radius: 8px; padding: 15px;
                            margin-bottom: 15px; background: #fafafa;">
                    <table><tr>
                        <td style="vertical-align: top; padding-right: 15px;">
                            <a href="{url}">
                                <img src="{thumbnail}" width="200"
                                     style="border-radius: 4px;" alt="thumbnail">
                            </a>
                        </td>
                        <td style="vertical-align: top;">
                            <a href="{url}" style="color: #1a0dab; font-size: 16px;
                               font-weight: bold; text-decoration: none;">
                                {title}
                            </a>
                            <p style="color: #666; margin: 5px 0;">
                                <strong>{channel}</strong> &middot; {published}
                            </p>
                            <p style="color: #444; font-size: 13px;">{description}</p>
                        </td>
                    </tr></table>
                </div>
                """.format(
                    url=v["url"],
                    thumbnail=v["thumbnail"],
                    title=v["title"],
                    channel=v["channel"],
                    published=v["published"][:10],
                    description=v["description"][:200] + ("..." if len(v["description"]) > 200 else ""),
                )
            )

    html_parts.append(
        '<hr style="margin-top: 30px;"><p style="color: #999; font-size: 11px;">'
        "Sent by YouTube News Notifier | {time}</p></body></html>".format(
            time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )

    return "".join(html_parts)


def send_email(config, new_videos):
    """Send email notification with new videos."""
    email_cfg = config["email"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "YouTube Alert: {count} new video(s) for [{keywords}]".format(
        count=len(new_videos),
        keywords=", ".join(set(v["keyword"] for v in new_videos)),
    )
    msg["From"] = email_cfg["sender_email"]
    msg["To"] = email_cfg["recipient_email"]

    html = build_email_html(new_videos)
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(email_cfg["smtp_server"], email_cfg["smtp_port"]) as server:
            server.starttls()
            server.login(email_cfg["sender_email"], email_cfg["sender_password"])
            server.send_message(msg)
        log.info("Email sent to %s with %d video(s)", email_cfg["recipient_email"], len(new_videos))
    except Exception as e:
        log.error("Failed to send email: %s", e)


def check_new_videos(config):
    """Check for new videos across all keywords and send notification if any found."""
    seen = load_seen_videos()
    all_new = []

    for keyword in config["keywords"]:
        log.info("Searching for keyword: '%s'", keyword)
        videos = search_youtube(
            api_key=config["youtube_api_key"],
            keyword=keyword,
            max_results=config.get("max_results_per_keyword", 5),
            published_after_hours=config.get("published_after_hours", 24),
            language=config.get("language", "en"),
        )

        for video in videos:
            if video["id"] not in seen:
                all_new.append(video)
                seen[video["id"]] = {
                    "title": video["title"],
                    "keyword": video["keyword"],
                    "found_at": datetime.now(timezone.utc).isoformat(),
                }

    if all_new:
        log.info("Found %d new video(s), sending email...", len(all_new))
        send_email(config, all_new)
        save_seen_videos(seen)
    else:
        log.info("No new videos found.")

    # Prune entries older than 7 days to keep file small
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    pruned = {k: v for k, v in seen.items() if v.get("found_at", "") > cutoff}
    if len(pruned) < len(seen):
        save_seen_videos(pruned)

    return len(all_new)


def run_once(config):
    """Run a single check."""
    log.info("Running single check...")
    count = check_new_videos(config)
    log.info("Done. Found %d new video(s).", count)


def run_loop(config):
    """Run continuously with interval from config."""
    interval = config.get("check_interval_minutes", 30)
    log.info("Starting continuous mode (every %d min). Ctrl+C to stop.", interval)

    stop = False

    def handler(sig, frame):
        nonlocal stop
        stop = True
        log.info("Shutting down...")

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    while not stop:
        try:
            config = load_config()  # Reload config each cycle to pick up keyword changes
            check_new_videos(config)
        except Exception as e:
            log.error("Error during check: %s", e)

        log.info("Next check in %d minutes...", interval)
        for _ in range(interval * 60):
            if stop:
                break
            time.sleep(1)


def main():
    if not CONFIG_PATH.exists():
        log.error("config.json not found at %s", CONFIG_PATH)
        sys.exit(1)

    config = load_config()

    if config["youtube_api_key"] == "YOUR_YOUTUBE_API_KEY":
        log.error("Please set your YouTube API key in config.json")
        sys.exit(1)

    if config["email"]["sender_password"] == "YOUR_APP_PASSWORD":
        log.error("Please set your Gmail App Password in config.json")
        sys.exit(1)

    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        run_once(config)
    else:
        run_loop(config)


if __name__ == "__main__":
    main()
