#!/usr/bin/env python3
"""
AI-Cake Reasoning Layer -- Deterministic/Probabilistic Split

Produces a briefing in two clearly separated layers:
1. DETERMINISTIC: calculated facts, verifiable by anyone
2. PROBABILISTIC: AI-interpreted patterns, marked with confidence and bias flags

Uses Haiku for pattern detection, Sonnet for synthesis, and a cognitive
bias checker that examines the probabilistic layer.
"""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import anthropic

# --- Config ------------------------------------------------------------------

HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-4-6"
OUTPUT_DIR = Path(__file__).parent / "output"
DAYS_BACK = 7

# --- Deterministic layer (pure Python, no LLM) ------------------------------


def compute_deterministic(feed_data, api_data):
    """Calculate all verifiable facts from the data. No AI involved."""
    facts = []

    # --- PyPI adoption facts ---
    pypi = api_data.get("pypi", [])
    pypi_valid = [p for p in pypi if p.get("downloads") and not p.get("error")]
    pypi_sorted = sorted(pypi_valid, key=lambda p: p["downloads"].get("last_week", 0), reverse=True)

    for p in pypi_sorted:
        dl = p["downloads"]
        week = dl.get("last_week", 0)
        month = dl.get("last_month", 0)
        monthly_avg = month / 4.33 if month else 0
        trend_pct = ((week - monthly_avg) / monthly_avg * 100) if monthly_avg > 0 else None

        fact = {
            "source": "PyPI",
            "subject": p["package"],
            "metrics": {
                "weekly_downloads": week,
                "monthly_downloads": month,
                "trend_vs_monthly_avg": round(trend_pct, 1) if trend_pct is not None else None,
            },
            "latest_version": p.get("latest_version"),
            "latest_date": p.get("latest_date"),
        }
        facts.append(fact)

    # --- npm adoption facts ---
    npm = api_data.get("npm", [])
    npm_valid = [p for p in npm if p.get("downloads") and not p.get("error")]
    for p in sorted(npm_valid, key=lambda x: (x["downloads"].get("last_week") or 0), reverse=True):
        dl = p["downloads"]
        week = dl.get("last_week", 0) or 0
        month = dl.get("last_month", 0) or 0
        monthly_avg = month / 4.33 if month else 0
        trend_pct = ((week - monthly_avg) / monthly_avg * 100) if monthly_avg > 0 else None
        facts.append({
            "source": "npm",
            "subject": p["package"],
            "metrics": {
                "weekly_downloads": week,
                "monthly_downloads": month,
                "trend_vs_monthly_avg": round(trend_pct, 1) if trend_pct is not None else None,
            },
        })

    # --- Docker facts ---
    docker = api_data.get("docker", [])
    for d in sorted(docker, key=lambda x: x.get("pull_count", 0), reverse=True):
        if not d.get("error"):
            facts.append({
                "source": "Docker Hub",
                "subject": d["image"],
                "metrics": {"total_pulls": d["pull_count"]},
                "last_updated": d.get("last_updated"),
            })

    # --- GitHub repo facts ---
    github = api_data.get("github", [])
    for r in sorted(github, key=lambda x: x.get("stars", 0), reverse=True):
        if not r.get("error"):
            issue_star_ratio = round(r["open_issues"] / max(r["stars"], 1) * 100, 2)
            facts.append({
                "source": "GitHub",
                "subject": r["repo"],
                "metrics": {
                    "stars": r["stars"],
                    "forks": r["forks"],
                    "open_issues": r["open_issues"],
                    "issue_to_star_ratio_pct": issue_star_ratio,
                },
                "last_push": r.get("pushed_at", "")[:10],
            })

    # --- Release cadence facts ---
    if feed_data:
        from collections import Counter
        release_counts = Counter()
        releases_detail = []
        for item in feed_data.get("items", []):
            if item.get("category") == "github":
                release_counts[item["source"]] += 1
                releases_detail.append({
                    "repo": item["source"],
                    "version": item.get("title", "unknown"),
                    "date": item.get("published", ""),
                })

        for repo, count in release_counts.most_common():
            facts.append({
                "source": "GitHub Releases",
                "subject": repo,
                "metrics": {"releases_in_feed": count},
            })

    # --- OpenRouter pricing facts ---
    openrouter = api_data.get("openrouter", [])
    if openrouter:
        providers = {}
        for m in openrouter:
            prov = m["provider"]
            if prov not in providers or m["prompt_cost_per_token"] > providers[prov]["prompt_cost_per_token"]:
                providers[prov] = m

        for m in sorted(providers.values(), key=lambda x: x["prompt_cost_per_token"], reverse=True):
            facts.append({
                "source": "OpenRouter",
                "subject": m["model_id"],
                "metrics": {
                    "input_cost_per_mtok": round(m["prompt_cost_per_token"] * 1_000_000, 2),
                    "output_cost_per_mtok": round(m["completion_cost_per_token"] * 1_000_000, 2),
                    "context_length": m["context_length"],
                },
            })

        # Aggregate stats
        costs = [m["prompt_cost_per_token"] * 1_000_000 for m in openrouter if m["prompt_cost_per_token"] > 0]
        free_models = sum(1 for m in openrouter if m["prompt_cost_per_token"] == 0)
        large_ctx = sum(1 for m in openrouter if m["context_length"] >= 1_000_000)
        facts.append({
            "source": "OpenRouter (aggregate)",
            "subject": "market_summary",
            "metrics": {
                "total_models": len(openrouter),
                "free_models": free_models,
                "models_with_1m_plus_context": large_ctx,
                "median_input_cost_per_mtok": round(sorted(costs)[len(costs) // 2], 2) if costs else 0,
                "min_paid_input_cost_per_mtok": round(min(costs), 2) if costs else 0,
                "max_input_cost_per_mtok": round(max(costs), 2) if costs else 0,
            },
        })

    # --- EDGAR facts ---
    edgar = api_data.get("edgar", [])
    for co in edgar:
        if not co.get("error"):
            filings = co.get("recent_filings", [])
            facts.append({
                "source": "SEC EDGAR",
                "subject": f"{co['company']} ({co['ticker']})",
                "metrics": {"recent_filings_count": len(filings)},
                "filings": filings,
            })

    # --- arXiv facts ---
    if feed_data:
        research = [i for i in feed_data.get("items", []) if i.get("category") == "research"]
        facts.append({
            "source": "arXiv cs.AI",
            "subject": "daily_volume",
            "metrics": {"papers_today": len(research)},
        })

    # --- HuggingFace facts ---
    hf = api_data.get("huggingface", [])
    if hf:
        facts.append({
            "source": "HuggingFace (aggregate)",
            "subject": "trending_summary",
            "metrics": {
                "top_model": hf[0]["model_id"] if hf else None,
                "top_model_likes": hf[0]["likes"] if hf else 0,
                "top_model_downloads": hf[0]["downloads"] if hf else 0,
                "total_trending_models": len(hf),
            },
        })

    return facts


# --- Probabilistic layer (LLM-powered) --------------------------------------

PATTERN_DETECTION_PROMPT = """You are an AI industry pattern detector. You will receive a set of VERIFIED FACTS
(calculated deterministically from structured data). Your job is to identify patterns,
connections, and anomalies.

CRITICAL RULES:
1. Every interpretation MUST reference specific facts by their exact numbers.
2. Rate your confidence: HIGH (multiple corroborating facts), MEDIUM (plausible but limited evidence), LOW (speculative).
3. For each interpretation, state what evidence would DISPROVE it.
4. Do NOT present interpretations as facts. Use language like "suggests", "may indicate", "is consistent with".
5. If the data doesn't support a strong conclusion, say so. "No clear pattern" is a valid finding.
6. Use -- for dashes, never em dashes.

Return as a JSON array of objects:
{
  "pattern": "one-sentence description of the pattern",
  "supporting_facts": ["fact references"],
  "confidence": "HIGH/MEDIUM/LOW",
  "would_disprove": "what evidence would invalidate this interpretation",
  "category": "adoption/velocity/capital/research/cross-cutting"
}

Keep to 6-10 patterns maximum. Quality over quantity."""


BIAS_CHECK_PROMPT = """You are a cognitive bias checker. You will receive a set of AI-generated
pattern interpretations alongside the raw facts they claim to be based on.

Your job is NOT to argue with the interpretations. Your job is to examine the REASONING PROCESS
and flag specific cognitive biases.

Check each interpretation against these biases:

1. NARRATIVE FALLACY: Are unrelated facts being woven into a coherent story? Would the story
   collapse if any single fact were removed?

2. CONFIRMATION BIAS: Is the analysis only citing facts that support the pattern while ignoring
   contradictory data in the same dataset?

3. RECENCY BIAS: Is something being flagged as significant simply because it happened recently?
   Without a historical baseline, how do we know this is unusual?

4. BASE RATE NEGLECT: Are absolute numbers being presented as meaningful without context?
   (e.g., "23M downloads" -- is that high or low for this package?)

5. ANCHORING: Is the entire analysis structured around one striking number? Would the
   conclusions change if that number were 20% different?

6. SURVIVORSHIP BIAS: Is the analysis only looking at things that exist in the data?
   What's missing? (companies not tracked, sources not included, failures not captured)

For each interpretation, return:
{
  "pattern_index": 0,
  "biases_detected": ["BIAS_NAME: explanation"],
  "severity": "NONE/LOW/MEDIUM/HIGH",
  "recommendation": "what the reader should keep in mind"
}

Be rigorous but not nihilistic. Some patterns ARE real. Your job is to flag which ones
the reader should scrutinize vs trust.

Use -- for dashes, never em dashes."""


SYNTHESIS_PROMPT = """You are writing the final AI-Cake intelligence briefing. You have three inputs:

1. DETERMINISTIC FACTS -- calculated, verifiable, no AI interpretation
2. PROBABILISTIC PATTERNS -- AI-detected patterns with confidence ratings
3. BIAS CHECK -- flags on the patterns from a cognitive bias review

Write a briefing that:
- Opens with a 2-3 sentence executive summary
- Has 3-5 sections, each built on a pattern or theme
- For each section, clearly marks what is FACT vs INTERPRETATION
- Includes the bias checker's caveats where relevant (inline, not as a separate section)
- Ends with "Worth watching" -- 2-3 testable predictions (specific enough to be proven right or wrong next week)
- Is 1000-1500 words, markdown formatted
- Uses -- for dashes, never em dashes
- Writes for a curious but non-technical reader -- explain jargon in context
- When mentioning technical terms (8-K, Docker pulls, SDK), briefly explain what they are

IMPORTANT: This briefing should be HONEST about its own limitations. Where confidence is low
or biases were flagged, say so. The reader trusts you more when you're transparent about
uncertainty."""


# --- Helpers -----------------------------------------------------------------


def find_latest(pattern):
    files = sorted(OUTPUT_DIR.glob(pattern), reverse=True)
    return files[0] if files else None


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def call_llm(client, model, system, user_content):
    response = client.messages.create(
        model=model,
        max_tokens=4000,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_content}],
    )
    tokens_in = response.usage.input_tokens
    tokens_out = response.usage.output_tokens
    cache = getattr(response.usage, "cache_read_input_tokens", 0) or 0
    return response.content[0].text, tokens_in, tokens_out, cache


# --- Main --------------------------------------------------------------------


def main():
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d_%H%M")

    feed_file = find_latest("ai_cake_feed_*.json")
    api_file = find_latest("ai_cake_apis_*.json")

    if not api_file:
        print("No API data found. Run fetch_apis.py first.", file=sys.stderr)
        return 1

    feed_data = load_json(feed_file) if feed_file else {}
    api_data = load_json(api_file)

    print(f"  Feed data: {feed_file.name if feed_file else 'none'}")
    print(f"  API data: {api_file.name}")

    # --- Step 1: Deterministic facts ---
    print("\nStep 1: Computing deterministic facts...")
    facts = compute_deterministic(feed_data, api_data)
    print(f"  {len(facts)} facts computed")

    facts_json = json.dumps(facts, indent=2, ensure_ascii=False)

    # --- Step 2: Probabilistic pattern detection (Haiku) ---
    print("\nStep 2: Haiku detecting patterns...")
    client = anthropic.Anthropic()

    patterns_raw, p_in, p_out, p_cache = call_llm(
        client, HAIKU, PATTERN_DETECTION_PROMPT,
        f"VERIFIED FACTS:\n{facts_json}"
    )
    print(f"  Haiku: {p_in} in, {p_out} out (cache: {p_cache})")

    # --- Step 3: Cognitive bias check (Haiku) ---
    print("\nStep 3: Haiku checking for cognitive biases...")
    bias_raw, b_in, b_out, b_cache = call_llm(
        client, HAIKU, BIAS_CHECK_PROMPT,
        f"FACTS:\n{facts_json}\n\nPATTERN INTERPRETATIONS:\n{patterns_raw}"
    )
    print(f"  Haiku: {b_in} in, {b_out} out (cache: {b_cache})")

    # --- Step 4: Synthesis (Sonnet) ---
    print("\nStep 4: Sonnet synthesizing briefing...")
    briefing_raw, s_in, s_out, s_cache = call_llm(
        client, SONNET, SYNTHESIS_PROMPT,
        f"DETERMINISTIC FACTS:\n{facts_json}\n\nPROBABILISTIC PATTERNS:\n{patterns_raw}\n\nBIAS CHECK:\n{bias_raw}"
    )
    print(f"  Sonnet: {s_in} in, {s_out} out (cache: {s_cache})")

    # --- Write outputs ---
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Save the intermediate artifacts for transparency
    artifacts = {
        "generated_at": now.isoformat(),
        "deterministic_facts_count": len(facts),
        "deterministic_facts": facts,
        "probabilistic_patterns": patterns_raw,
        "bias_check": bias_raw,
        "token_usage": {
            "pattern_detection": {"model": HAIKU, "input": p_in, "output": p_out, "cache_read": p_cache},
            "bias_check": {"model": HAIKU, "input": b_in, "output": b_out, "cache_read": b_cache},
            "synthesis": {"model": SONNET, "input": s_in, "output": s_out, "cache_read": s_cache},
        },
    }
    artifacts_file = OUTPUT_DIR / f"artifacts_{timestamp}.json"
    artifacts_file.write_text(json.dumps(artifacts, indent=2, ensure_ascii=False), encoding="utf-8")

    # Save the briefing
    header = (
        f"# AI-Cake Intelligence Briefing\n"
        f"**Generated:** {now.strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"**Pipeline:** Deterministic facts -> Haiku patterns -> Haiku bias check -> Sonnet synthesis\n"
        f"**Facts:** {len(facts)} verified | **Patterns:** extracted by AI | **Bias check:** applied\n\n"
        f"---\n\n"
    )
    briefing_file = OUTPUT_DIR / f"briefing_split_{timestamp}.md"
    briefing_file.write_text(header + briefing_raw, encoding="utf-8")

    total_cost = (
        (p_in * 1 + p_out * 5) / 1_000_000 +  # Haiku
        (b_in * 1 + b_out * 5) / 1_000_000 +  # Haiku
        (s_in * 3 + s_out * 15) / 1_000_000    # Sonnet
    )

    print(f"\n  Artifacts: {artifacts_file}")
    print(f"  Briefing: {briefing_file}")
    print(f"  Estimated cost: ${total_cost:.4f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
