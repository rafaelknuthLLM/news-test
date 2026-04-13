#!/usr/bin/env python3
"""
AI-Cake News Aggregator -- Layer 1 (FETCH)
Pulls structured data from RSS/Atom feeds. No web search. No scraping.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import mktime

import feedparser

# --- Feed Registry -----------------------------------------------------------

FEEDS = [
    # Direct RSS feeds
    {"source": "NVIDIA Newsroom", "url": "https://nvidianews.nvidia.com/rss.xml", "category": "rss"},
    {"source": "OpenAI News", "url": "https://openai.com/news/rss.xml", "category": "rss"},
    {"source": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml", "category": "rss"},
    {"source": "arXiv cs.AI", "url": "http://arxiv.org/rss/cs.AI", "category": "rss"},
    # GitHub releases Atom feeds (bare .atom is dead, /releases.atom works)
    {"source": "anthropics/claude-code", "url": "https://github.com/anthropics/claude-code/releases.atom", "category": "github"},
    {"source": "anthropics/anthropic-sdk-python", "url": "https://github.com/anthropics/anthropic-sdk-python/releases.atom", "category": "github"},
    {"source": "anthropics/courses", "url": "https://github.com/anthropics/courses/releases.atom", "category": "github"},
    {"source": "openai/openai-python", "url": "https://github.com/openai/openai-python/releases.atom", "category": "github"},
    {"source": "huggingface/transformers", "url": "https://github.com/huggingface/transformers/releases.atom", "category": "github"},
    {"source": "NVIDIA/TensorRT", "url": "https://github.com/NVIDIA/TensorRT/releases.atom", "category": "github"},
]

USER_AGENT = "AI-Cake-Fetcher/1.0 (+https://github.com/rafaelknuthLLM/news-test)"

# --- Helpers -----------------------------------------------------------------


def parse_date(entry):
    """Extract and normalize date from a feed entry to ISO 8601."""
    for field in ("published_parsed", "updated_parsed"):
        parsed = entry.get(field)
        if parsed:
            try:
                return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc).isoformat()
            except (ValueError, OverflowError):
                continue
    for field in ("published", "updated"):
        raw = entry.get(field)
        if raw:
            return raw
    return None


def clean_summary(summary):
    """Strip HTML tags and collapse whitespace."""
    if not summary:
        return None
    text = re.sub(r"<[^>]+>", "", summary)
    text = re.sub(r"\s+", " ", text).strip()
    return text if text else None


def fetch_feed(feed_info):
    """Fetch and parse a single feed. Returns (items, error_msg)."""
    source = feed_info["source"]
    url = feed_info["url"]

    try:
        result = feedparser.parse(url, agent=USER_AGENT)
    except Exception as e:
        return [], f"{source}: exception during fetch -- {e}"

    if result.bozo and not result.entries:
        err = result.get("bozo_exception", "unknown error")
        return [], f"{source}: feed error -- {err}"

    items = []
    for entry in result.entries:
        items.append({
            "source": source,
            "category": feed_info["category"],
            "title": entry.get("title", "").strip() or None,
            "published": parse_date(entry),
            "summary": clean_summary(entry.get("summary", "")),
            "link": entry.get("link", "").strip() or None,
        })

    return items, None


def deduplicate(items):
    """Remove duplicate items by link URL."""
    seen = set()
    unique = []
    for item in items:
        link = item.get("link")
        if link and link in seen:
            continue
        if link:
            seen.add(link)
        unique.append(item)
    return unique


# --- Main --------------------------------------------------------------------


def main():
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d_%H%M")

    all_items = []
    succeeded = []
    failed = []

    for feed_info in FEEDS:
        items, error = fetch_feed(feed_info)
        if error:
            failed.append(error)
            print(f"  FAIL  {feed_info['source']}: {error}", file=sys.stderr)
        else:
            succeeded.append(feed_info["source"])
            print(f"  OK    {feed_info['source']}: {len(items)} items")
        all_items.extend(items)

    all_items = deduplicate(all_items)

    output = {
        "meta": {
            "generated_at": now.isoformat(),
            "feeds_succeeded": succeeded,
            "feeds_failed": failed,
            "total_items": len(all_items),
            "total_feeds": len(FEEDS),
        },
        "items": all_items,
    }

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f"ai_cake_feed_{timestamp}.json"
    output_file.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n  Done: {len(all_items)} items from {len(succeeded)}/{len(FEEDS)} feeds")
    print(f"  Output: {output_file}")

    if failed:
        print(f"  Failed feeds: {len(failed)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
