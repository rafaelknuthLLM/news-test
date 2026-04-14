# AI-Cake Intelligence System

An AI-powered intelligence system that monitors the AI industry through machine-readable data sources and produces weekly briefings. Built for $0.06 per run.

## The Problem

Staying informed about the AI industry means choosing between reading news (narrative-driven, opinion-heavy, covers what gets clicks) or going to the source (GitHub changelogs, arXiv papers, download stats, SEC filings -- scattered, boring, impractical for humans).

This project automates the second option and translates the results into plain English.

## The Insight

We started by having AI scrape news websites. That was expensive (70% of a session's token budget in 3 runs) and shallow (rehashing what journalists already wrote).

The breakthrough: **flip the question.** Instead of asking "what should the AI read on behalf of the human?", ask "what data does the AI find genuinely easy to read that the human would never look at?"

The answer: machine-native data sources -- package downloads, repo metrics, container pulls, SEC filings, model pricing. All structured JSON, all free, all high-signal, all invisible to humans.

The AI reads data that's boring to humans, then translates the patterns into insight. **$0.06 per briefing containing original analysis no news site publishes.**

## How It Works

**Layer 1 -- FETCH (free, no AI needed)**

Two Python scripts hit 9 structured APIs and save the results as JSON:

- **PyPI** -- Python package download counts (adoption signal)
- **npm** -- JavaScript package download counts (different ecosystem, different preferences)
- **Docker Hub** -- container pull counts (production deployment signal)
- **GitHub** -- stars, forks, issues for key repos (velocity and health)
- **HuggingFace** -- trending AI models (community excitement)
- **SEC EDGAR** -- financial filings from NVIDIA, AMD, Microsoft, Google, Meta, Amazon (capital flow)
- **OpenRouter** -- real-time pricing for 232 AI models (competitive landscape)
- **arXiv** -- today's AI research papers (what's being studied)
- **GitHub Releases** -- changelogs from key AI projects (what shipped)

**Layer 2 -- REASON (~$0.06 per run)**

A two-pass AI pipeline:

1. **Haiku 4.5** (fast/cheap) scans all 300+ data points, identifies the 5-8 most important signals (~$0.01)
2. **Sonnet 4.6** (balanced) writes a ~1,000-word briefing explaining what the signals mean in plain language (~$0.05)

## Sample Output

From the first briefing this system produced:

> **Anthropic Is Building a Platform, Not Just a Model**
>
> 11 SDK releases in 13 days, with features shipping in deliberate sequence: filesystem memory tools, Bedrock authentication, Managed Agents, Bedrock Mantle client, beta advisor tool. This is not a normal release cadence. This is a platform buildout happening in public.

> **Ollama Crossed nvidia/cuda on Docker**
>
> Ollama has 121M Docker pulls vs nvidia/cuda at 106M. Docker pull counts are a production signal, not a hobbyist signal. Local inference is no longer an experiment.

> **Pricing Has Collapsed -- But Not Uniformly**
>
> The realistic market price for capable AI reasoning is now $1-3/M input tokens. At that price, a complex agent task costs $0.10-$0.30. The economics of agentic applications have genuinely changed.

None of this exists in any news article. It was derived from structured API data no human would read voluntarily.

## Quick Start

```bash
# Install dependencies
pip install feedparser anthropic python-dotenv

# Create .env file with your Anthropic API key
echo "ANTHROPIC_API_KEY=your-key-here" > .env

# Run the full pipeline
python fetch_feeds.py          # arXiv + GitHub releases (free)
python fetch_apis.py           # 7 API sources (free)
python reason_llm.py           # Haiku scan + Sonnet briefing (~$0.06)
```

Output lands in `output/` -- a markdown briefing ready to read.

There is also a rule-based reasoning script (`reason.py`) that produces a table-formatted briefing without any AI calls -- completely free, useful for quick checks.

## Project Structure

```
fetch_feeds.py        -- Layer 1: arXiv RSS + 5 GitHub releases Atom feeds
fetch_apis.py         -- Layer 1: PyPI, npm, Docker Hub, GitHub, HuggingFace, SEC EDGAR, OpenRouter
reason.py             -- Layer 2: rule-based briefing (tables + trend arrows, free)
reason_llm.py         -- Layer 2: LLM-powered briefing (Haiku + Sonnet, ~$0.06/run)
requirements.txt      -- dependencies
.env                  -- your API key (gitignored, never committed)
PRD.md                -- product requirements and roadmap
TUTORIAL.md           -- detailed tutorial for technical and non-technical readers
```

## Cost Comparison

- **AI scraping news websites** -- ~$1-5 per run, rehashes existing journalism
- **Human reading news manually** -- 1-2 hours per day, subjective, limited sources
- **This system** -- $0.06 per run, original analysis from 9 machine-native sources

## What is Next

- **History tracking** -- store metrics between runs to show week-over-week deltas
- **Scheduled automation** -- daily briefings via Claude Code scheduled tasks, emailed via Gmail
- **Multi-agent architecture** -- scanner agents, deep-dive agents, synthesis agents working in parallel
- **More sources** -- Semantic Scholar (citation velocity), LMSYS (model rankings), cloud GPU pricing

## Framework

This project uses Jensen Huang's "AI-Cake" framework to organize the AI industry into layers: Energy, Chips, Infrastructure, Models, Applications. Each data source maps to one or more layers, making it possible to see how changes cascade through the stack.

## Learn More

See [TUTORIAL.md](TUTORIAL.md) for a detailed walkthrough -- including getting-started prompts (natural language, no code required), a full glossary of all data sources and AI terms, and guidance on adapting this system for other industries.

## Background

Built in a single session (April 13, 2026) as a collaboration between a human learning AI engineering and Claude. The initial approach (scraping news) failed. The pivot to machine-native data sources -- letting the AI lead on what it finds genuinely useful to read -- produced something better than either human or AI would have built alone.

## License

MIT
