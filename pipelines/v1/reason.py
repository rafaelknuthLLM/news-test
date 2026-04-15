#!/usr/bin/env python3
"""
AI-Cake News Aggregator -- Layer 2 (REASON)
Reads feed data + API data, produces a unified briefing.
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


def fmt_num(n):
    """Format a number with commas."""
    if n is None:
        return "n/a"
    return f"{n:,}"


def find_latest(pattern, output_dir):
    """Find the most recent file matching a glob pattern."""
    files = sorted(output_dir.glob(pattern), reverse=True)
    return files[0] if files else None


# --- Section builders --------------------------------------------------------


def trend_indicator(weekly, monthly):
    """Compare weekly rate to monthly average. Returns arrow + percentage."""
    if not weekly or not monthly or monthly == 0:
        return ""
    weekly_avg = monthly / 4.33  # avg weeks per month
    if weekly_avg == 0:
        return ""
    delta = ((weekly - weekly_avg) / weekly_avg) * 100
    if delta > 5:
        return f" ^{delta:.0f}%"
    elif delta < -5:
        return f" v{abs(delta):.0f}%"
    return " ="


def build_signals_section(api_data):
    """Build the Signals section from API data."""
    lines = []
    lines.append("## Signals (API data)")
    lines.append("")

    # --- PyPI adoption ---
    pypi = api_data.get("pypi", [])
    if pypi:
        lines.append("### Python ecosystem (PyPI)")
        lines.append("")
        lines.append("| Package | Weekly | Monthly | Trend | Latest |")
        lines.append("|---|---:|---:|---|---|")
        pypi_sorted = sorted(
            pypi,
            key=lambda p: (p.get("downloads") or {}).get("last_week", 0),
            reverse=True,
        )
        for p in pypi_sorted:
            pkg = p["package"]
            dl = p.get("downloads") or {}
            week = dl.get("last_week", 0)
            month = dl.get("last_month", 0)
            trend = trend_indicator(week, month)
            ver = p.get("latest_version") or "?"
            date = p.get("latest_date") or ""
            ver_str = f"{ver} ({date})" if date else ver
            lines.append(f"| {pkg} | {fmt_num(week)} | {fmt_num(month)} | {trend} | {ver_str} |")
        lines.append("")

    # --- npm adoption ---
    npm = api_data.get("npm", [])
    if npm:
        lines.append("### JavaScript ecosystem (npm)")
        lines.append("")
        lines.append("| Package | Weekly | Monthly | Trend |")
        lines.append("|---|---:|---:|---|")
        npm_sorted = sorted(
            npm,
            key=lambda p: (p.get("downloads") or {}).get("last_week", 0) or 0,
            reverse=True,
        )
        for p in npm_sorted:
            pkg = p["package"]
            dl = p.get("downloads") or {}
            week = dl.get("last_week", 0) or 0
            month = dl.get("last_month", 0) or 0
            trend = trend_indicator(week, month)
            lines.append(f"| {pkg} | {fmt_num(week)} | {fmt_num(month)} | {trend} |")
        lines.append("")

    # --- Docker Hub ---
    docker = api_data.get("docker", [])
    if docker:
        lines.append("### Production deployment (Docker Hub pulls)")
        lines.append("")
        lines.append("| Image | Total pulls | Last updated |")
        lines.append("|---|---:|---|")
        docker_sorted = sorted(
            docker,
            key=lambda d: d.get("pull_count", 0),
            reverse=True,
        )
        for d in docker_sorted:
            if d.get("error"):
                lines.append(f"| {d['image']} | error | |")
                continue
            image = d["image"]
            pulls = fmt_num(d.get("pull_count"))
            updated = d.get("last_updated", "")
            lines.append(f"| {image} | {pulls} | {updated} |")
        lines.append("")

    # --- GitHub repos ---
    github = api_data.get("github", [])
    if github:
        lines.append("### Repository activity (GitHub)")
        lines.append("")
        lines.append("| Repo | Stars | Forks | Open issues | Last push |")
        lines.append("|---|---:|---:|---:|---|")
        github_sorted = sorted(
            github,
            key=lambda r: r.get("stars", 0),
            reverse=True,
        )
        for r in github_sorted:
            if r.get("error"):
                lines.append(f"| {r['repo']} | error | | | |")
                continue
            repo = r["repo"]
            stars = fmt_num(r.get("stars"))
            forks = fmt_num(r.get("forks"))
            issues = fmt_num(r.get("open_issues"))
            pushed = r.get("pushed_at", "")[:10]
            lines.append(f"| {repo} | {stars} | {forks} | {issues} | {pushed} |")
        lines.append("")

    # --- HuggingFace trending ---
    hf = api_data.get("huggingface", [])
    if hf:
        lines.append("### Trending models (HuggingFace, by likes this week)")
        lines.append("")
        lines.append("| # | Model | Downloads | Likes | Type |")
        lines.append("|--:|---|---:|---:|---|")
        for i, m in enumerate(hf[:15], 1):
            name = m.get("model_id", "unknown")
            dl = fmt_num(m.get("downloads"))
            likes = fmt_num(m.get("likes"))
            ptype = m.get("pipeline_tag", "n/a")
            lines.append(f"| {i} | {name} | {dl} | {likes} | {ptype} |")
        lines.append("")

    # --- SEC EDGAR filings ---
    edgar = api_data.get("edgar", [])
    if edgar:
        has_filings = any(r.get("recent_filings") for r in edgar)
        if has_filings:
            lines.append("### SEC filings (AI-Cake companies)")
            lines.append("")
            lines.append("| Date | Company | Form | Description |")
            lines.append("|---|---|---|---|")
            all_filings = []
            for co in edgar:
                if co.get("error"):
                    continue
                for f in co.get("recent_filings", []):
                    all_filings.append({
                        "date": f["date"],
                        "ticker": co["ticker"],
                        "form": f["form"],
                        "desc": f["description"][:60] if f["description"] else "",
                    })
            all_filings.sort(key=lambda x: x["date"], reverse=True)
            for f in all_filings[:20]:
                lines.append(f"| {f['date']} | {f['ticker']} | {f['form']} | {f['desc']} |")
            lines.append("")

    # --- OpenRouter model pricing ---
    openrouter = api_data.get("openrouter", [])
    if openrouter:
        lines.append("### Model pricing (OpenRouter, flagship per provider)")
        lines.append("")
        lines.append("| Provider | Model | Context | $/M input | $/M output |")
        lines.append("|---|---|---:|---:|---:|")
        providers = {}
        for m in openrouter:
            prov = m["provider"]
            if prov not in providers or m["prompt_cost_per_token"] > providers[prov]["prompt_cost_per_token"]:
                providers[prov] = m
        flagships = sorted(providers.values(), key=lambda m: m["prompt_cost_per_token"], reverse=True)
        for m in flagships:
            model_short = m["model_id"].split("/", 1)[1] if "/" in m["model_id"] else m["model_id"]
            ctx = fmt_num(m["context_length"])
            input_cost = f"${m['prompt_cost_per_token'] * 1_000_000:.2f}"
            output_cost = f"${m['completion_cost_per_token'] * 1_000_000:.2f}"
            lines.append(f"| {m['provider']} | {model_short} | {ctx} | {input_cost} | {output_cost} |")
        lines.append("")

    return lines


def build_releases_section(feed_data, cutoff):
    """Build the Releases section from feed data."""
    releases = []
    for item in feed_data.get("items", []):
        if item.get("category") != "github":
            continue
        dt = parse_iso(item.get("published"))
        if not dt or dt < cutoff:
            continue
        releases.append((item, dt))

    releases.sort(key=lambda x: x[1], reverse=True)

    lines = []
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

    return lines, len(releases)


def build_research_section(feed_data, cutoff):
    """Build the Research section from feed data."""
    arxiv_matched = []
    arxiv_total = 0

    for item in feed_data.get("items", []):
        if item.get("category") != "research":
            continue
        dt = parse_iso(item.get("published"))
        if not dt or dt < cutoff:
            continue
        arxiv_total += 1
        if matches_arxiv_keywords(item):
            arxiv_matched.append((item, dt))

    arxiv_matched.sort(key=lambda x: x[1], reverse=True)
    arxiv_filtered = arxiv_total - len(arxiv_matched)

    lines = []
    lines.append(f"## Research ({len(arxiv_matched)} relevant / {arxiv_total} total arXiv cs.AI)")
    lines.append(f"*Filtered by keyword relevance. {arxiv_filtered} papers skipped.*")
    lines.append("")
    if arxiv_matched:
        for item, dt in arxiv_matched:
            title = (item["title"] or "(no title)").strip()
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

    return lines, len(arxiv_matched), arxiv_total


# --- Main --------------------------------------------------------------------


def main():
    output_dir = Path(__file__).parent / "output"
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=DAYS_BACK)

    # Find data files
    feed_file = find_latest("ai_cake_feed_*.json", output_dir)
    api_file = find_latest("ai_cake_apis_*.json", output_dir)

    if not feed_file and not api_file:
        print("No data files found. Run fetch_feeds.py and/or fetch_apis.py first.", file=sys.stderr)
        return 1

    feed_data = {}
    api_data = {}
    sources_used = []

    if feed_file:
        print(f"  Reading: {feed_file.name}")
        with open(feed_file, encoding="utf-8") as f:
            feed_data = json.load(f)
        sources_used.append(feed_file.name)

    if api_file:
        print(f"  Reading: {api_file.name}")
        with open(api_file, encoding="utf-8") as f:
            api_data = json.load(f)
        sources_used.append(api_file.name)

    # Build briefing
    lines = []
    lines.append("# AI-Cake Weekly Briefing")
    lines.append(f"**Generated:** {now.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"**Period:** last {DAYS_BACK} days")
    lines.append(f"**Sources:** {', '.join(sources_used)}")
    lines.append("")

    # Section 1: Signals (from APIs)
    release_count = 0
    research_matched = 0
    research_total = 0

    if api_data:
        lines.extend(build_signals_section(api_data))

    # Section 2: Releases (from feeds)
    if feed_data:
        release_lines, release_count = build_releases_section(feed_data, cutoff)
        lines.extend(release_lines)

    # Section 3: Research (from feeds)
    if feed_data:
        research_lines, research_matched, research_total = build_research_section(feed_data, cutoff)
        lines.extend(research_lines)

    # Footer
    lines.append("---")
    meta_parts = []
    if api_data:
        s = api_data.get("meta", {}).get("sources", {})
        meta_parts.append(f"APIs: {s.get('pypi_packages', 0)} packages, "
                          f"{s.get('github_repos', 0)} repos, "
                          f"{s.get('huggingface_models', 0)} models")
    if feed_data:
        meta_parts.append(f"Feeds: {feed_data.get('meta', {}).get('total_feeds', 0)} sources, "
                          f"{feed_data.get('meta', {}).get('total_items', 0)} items")
    meta_parts.append(f"Briefing: {release_count} releases, {research_matched}/{research_total} papers")
    lines.append(f"*{' | '.join(meta_parts)}*")

    briefing = "\n".join(lines)

    # Write
    timestamp = now.strftime("%Y%m%d_%H%M")
    briefing_file = output_dir / f"briefing_{timestamp}.md"
    briefing_file.write_text(briefing, encoding="utf-8")

    print(f"  Signals: {len(api_data.get('pypi', []))} packages, "
          f"{len(api_data.get('github', []))} repos, "
          f"{len(api_data.get('huggingface', []))} models")
    print(f"  Releases: {release_count}")
    print(f"  Research: {research_matched}/{research_total} (keyword-filtered)")
    print(f"  Output:   {briefing_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
