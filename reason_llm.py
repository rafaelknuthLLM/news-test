#!/usr/bin/env python3
"""
AI-Cake News Aggregator -- Layer 2 (REASON: LLM-powered)
Two-pass analysis: Haiku scans for signals, Sonnet writes the briefing.
Uses prompt caching to minimize cost on repeated runs.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic

# --- Config ------------------------------------------------------------------

HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-4-6"

OUTPUT_DIR = Path(__file__).parent / "output"

# The analysis framework -- cached across runs via prompt caching
SYSTEM_PROMPT = """You are an AI industry analyst producing a weekly intelligence briefing.

Your audience is a solo founder learning agentic engineering and AI development. He is curious
and smart but not deeply technical yet. He values plain language, honest assessment, and
"so what" context -- not jargon or hype.

Framework: Jensen Huang's "AI-Cake" layers:
- Compute/Hardware: chips, GPUs, data centers (NVIDIA, AMD, TSMC)
- System Software: drivers, runtimes, inference engines (CUDA, TensorRT, vLLM)
- Platform Software: APIs, SDKs, orchestration (Anthropic, OpenAI, LangChain, HuggingFace)
- Applications: products built on top (Claude Code, Ollama, coding assistants)

Your job is to find the SIGNAL in structured data that a human would miss, and explain
WHY it matters. You are reading machine-native data (download counts, repo metrics, SEC
filings, model pricing) -- data that is boring to humans but rich in insight.

Rules:
- Lead with the 3-5 most important signals, not a comprehensive list
- Explain what changed and why it matters -- not just what the numbers are
- Connect signals across sources when they tell a story together
- Flag anomalies (sudden spikes, unexpected drops, new entrants)
- Use -- for dashes, never em dashes
- Keep it scannable: headers, short paragraphs, no walls of text
- Be honest about what's noise vs signal
- End with "Worth watching" -- 2-3 things to keep an eye on next week"""


# --- Helpers -----------------------------------------------------------------


def find_latest(pattern):
    """Find the most recent file matching a glob pattern."""
    files = sorted(OUTPUT_DIR.glob(pattern), reverse=True)
    return files[0] if files else None


def load_json(path):
    """Load a JSON file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def count_tokens_approx(text):
    """Rough token count (1 token ~ 4 chars)."""
    return len(text) // 4


# --- Pass 1: Haiku scanner ---------------------------------------------------


def haiku_scan(client, data_summary):
    """Use Haiku to quickly classify and flag the most important signals."""
    response = client.messages.create(
        model=HAIKU,
        max_tokens=2000,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": f"""Scan this structured data from 9 sources (package registries,
GitHub, Docker Hub, HuggingFace, SEC filings, model pricing, arXiv, GitHub releases).

Identify the 5-8 most important signals -- things that changed, anomalies, trends,
or cross-source patterns. For each signal, give:
- What: one-sentence factual observation
- Why it matters: one sentence of context
- Confidence: high/medium/low

Also flag any data quality issues (missing data, failed fetches, stale sources).

Output as JSON array of objects with keys: what, why, confidence, sources.

DATA:
{data_summary}""",
            }
        ],
    )

    print(f"  Haiku scan: {response.usage.input_tokens} in, {response.usage.output_tokens} out")
    cache = getattr(response.usage, "cache_read_input_tokens", 0) or 0
    if cache:
        print(f"  Cache hit: {cache} tokens read from cache")

    return response.content[0].text


# --- Pass 2: Sonnet synthesizer ----------------------------------------------


def sonnet_synthesize(client, haiku_signals, raw_data_summary):
    """Use Sonnet to write the human-readable briefing from Haiku's signals."""
    response = client.messages.create(
        model=SONNET,
        max_tokens=4000,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": f"""Write this week's AI-Cake intelligence briefing.

You have two inputs:
1. A Haiku-generated signal scan (pre-classified important signals)
2. The raw structured data (for any details you need to reference)

Write a briefing that:
- Opens with a 2-3 sentence executive summary of the week
- Has 3-5 sections, each covering a key signal or theme
- Connects signals across sources when they tell a story together
- Ends with "Worth watching" section (2-3 things for next week)
- Is ~800-1200 words total
- Uses markdown formatting

HAIKU SIGNAL SCAN:
{haiku_signals}

RAW DATA (reference as needed):
{raw_data_summary}""",
            }
        ],
    )

    print(f"  Sonnet synthesis: {response.usage.input_tokens} in, {response.usage.output_tokens} out")
    cache = getattr(response.usage, "cache_read_input_tokens", 0) or 0
    if cache:
        print(f"  Cache hit: {cache} tokens read from cache")

    return response.content[0].text


# --- Data preparation --------------------------------------------------------


def prepare_data_summary(feed_data, api_data):
    """Prepare a condensed data summary for LLM consumption."""
    sections = []

    # PyPI
    pypi = api_data.get("pypi", [])
    if pypi:
        lines = ["## PyPI Downloads (Python packages)"]
        for p in sorted(pypi, key=lambda x: (x.get("downloads") or {}).get("last_week", 0), reverse=True):
            dl = p.get("downloads") or {}
            week = dl.get("last_week", 0)
            month = dl.get("last_month", 0)
            ver = p.get("latest_version", "?")
            date = p.get("latest_date", "")
            lines.append(f"- {p['package']}: {week:,}/week, {month:,}/month, v{ver} ({date})")
        sections.append("\n".join(lines))

    # npm
    npm = api_data.get("npm", [])
    if npm:
        lines = ["## npm Downloads (JavaScript packages)"]
        for p in sorted(npm, key=lambda x: (x.get("downloads") or {}).get("last_week", 0) or 0, reverse=True):
            dl = p.get("downloads") or {}
            week = dl.get("last_week", 0) or 0
            month = dl.get("last_month", 0) or 0
            lines.append(f"- {p['package']}: {week:,}/week, {month:,}/month")
        sections.append("\n".join(lines))

    # Docker
    docker = api_data.get("docker", [])
    if docker:
        lines = ["## Docker Hub (production deployment)"]
        for d in sorted(docker, key=lambda x: x.get("pull_count", 0), reverse=True):
            if not d.get("error"):
                lines.append(f"- {d['image']}: {d['pull_count']:,} total pulls, updated {d.get('last_updated','?')}")
        sections.append("\n".join(lines))

    # GitHub
    github = api_data.get("github", [])
    if github:
        lines = ["## GitHub Repositories"]
        for r in sorted(github, key=lambda x: x.get("stars", 0), reverse=True):
            if not r.get("error"):
                lines.append(f"- {r['repo']}: {r['stars']:,} stars, {r['forks']:,} forks, "
                             f"{r['open_issues']:,} issues, pushed {r.get('pushed_at','?')[:10]}")
        sections.append("\n".join(lines))

    # HuggingFace
    hf = api_data.get("huggingface", [])
    if hf:
        lines = ["## HuggingFace Trending Models (by likes this week)"]
        for m in hf[:15]:
            lines.append(f"- {m['model_id']}: {m['downloads']:,} downloads, {m['likes']:,} likes, {m['pipeline_tag']}")
        sections.append("\n".join(lines))

    # EDGAR
    edgar = api_data.get("edgar", [])
    if edgar:
        lines = ["## SEC EDGAR Filings (AI-Cake companies)"]
        all_filings = []
        for co in edgar:
            for f in co.get("recent_filings", []):
                all_filings.append(f"- [{f['date']}] {co['ticker']} {f['form']}: {f['description']}")
        all_filings.sort(reverse=True)
        lines.extend(all_filings[:15])
        sections.append("\n".join(lines))

    # OpenRouter pricing
    openrouter = api_data.get("openrouter", [])
    if openrouter:
        lines = ["## Model Pricing (OpenRouter, flagship per provider)"]
        providers = {}
        for m in openrouter:
            prov = m["provider"]
            if prov not in providers or m["prompt_cost_per_token"] > providers[prov]["prompt_cost_per_token"]:
                providers[prov] = m
        for m in sorted(providers.values(), key=lambda x: x["prompt_cost_per_token"], reverse=True):
            cost = m["prompt_cost_per_token"] * 1_000_000
            lines.append(f"- {m['model_id']}: ${cost:.2f}/M input, ctx {m['context_length']:,}")
        sections.append("\n".join(lines))

    # Releases (from feeds)
    if feed_data:
        items = [i for i in feed_data.get("items", []) if i.get("category") == "github"]
        if items:
            lines = ["## GitHub Releases (last 7 days)"]
            for item in items[:20]:
                title = item.get("title", "?")
                source = item.get("source", "?")
                summary = (item.get("summary") or "")[:150]
                lines.append(f"- {source}: {title}")
                if summary:
                    lines.append(f"  {summary}")
            sections.append("\n".join(lines))

    # arXiv (just titles for token efficiency)
    if feed_data:
        papers = [i for i in feed_data.get("items", []) if i.get("category") == "research"]
        if papers:
            lines = [f"## arXiv cs.AI ({len(papers)} papers today, titles only for brevity)"]
            for p in papers[:30]:
                title = (p.get("title") or "").strip()
                lines.append(f"- {title}")
            if len(papers) > 30:
                lines.append(f"- ... and {len(papers) - 30} more")
            sections.append("\n".join(lines))

    return "\n\n".join(sections)


# --- Main --------------------------------------------------------------------


def main():
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d_%H%M")

    # Load data
    feed_file = find_latest("ai_cake_feed_*.json")
    api_file = find_latest("ai_cake_apis_*.json")

    if not feed_file and not api_file:
        print("No data files found. Run fetch_feeds.py and/or fetch_apis.py first.", file=sys.stderr)
        return 1

    feed_data = load_json(feed_file) if feed_file else {}
    api_data = load_json(api_file) if api_file else {}

    print(f"  Feed data: {feed_file.name if feed_file else 'none'}")
    print(f"  API data: {api_file.name if api_file else 'none'}")

    # Prepare condensed data summary
    data_summary = prepare_data_summary(feed_data, api_data)
    approx_tokens = count_tokens_approx(data_summary)
    print(f"  Data summary: ~{approx_tokens:,} tokens")

    # Initialize client
    client = anthropic.Anthropic()

    # Pass 1: Haiku scan
    print("\nPass 1: Haiku scanning for signals...")
    haiku_signals = haiku_scan(client, data_summary)

    # Pass 2: Sonnet synthesis
    print("\nPass 2: Sonnet writing briefing...")
    briefing = sonnet_synthesize(client, haiku_signals, data_summary)

    # Write output
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Save the raw Haiku signals for debugging
    signals_file = OUTPUT_DIR / f"signals_{timestamp}.json"
    signals_file.write_text(haiku_signals, encoding="utf-8")

    # Save the final briefing
    header = (
        f"# AI-Cake Intelligence Briefing\n"
        f"**Generated:** {now.strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"**Sources:** {feed_file.name if feed_file else 'n/a'}, {api_file.name if api_file else 'n/a'}\n"
        f"**Pipeline:** Haiku 4.5 (scan) -> Sonnet 4.6 (synthesis)\n\n---\n\n"
    )
    briefing_file = OUTPUT_DIR / f"briefing_llm_{timestamp}.md"
    briefing_file.write_text(header + briefing, encoding="utf-8")

    print(f"\n  Signals: {signals_file}")
    print(f"  Briefing: {briefing_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
