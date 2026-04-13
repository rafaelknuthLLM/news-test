# PRD: AI-Native Intelligence System

## The Premise

Most AI industry coverage is built for human consumption: blog posts, news articles, Twitter threads, conference talks. An AI reading these sources is doing the equivalent of a human reading binary -- technically possible, but fighting the format.

Meanwhile, the infrastructure underneath the AI industry -- package registries, version control systems, model hubs, financial filings, patent databases, benchmark leaderboards -- emits structured, machine-readable data that contains high-signal intelligence about where the industry is heading. Humans ignore this data because it's boring at face value. An AI can read it natively and surface patterns no journalist covers.

**The inversion:** instead of an AI struggling to read human news, an AI reads machine-native data and translates it into human insight.

## What We're Building

A weekly intelligence briefing about the AI industry (framed through Jensen Huang's "AI-Cake": Compute/Hardware, System Software, Platform Software, Applications) -- sourced entirely from structured APIs and machine-readable data. No web scraping. No HTML parsing. No token-heavy web search.

The human (Rafael) reads the briefing. The AI picks the sources, processes the data, identifies the signals.

## Data Sources -- Organized by Signal Type

### 1. ADOPTION -- Who's actually using what?

This is the most underrated intelligence source. Blog posts tell you what companies *announce*. Download counts tell you what developers *use*. These often diverge.

| Source | API | What it reveals | Cost |
|---|---|---|---|
| **PyPI** (Python packages) | `pypi.org/pypi/{pkg}/json`, `pypistats.org/api/` | Weekly/monthly downloads, version history, dependency chains for AI packages | Free |
| **npm** (JavaScript packages) | `registry.npmjs.org/{pkg}` + `api.npmjs.org/downloads/` | Same for JS ecosystem (@anthropic-ai/sdk, openai, langchain.js, vercel ai) | Free |
| **Docker Hub** | `hub.docker.com/v2/repositories/{ns}/{repo}` | Container pull counts for nvidia/cuda, pytorch/pytorch, vllm/vllm-openai -- shows what's running in production, not just installed | Free |
| **HuggingFace Hub** | `huggingface.co/api/models`, `/api/datasets`, `/api/spaces` | Model downloads, trending models, new datasets, popular demos | Free |
| **libraries.io** | `libraries.io/api/` | Cross-ecosystem dependency tracking -- if 200 packages add `anthropic` as a dependency in one month, that's an adoption wave | Free (API key) |

**Why this matters:** When CrewAI has 1.4M weekly downloads but Autogen has 36K, that's not an opinion -- that's the market speaking. When `langchain` downloads nearly match `openai`, it tells you the orchestration layer is as important as the model layer. No blog post gives you this clarity.

### 2. VELOCITY -- How fast are things moving?

Release cadence and commit activity tell you where companies are investing engineering effort right now. A repo with 8 releases in 7 days is in sprint mode. A repo with no commits in 3 weeks is in maintenance mode or trouble.

| Source | API | What it reveals | Cost |
|---|---|---|---|
| **GitHub REST/GraphQL** | `api.github.com/repos/{owner}/{repo}` | Stars, forks, issues, commit frequency, contributor count, release cadence | Free (5,000 req/hr authenticated) |
| **GitHub Releases Atom** | `github.com/{owner}/{repo}/releases.atom` | Changelogs, version bumps, feature announcements | Free |
| **GitHub Trending** | `github.com/trending` (needs parsing) or third-party APIs | What's gaining momentum this week across all of GitHub | Varies |
| **Changelog databases** | `changelogs.md`, `keepachangelog.com` | Aggregated changelogs across projects | Free |

**Why this matters:** Claude Code went from 0 to 113K stars in 14 months. That trajectory, visible in the GitHub API, tells you more about product-market fit than any press release.

### 3. RESEARCH -- What's being studied?

arXiv is the de facto preprint server for AI research. But the raw firehose (289 papers/day in cs.AI alone) is noise without filtering. The real signal comes from metadata: who wrote it, who's citing it, and which papers are gaining traction.

| Source | API | What it reveals | Cost |
|---|---|---|---|
| **arXiv API** | `export.arxiv.org/api/query` | Papers with full metadata: authors, affiliations, categories, abstracts | Free |
| **Semantic Scholar** | `api.semanticscholar.org/graph/v1/` | Citation counts, influential citations, author networks, paper embeddings | Free (API key, 100 req/sec) |
| **Papers With Code** | `paperswithcode.com/api/v1/` | Links papers to their code implementations, benchmarks, datasets | Free |
| **OpenReview** | `api2.openreview.net/` | Conference submissions, peer reviews (NeurIPS, ICLR, ICML) -- see what's being accepted before it's published | Free |

**Why this matters:** A paper cited 50 times in its first week is a different signal than one cited 50 times in 2 years. Semantic Scholar gives us that velocity. Papers With Code tells us which research is actually getting implemented, not just published.

### 4. CAPITAL -- Where is money flowing?

This is where it gets interesting. Financial filings are structured data that humans find boring but that contain concrete signals about strategic direction.

| Source | API | What it reveals | Cost |
|---|---|---|---|
| **SEC EDGAR** | `efts.sec.gov/LATEST/search-index?q=` | 10-K, 10-Q, 8-K filings -- mentions of "AI", "GPU", "machine learning" in earnings reports, capex figures, risk factors | Free |
| **Federal Register** | `federalregister.gov/api/v1/` | US government AI policy, executive orders, procurement rules | Free |
| **EU Publications** | `eur-lex.europa.eu/` (SPARQL endpoint) | EU AI Act implementation, regulatory timelines | Free |
| **Crunchbase** (limited) | `api.crunchbase.com/` | Funding rounds, M&A, valuations for AI companies | Paid (basic free tier) |
| **USPTO Patents** | `developer.uspto.gov/api-catalog` | Patent filings show R&D direction 2-3 years ahead of products | Free |

**Why this matters:** When NVIDIA's 10-K shows data center revenue growing 400% year-over-year, that's the hardware layer of the AI-Cake in hard numbers. When an 8-K filing reveals a $2B investment in a partner (like NVIDIA-Marvell), that's a supply chain signal. The Federal Register tells you what the US government is about to regulate before it becomes news.

### 5. INFRASTRUCTURE -- What's being built?

The physical and digital infrastructure underneath AI is visible through surprisingly accessible data.

| Source | API | What it reveals | Cost |
|---|---|---|---|
| **Cloud pricing APIs** | AWS, GCP, Azure pricing endpoints | GPU instance pricing changes = supply/demand dynamics. New instance types = new hardware availability. Price drops = commoditization. | Free |
| **NVIDIA driver/CUDA releases** | Release notes (structured) | CUDA version support tells you which GPUs are being prioritized. Driver updates signal new hardware coming. | Free |
| **Benchmark leaderboards** | LMSYS Chatbot Arena, Open LLM Leaderboard, SWE-bench | Model rankings with ELO scores, updated continuously. Structured JSON/CSV. | Free |
| **Certificate Transparency logs** | `crt.sh/?q=` | New subdomains registered by AI companies (api.newproduct.anthropic.com appearing before any announcement) | Free |

**Why this matters:** If AWS drops the price of p5 instances by 30%, that signals GPU supply is loosening -- which affects every layer of the AI-Cake. If a new subdomain appears in Anthropic's CT logs, something is launching soon.

### 6. TALENT -- Where are people going?

Harder to access via API, but some signals are available.

| Source | API | What it reveals | Cost |
|---|---|---|---|
| **GitHub contributor graphs** | `api.github.com/repos/{owner}/{repo}/contributors` | Who's contributing to which projects. If a Google engineer starts committing to an Anthropic repo, that's a signal. | Free |
| **Company career pages** (structured) | Many use Greenhouse/Lever APIs with JSON endpoints | What roles are being hired for. If NVIDIA posts 50 "AI Safety" roles, that's a strategic shift. | Free (varies) |
| **arXiv author affiliations** | Via Semantic Scholar API | Researchers moving between institutions/companies | Free |

**Why this matters:** Talent movement is a leading indicator. When a company starts hiring heavily in a new area, the product follows 12-18 months later.

## What We Already Built (v0.1)

| Component | Status | Sources |
|---|---|---|
| `fetch_feeds.py` | Working | arXiv RSS (289 papers/day), 5 GitHub releases feeds |
| `fetch_apis.py` | Working | PyPI stats (10 packages), GitHub repo metrics (8 repos), HuggingFace trending (20 models) |
| `reason.py` | Working | Unified briefing with Signals + Releases + Research sections |

## Proposed Next Steps -- In Priority Order

### Phase 1: Deepen what's working (low effort, high signal)

- **Add npm stats** for JS SDK packages (anthropic, openai) -- same pattern as PyPI
- **Add Docker Hub pulls** for key AI containers -- production deployment signal
- **Add Semantic Scholar** for citation velocity on arXiv papers -- separates important research from noise
- **Switch arXiv from RSS to API** -- richer metadata (author affiliations, full abstracts)
- **Add week-over-week deltas** in reason.py -- "anthropic downloads up 12% this week" is more useful than raw numbers

### Phase 2: New signal types (medium effort, unique insight)

- **SEC EDGAR integration** -- monitor AI-related filings from NVIDIA, Google, Microsoft, Meta, Amazon
- **Benchmark leaderboard tracking** -- LMSYS Chatbot Arena rankings over time
- **Cloud GPU pricing** -- track p5/a100/h100 instance pricing across AWS, GCP, Azure
- **libraries.io dependency tracking** -- who depends on which AI packages

### Phase 3: Advanced signals (higher effort, differentiated intelligence)

- **Patent filing analysis** -- USPTO AI patent trends by company
- **Certificate transparency monitoring** -- early detection of new AI product launches
- **GitHub contributor network analysis** -- talent flow between companies
- **Federal Register + EU regulatory tracking** -- policy signals before they become news

## Design Principles

1. **Machine-native sources only.** If it requires a web browser to access, it's not for us. JSON APIs, Atom feeds, SPARQL endpoints, CSV downloads.
2. **Signals over stories.** We want state changes, not narratives. "Downloads up 40%" beats "Company X is gaining momentum."
3. **Cheap to fetch, valuable to interpret.** Layer 1 (fetch) should cost nearly nothing. Layer 2 (reason) is where intelligence happens.
4. **The AI leads on sources, the human leads on decisions.** The AI identifies what's changing. The human decides what it means for their work.
5. **Every artifact is software.** All outputs are structured, versioned, and machine-consumable for future automation.
