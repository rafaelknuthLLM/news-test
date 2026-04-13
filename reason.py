#!/usr/bin/env python3
"""
AI-Cake News Aggregator -- Layer 2 (REASON)
Filters, categorizes, and formats Layer 1 data into a readable briefing.
No LLM calls. Pure filtering and formatting.
"""

import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# --- Config ------------------------------------------------------------------

DAYS_BACK = 7

ARXIV_KEYWORDS = [
    # Agentic engineering (your primary learning area)
    "agentic", "multi-agent", "tool use", "tool-use", "tool calling",
    "function calling", "agent framework", "agent orchestration",
    # Code + software
    "code generation", "code synthesis", "program synthesis",
    "coding assistant", "software engineering", "automated programming",
    # RAG + retrieval
    "retrieval-augmented", "retrieval augmented", r"\bRAG\b",
    # Prompting techniques
    "chain-of-thought", "in-context learning", "few-shot",
    # Safety (relevant to responsible building)
    "red teaming", "jailbreak", "guardrail",
]

# Compile a single regex for speed
# Keywords starting with \b are already regex patterns; others get escaped
_ARXIV_PATTERN = re.compile(
    "|".join(kw if kw.startswith(r"\b") else re.escape(kw) for kw in ARXIV_KEYWORDS),
    re.IGNORECASE,
)

# --- Helpers -----------------------------------------------------------------


def parse_iso(s):
    """Parse an ISO 8601 date string to a timezone-aware datetime."""
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def matches_arxiv_keywords(item):
    """Check if an arXiv item's title or summary matches any keyword."""
    text = (item.get("title") or "") + " " + (item.get("summary") or "")
    return bool(_ARXIV_PATTERN.search(text))


def format_date(dt):
    """Format datetime as MM/DD."""
    return dt.strftime("%m/%d")


def truncate(text, length=200):
    """Truncate text to length, adding ... if needed."""
    if not text or len(text) <= length:
        return text
    return text[:length].rsplit(" ", 1)[0] + "..."


# --- Main --------------------------------------------------------------------


def main():
    output_dir = Path(__file__).parent / "output"

    # Find the most recent Layer 1 JSON
    json_files = sorted(output_dir.glob("ai_cake_feed_*.json"), reverse=True)
    if not json_files:
        print("No Layer 1 output found in output/. Run fetch_feeds.py first.", file=sys.stderr)
        return 1

    latest = json_files[0]
    print(f"  Reading: {latest.name}")

    with open(latest, encoding="utf-8") as f:
        data = json.load(f)

    # Filter to last N days
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=DAYS_BACK)

    releases = []
    arxiv_matched = []
    arxiv_total = 0

    for item in data["items"]:
        dt = parse_iso(item.get("published"))
        if not dt or dt < cutoff:
            continue

        if item["category"] == "research":
            arxiv_total += 1
            if matches_arxiv_keywords(item):
                arxiv_matched.append((item, dt))
        elif item["category"] == "github":
            releases.append((item, dt))

    # Sort newest first
    releases.sort(key=lambda x: x[1], reverse=True)
    arxiv_matched.sort(key=lambda x: x[1], reverse=True)

    # Build markdown briefing
    lines = []
    lines.append(f"# AI-Cake Weekly Briefing")
    lines.append(f"**Generated:** {now.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"**Period:** last {DAYS_BACK} days")
    lines.append(f"**Source:** {latest.name}")
    lines.append("")

    # --- Releases ---
    lines.append(f"## Releases ({len(releases)} items)")
    lines.append("")
    if releases:
        for item, dt in releases:
            title = item["title"] or "(no title)"
            source = item["source"]
            link = item.get("link") or ""
            summary = truncate(item.get("summary"), 200)
            lines.append(f"### [{format_date(dt)}] {title}")
            lines.append(f"**Repo:** {source}  ")
            if link:
                lines.append(f"**Link:** {link}  ")
            if summary:
                lines.append(f"{summary}")
            lines.append("")
    else:
        lines.append("No releases in this period.")
        lines.append("")

    # --- Research ---
    arxiv_filtered = arxiv_total - len(arxiv_matched)
    lines.append(f"## Research ({len(arxiv_matched)} relevant / {arxiv_total} total arXiv cs.AI)")
    lines.append(f"*Filtered by keyword relevance. {arxiv_filtered} papers skipped.*")
    lines.append("")
    if arxiv_matched:
        for item, dt in arxiv_matched:
            title = (item["title"] or "(no title)").strip()
            # Clean arXiv prefix from title
            title = re.sub(r"^arXiv:\d+\.\d+v?\d*\s*", "", title)
            summary = truncate(item.get("summary"), 300)
            link = item.get("link") or ""
            lines.append(f"### {title}")
            if link:
                lines.append(f"**Link:** {link}  ")
            if summary:
                lines.append(f"{summary}")
            lines.append("")
    else:
        lines.append("No keyword-matched papers in this period.")
        lines.append("")

    # --- Meta ---
    lines.append("---")
    lines.append(f"*Layer 1 feeds: {data['meta']['total_feeds']} | "
                 f"Layer 1 items: {data['meta']['total_items']} | "
                 f"After date filter: {len(releases) + arxiv_total} | "
                 f"After keyword filter: {len(releases) + len(arxiv_matched)}*")

    briefing = "\n".join(lines)

    # Write briefing
    timestamp = now.strftime("%Y%m%d_%H%M")
    briefing_file = output_dir / f"briefing_{timestamp}.md"
    briefing_file.write_text(briefing, encoding="utf-8")

    print(f"  Releases: {len(releases)}")
    print(f"  Research: {len(arxiv_matched)}/{arxiv_total} (keyword-filtered)")
    print(f"  Output:   {briefing_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
