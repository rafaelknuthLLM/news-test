# AI-Cake Intelligence System -- Session Log
**Date:** 2026-04-13/14 (session ran ~6 hours, 20:30 - 02:30 CET)

## What We Built

An AI-native intelligence system that monitors the AI industry through machine-readable data sources, then uses a two-pass LLM pipeline to produce a human-readable briefing. Total cost: ~$0.06 per briefing.

### The Key Insight (mid-session pivot)

Started with RSS feeds (human-readable sources) -- expensive to fetch, limited insight. Pivoted to **machine-native APIs** (package registries, GitHub stats, Docker Hub, SEC filings, model pricing) -- near-zero fetch cost, rich signals that no human journalist covers. The AI reads data that's boring to humans, then translates it into insight.

**The inversion:** instead of a human telling the AI what to read, the AI leads on data sources and translates back for the human.

## Repo Structure

```
C:\Users\rafae\VSCode_Rafael\news-test\
GitHub: https://github.com/rafaelknuthLLM/news-test

fetch_feeds.py        -- Layer 1: arXiv RSS + 5 GitHub releases Atom feeds
fetch_apis.py         -- Layer 1: PyPI, npm, Docker Hub, GitHub stats, HuggingFace, SEC EDGAR, OpenRouter
reason.py             -- Layer 2: rule-based briefing (tables, trend arrows) -- no LLM, free
reason_llm.py         -- Layer 2: LLM-powered briefing (Haiku scan + Sonnet synthesis, ~$0.06/run)
requirements.txt      -- feedparser, anthropic, python-dotenv
.env                  -- API key (gitignored, never committed)
.gitignore            -- excludes output/ and .env
PRD.md                -- product requirements doc (6 signal types, phased roadmap)
```

## Data Sources (9 total, all working)

| Source | Script | Data Points | Cost |
|---|---|---|---|
| arXiv cs.AI RSS | fetch_feeds.py | ~289 papers/day | Free |
| GitHub Releases Atom (5 repos) | fetch_feeds.py | ~50 releases/week | Free |
| PyPI download stats (10 packages) | fetch_apis.py | Weekly + monthly counts | Free |
| npm download stats (6 packages) | fetch_apis.py | Weekly + monthly counts | Free |
| Docker Hub pulls (5 images) | fetch_apis.py | Total pull counts | Free |
| GitHub repo metrics (10 repos) | fetch_apis.py | Stars, forks, issues | Free |
| HuggingFace trending (20 models) | fetch_apis.py | Downloads, likes, type | Free |
| SEC EDGAR filings (8 companies) | fetch_apis.py | 10-K, 10-Q, 8-K forms | Free |
| OpenRouter model pricing (232 models) | fetch_apis.py | Per-token pricing, context | Free |

## How to Run

```bash
cd C:\Users\rafae\VSCode_Rafael\news-test

# Full pipeline (rule-based briefing, free)
python fetch_feeds.py && python fetch_apis.py && python reason.py

# Full pipeline (LLM briefing, ~$0.06)
python fetch_feeds.py && python fetch_apis.py && python reason_llm.py
```

Output goes to `output/` directory (gitignored).

## LLM Pipeline Details

- **Pass 1 -- Haiku 4.5:** Scans ~2,600 tokens of structured data, identifies 5-8 key signals. Cost: ~$0.01
- **Pass 2 -- Sonnet 4.6:** Takes Haiku's signals + raw data, writes ~1,000-word briefing. Cost: ~$0.05
- **Prompt caching:** System prompt (analysis framework) is cached across runs via `cache_control: ephemeral`
- **API key:** Stored in `.env`, loaded via python-dotenv. Never committed to git.

## Known Issues

- PyPI rate limiting: pypistats.org sometimes drops requests despite 1.5s delay. Non-critical (script continues with partial data).
- SEC EDGAR: requires email in User-Agent header (`EDGAR_USER_AGENT` in fetch_apis.py).
- Semantic Scholar: rate-limited (429), needs API key for reliable access. Deferred to Phase 2.
- anthropic SDK: installed version is 0.84.0, may need upgrade for latest features.

## What's Next (prioritized)

### 1. History tracking (high value, no cost)
Store key metrics from each run to a `history.json` file. Next run compares against previous. Briefings then show real week-over-week deltas instead of approximations.

### 2. Automate as scheduled task (high value, Max plan)
Deploy as a Claude Code scheduled task:
- Runs daily (or weekly)
- Clones repo, runs fetch scripts, runs reason_llm.py
- Commits briefing to repo, pushes
- Emails via Gmail MCP
- No additional cost beyond Max plan

### 3. PRD update
Capture the architecture pivot (machine-native sources, AI-interpreted, human-consumed). The current PRD.md was written before the pivot.

### 4. Phase 2 sources (from PRD)
- Semantic Scholar (citation velocity -- needs API key)
- LMSYS Chatbot Arena (benchmark rankings)
- Cloud GPU pricing (AWS, GCP, Azure)
- libraries.io (dependency tracking)

### 5. Agent SDK exploration
- Claude Managed Agents launched April 8, 2026
- Agent SDK supports subagents with parallel execution
- Could enable multi-agent patterns: scanner agents, deep-dive agents, synthesis agents

## Build Plan Reference

Original build plan: `C:\Users\rafae\VSCode_Rafael\weely_planning\CW_16_2026\WORKSTREAM - FIRST PRINCIPLES SYSTEM\build_plan_04132026.md`

## Git History

```
ee587bd add .env support for API key, update requirements
ae34531 add LLM-powered reasoning layer (Haiku scan + Sonnet synthesis)
970cfd3 add SEC EDGAR filings + OpenRouter model pricing, fix PyPI rate limit
f71f399 add npm, Docker Hub sources + trend indicators + PRD
0a9b3ef add API fetch layer (PyPI, GitHub, HuggingFace) + unified briefing
0a274ed add Layer 2 reason pipeline, trim feeds to releases + arXiv only
4f79548 add Layer 1 RSS/Atom fetch pipeline -- 10 feeds, all working
60a201a remove old web search briefing -- repo repurposed for RSS/Atom fetch pipeline
```
