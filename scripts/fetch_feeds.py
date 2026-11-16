#!/usr/bin/env python3
"""Fetch every feed in feeds.opml and write recent posts to items.json.

Runs daily in GitHub Actions. Keeps a rolling window of posts so the weekly
curation task always has the last few weeks to choose from, and writes a
feed_status.json so broken feeds are easy to spot.
"""
import calendar
import html
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import feedparser

ROOT = Path(__file__).resolve().parent.parent
OPML = ROOT / "feeds.opml"
ITEMS = ROOT / "items.json"
STATUS = ROOT / "feed_status.json"

WINDOW_DAYS = 28          # how far back to keep posts
SUMMARY_CHARS = 600       # enough for the curator to judge a post
USER_AGENT = "my-scholastic-book-fair/1.0 (+https://github.com/nickconnor52/my-scholastic-book-fair)"


def load_feeds():
    tree = ET.parse(OPML)
    feeds = []
    for node in tree.iter("outline"):
        url = node.get("xmlUrl")
        if url:
            feeds.append({"name": node.get("title") or node.get("text") or url, "url": url})
    return feeds


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def entry_time(entry):
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        value = entry.get(key)
        if value:
            return calendar.timegm(value)
    return None


def main():
    now = time.time()
    cutoff = now - WINDOW_DAYS * 86400
    existing = {}
    if ITEMS.exists():
        for item in json.loads(ITEMS.read_text()).get("items", []):
            existing[item["url"]] = item

    status = []
    for feed in load_feeds():
        parsed = feedparser.parse(feed["url"], agent=USER_AGENT)
        http = parsed.get("status")
        ok = bool(parsed.entries) and (http is None or http < 400)
        status.append({
            "name": feed["name"],
            "url": feed["url"],
            "ok": ok,
            "http_status": http,
            "entries": len(parsed.entries),
            "error": str(parsed.get("bozo_exception")) if not ok and parsed.get("bozo") else None,
        })
        for entry in parsed.entries:
            link = entry.get("link")
            ts = entry_time(entry)
            if not link or ts is None or ts < cutoff:
                continue
            summary = clean(entry.get("summary") or "")
            if not summary and entry.get("content"):
                summary = clean(entry["content"][0].get("value", ""))
            existing.setdefault(link, {
                "url": link,
                "title": clean(entry.get("title")) or link,
                "source": feed["name"],
                "author": clean(entry.get("author")) or None,
                "published": datetime.fromtimestamp(ts, timezone.utc).isoformat(),
                "first_seen": datetime.fromtimestamp(now, timezone.utc).isoformat(),
                "summary": summary[:SUMMARY_CHARS],
            })

    items = [i for i in existing.values()
             if datetime.fromisoformat(i["published"]).timestamp() >= cutoff]
    items.sort(key=lambda i: i["published"], reverse=True)

    stamp = datetime.fromtimestamp(now, timezone.utc).isoformat()
    ITEMS.write_text(json.dumps({"updated": stamp, "window_days": WINDOW_DAYS, "items": items},
                                indent=2, ensure_ascii=False) + "\n")
    STATUS.write_text(json.dumps({"updated": stamp, "feeds": status}, indent=2) + "\n")

    broken = [s["name"] for s in status if not s["ok"]]
    print(f"{len(items)} items from {len(status)} feeds; broken: {broken or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
