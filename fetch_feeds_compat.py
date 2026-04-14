#!/usr/bin/env python3
"""
AI-Cake News Aggregator -- Layer 1 (FETCH) -- Python 3.11 compatible version
Uses requests + ElementTree instead of feedparser (avoids sgmllib dependency).
"""

import json
import re
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

import requests

FEEDS = [
    {"source": "arXiv cs.AI", "url": "http://arxiv.org/rss/cs.AI", "category": "research"},
    {"source": "anthropics/claude-code", "url": "https://github.com/anthropics/claude-code/releases.atom", "category": "github"},
    {"source": "anthropics/anthropic-sdk-python", "url": "https://github.com/anthropics/anthropic-sdk-python/releases.atom", "category": "github"},
    {"source": "openai/openai-python", "url": "https://github.com/openai/openai-python/releases.atom", "category": "github"},
    {"source": "huggingface/transformers", "url": "https://github.com/huggingface/transformers/releases.atom", "category": "github"},
    {"source": "NVIDIA/TensorRT", "url": "https://github.com/NVIDIA/TensorRT/releases.atom", "category": "github"},
]

USER_AGENT = "AI-Cake-Fetcher/1.0 (+https://github.com/rafaelknuthLLM/news-test)"

NS = {
    'atom': 'http://www.w3.org/2005/Atom',
    'rss': '',
}

def clean_summary(text):
    if not text:
        return None
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text if text else None

def parse_atom_feed(root, source, category):
    items = []
    for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
        title_el = entry.find('{http://www.w3.org/2005/Atom}title')
        title = title_el.text.strip() if title_el is not None and title_el.text else None

        link_el = entry.find('{http://www.w3.org/2005/Atom}link')
        link = link_el.get('href', '').strip() if link_el is not None else None

        updated_el = entry.find('{http://www.w3.org/2005/Atom}updated')
        published_el = entry.find('{http://www.w3.org/2005/Atom}published')
        date_str = None
        for el in [published_el, updated_el]:
            if el is not None and el.text:
                date_str = el.text.strip()
                break

        summary_el = entry.find('{http://www.w3.org/2005/Atom}summary')
        content_el = entry.find('{http://www.w3.org/2005/Atom}content')
        summary_text = None
        for el in [summary_el, content_el]:
            if el is not None and el.text:
                summary_text = clean_summary(el.text)
                break

        items.append({
            "source": source,
            "category": category,
            "title": title,
            "published": date_str,
            "summary": summary_text,
            "link": link,
        })
    return items

def parse_rss_feed(root, source, category):
    items = []
    channel = root.find('channel')
    if channel is None:
        channel = root
    for item in channel.findall('item'):
        title_el = item.find('title')
        title = title_el.text.strip() if title_el is not None and title_el.text else None

        link_el = item.find('link')
        link = link_el.text.strip() if link_el is not None and link_el.text else None

        pubdate_el = item.find('pubDate')
        date_str = None
        if pubdate_el is not None and pubdate_el.text:
            try:
                dt = parsedate_to_datetime(pubdate_el.text.strip())
                date_str = dt.isoformat()
            except Exception:
                date_str = pubdate_el.text.strip()

        desc_el = item.find('description')
        summary = clean_summary(desc_el.text) if desc_el is not None else None

        items.append({
            "source": source,
            "category": category,
            "title": title,
            "published": date_str,
            "summary": summary,
            "link": link,
        })
    return items

def fetch_feed(feed_info):
    source = feed_info["source"]
    url = feed_info["url"]
    category = feed_info["category"]

    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        return [], f"{source}: fetch error -- {e}"

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        return [], f"{source}: XML parse error -- {e}"

    tag = root.tag.lower()
    if 'atom' in tag or root.tag == '{http://www.w3.org/2005/Atom}feed':
        items = parse_atom_feed(root, source, category)
    else:
        items = parse_rss_feed(root, source, category)

    return items, None

def deduplicate(items):
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
