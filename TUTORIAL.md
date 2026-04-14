# AI-Cake Intelligence System -- Tutorial

## What This Project Is

This is an AI-powered intelligence system that monitors the artificial intelligence industry and produces weekly briefings. It tracks who is building what, how fast things are moving, what researchers are studying, where money is flowing, and how much AI models cost.

The system was built in a single evening session (April 13, 2026) as a collaboration between a human (a solo founder learning AI engineering) and an AI (Claude). It started as a simple news aggregator and evolved into something more interesting -- which is the real story.

## The Problem

If you want to stay informed about the AI industry, you have two options -- and both are bad:

**Option A: Read the news.** Blog posts, Twitter threads, tech journalism. This is written for humans, by humans. It's narrative-driven, opinion-heavy, and covers whatever got the most clicks. It tells you what companies *want* you to know, not necessarily what's actually happening.

**Option B: Go to the source.** Read GitHub changelogs, scan arXiv papers, check download statistics, review SEC filings. This is where the real signals live -- but the data is scattered across dozens of platforms, formatted for machines, and mind-numbingly boring to read as a human.

Most people choose Option A because Option B is impractical. This project automates Option B and translates the results into plain English.

## The Key Insight

This project started as Option A -- we tried to have AI scrape news websites and summarize them. That approach was expensive (three test runs burned through 70% of the session's token budget (Claude Max 5x plan)) and produced shallow output (it was essentially rehashing what journalists had already written).

The breakthrough came from flipping the question:

> Instead of asking "what should the AI read on behalf of the human?", we asked "what data does the AI find genuinely easy to read that the human would never look at?"

The answer: **machine-native data sources**. Package download counts, repository metrics, container pull statistics, SEC filings, model pricing APIs. All of this data is:

- **Structured** (JSON, XML -- not messy HTML and JavaScript)
- **Free** (public APIs, no scraping required)
- **High-signal** (actual usage data, not marketing narratives)
- **Invisible to humans** (no journalist writes articles about PyPI download trends)

The AI reads this data natively -- it's the format AI was built for. Then it translates the patterns into a briefing that a human can understand and act on.

**The result:** $0.06 per briefing that contains original analysis no news site publishes.

## How It Works

The system has two layers, inspired by Linus Torvalds' advice: *"Get the data architecture right first, the logic follows."*

### Layer 1: FETCH (free, no AI needed)

Two Python scripts hit 9 structured data sources and save the results as JSON files. No AI tokens are consumed. The total data payload is about 50 kilobytes.

**What gets fetched:**

- **PyPI** (Python Package Index) -- How many developers downloaded each AI package this week -- the real adoption signal
- **npm** (Node Package Manager) -- Same for JavaScript developers -- a different community with different preferences
- **Docker Hub** -- How many times AI containers were pulled for production deployment -- not just installed, but actually used
- **GitHub** -- Stars, forks, open issues for key repos -- developer excitement and project health
- **HuggingFace** -- Which AI models are trending -- what the community is actually downloading and experimenting with
- **SEC EDGAR** -- Financial filings from NVIDIA, AMD, Microsoft, Google, Meta, Amazon -- where the big money is going
- **OpenRouter** -- Real-time pricing for 232 AI models across all major providers -- the competitive landscape
- **arXiv** -- Today's AI research papers -- what academics and corporate labs are publishing
- **GitHub Releases** -- Version-by-version changelogs from key AI projects -- what actually shipped this week

### Layer 2: REASON (costs ~$0.06 per run)

A two-pass AI pipeline reads the structured data and writes the briefing:

**Pass 1 -- Quick scan (Haiku, Anthropic's fast/cheap model):** Reads all 300+ data points and identifies the 5-8 most important signals -- things that changed, anomalies, trends, or patterns across sources. Cost: about $0.01.

**Pass 2 -- Deep synthesis (Sonnet, Anthropic's balanced model):** Takes the signals from Pass 1 plus the raw data, and writes a 1,000-word briefing that explains what the signals mean in plain language. Cost: about $0.05.

The system prompt (the "analysis framework" that tells the AI how to think about the data) is cached between runs, so repeated runs cost even less.

## What the Output Looks Like

Here is a real excerpt from the first briefing this system produced:

> **Anthropic Is Building a Platform, Not Just a Model**
>
> 11 SDK releases in 13 days, with features shipping in deliberate sequence: filesystem memory tools, Bedrock authentication, Managed Agents, Bedrock Mantle client, beta advisor tool.
>
> This is not a normal release cadence. This is a platform buildout happening in public. Read the changelog in order and you see the architecture emerge: Anthropic is constructing the scaffolding for autonomous, enterprise-deployable agents.

> **Ollama Crossed nvidia/cuda on Docker -- That's Not Nothing**
>
> Ollama has 121M Docker pulls vs nvidia/cuda at 106M. Docker pull counts are a production signal, not a hobbyist signal. You don't run Docker in production unless you're serious.

> **Pricing Has Collapsed -- But Not Uniformly**
>
> OpenAI o1-pro at $150/M input is 50-75x more expensive than DeepSeek at $0.70/M. The realistic market price for capable reasoning is now $1-3/M input tokens. At that price, a complex agent task costs $0.10-$0.30. The economics of agentic applications have genuinely changed.

None of this analysis exists in any news article. It was derived entirely from structured API data that no human would read voluntarily.

## The Economics

- **AI scraping news websites** -- ~$1-5 per run (token-heavy), rehashes existing journalism
- **Human reading news manually** -- 1-2 hours per day, subjective, limited sources
- **This system** -- $0.06 per run, original analysis from 9 machine-native sources

At $0.06 per run, you could generate a briefing every single day for a month and spend $1.80.

## Getting Started

You do not need to write code to use this system. If you are working with Claude Code (Anthropic's AI coding assistant), you can describe what you want in plain English. Here are the prompts that built this project:

### Prompt 1: Build the fetch layer

> "Build a Python script that fetches data from these APIs and saves the results as JSON: PyPI download stats for anthropic, openai, langchain, transformers. GitHub repo metrics for anthropics/claude-code, openai/openai-python. HuggingFace trending models. Keep it simple -- one file, one dependency if needed."

### Prompt 2: Add more data sources

> "Add npm download stats, Docker Hub pull counts, SEC EDGAR filings for NVIDIA/AMD/Microsoft/Google/Meta/Amazon, and OpenRouter model pricing to the fetch script. All of these are free JSON APIs."

### Prompt 3: Build the reasoning layer

> "Write a script that reads the JSON data from the fetch scripts, sends it to Claude Haiku for a quick signal scan, then to Claude Sonnet for a full briefing. Use prompt caching for the system prompt. Store the API key in a .env file."

### Prompt 4: Customize the analysis

> "Update the system prompt to focus on [your industry/interest]. I care about [specific companies, technologies, or trends]. The audience is [describe yourself -- technical level, role, what you need to make decisions]."

### Prompt 5: Automate it

> "Set up a scheduled task that runs the full pipeline daily, commits the briefing to the GitHub repo, and emails it to me."

## What Data Sources to Choose

The sources in this project are tailored to AI industry monitoring, but the pattern works for any industry where machine-readable data exists. Here are questions to help you pick sources:

- **Who is adopting what?** -- Look for package registries, app stores, download counters
- **How fast are things moving?** -- Look for version control systems, release feeds, commit activity
- **Where is money going?** -- Look for SEC filings, patent databases, funding announcements
- **What is being researched?** -- Look for preprint servers, conference proceedings, benchmark leaderboards
- **What does it cost?** -- Look for pricing APIs, marketplace listings, cloud provider rate cards

The key principle: **if the data comes from a structured API that returns JSON, it is cheap for AI to read. If it requires a web browser to access, it is expensive.**

## What is Next

### Automation

The pipeline currently runs manually from the command line. The next step is to deploy it as a scheduled task using Claude Code's built-in scheduling feature. This means:

- The pipeline runs automatically (daily or weekly)
- Results are committed to the GitHub repository
- A briefing is emailed to you
- No manual intervention required
- Covered under Anthropic's Max plan (no additional cost beyond the ~$0.06 API calls)

### History and Trends

Currently, each briefing is a snapshot -- it shows where things are right now. With a simple history file that stores key metrics from each run, future briefings could show **how things are changing**: "Anthropic's weekly downloads grew 15% compared to last week" is more useful than "Anthropic has 23 million weekly downloads."

### Multi-Agent Architecture

Anthropic launched Claude Managed Agents in April 2026, which enables multiple AI agents to work in parallel on different tasks. Future versions of this system could use:

- **Scanner agents** that each specialize in one data source (one for GitHub, one for SEC filings, one for arXiv)
- **Deep-dive agents** that investigate specific signals flagged by the scanner ("NVIDIA filed an 8-K -- what does it say?")
- **Synthesis agents** that combine findings from all scanners into a single briefing

This is the same pattern that newsrooms use (reporters, editors, analysts) -- but with AI agents that can process hundreds of data points in seconds.

### Additional Data Sources

The system is designed to be expandable. Sources on the roadmap include:

- **Semantic Scholar** -- citation velocity for research papers (which papers are being cited fastest)
- **LMSYS Chatbot Arena** -- live model rankings based on blind human evaluations
- **Cloud GPU pricing** -- tracking instance costs across AWS, Google Cloud, and Azure
- **libraries.io** -- dependency graphs showing which packages depend on which others
- **Patent databases** -- tracking AI patent filings by company
- **Certificate transparency logs** -- detecting new product launches before they are announced

## Frequently Asked Questions

**Does this replace reading the news?**
No. It supplements it with a different kind of information. News tells you narratives and opinions. This system tells you what actually happened in the data. Both are valuable. But if you only have time for one, the data is harder to get elsewhere.

**Do I need to know how to code?**
Not to use the system -- you can ask Claude Code to build and run it for you using natural language prompts (see "Getting Started" above). To modify the data sources or analysis, some familiarity with Python helps, but Claude Code can handle the implementation.

**How much does it cost to run?**
About $0.06 per briefing using the Anthropic API (Haiku + Sonnet). The data fetching itself is completely free. If you automate it as a scheduled task under Anthropic's Max plan, the only incremental cost is the API calls for the reasoning layer.

**Can I use this for a different industry?**
Yes. The architecture (fetch structured data from APIs, then use AI to interpret it) works for any domain where machine-readable data exists. Finance, healthcare, supply chain, cybersecurity -- any industry with public APIs, registries, or filing systems.

**Is the data reliable?**
The data comes directly from primary sources (PyPI, GitHub, Docker Hub, SEC, etc.) -- not from third-party aggregators or news reports. It is as reliable as the source itself. The system also tracks which fetches succeeded and which failed, so you always know if data is missing.

**Why two AI passes instead of one?**
Cost efficiency. Haiku (the cheap, fast model) does the heavy lifting of scanning 300+ data points and classifying what matters. Sonnet (the more capable, more expensive model) only processes the pre-classified signals. This keeps the total cost under $0.10 per run while maintaining high output quality.

---

## Glossary

### Data Sources

**arXiv**
A free, open-access repository where researchers publish academic papers (called "preprints") before they go through formal peer review. It is the primary place where AI research is shared with the world, often months before it appears in journals or conferences. The cs.AI section covers artificial intelligence research specifically. Think of it as the "early release" channel for scientific papers.
Website: [arxiv.org](https://arxiv.org)

**Docker Hub**
A cloud-based registry where developers store and share "container images" -- pre-packaged software environments that can run anywhere. When a company wants to deploy an AI model in production, they often package it as a Docker container. The number of times a container has been "pulled" (downloaded for use) is a strong signal of real-world production adoption -- unlike stars or likes, you only pull a Docker image when you intend to actually run it.
Website: [hub.docker.com](https://hub.docker.com)

**GitHub**
The world's largest platform for hosting and collaborating on software code. Developers use it to share code, track bugs, and coordinate work. Key metrics include "stars" (bookmarks indicating interest), "forks" (copies made by others to build upon), and "open issues" (reported bugs or feature requests). GitHub also hosts "releases" -- versioned snapshots of software with changelogs describing what changed.
Website: [github.com](https://github.com)

**HuggingFace Hub**
A platform with over 2 million AI models, 500,000 datasets, and 1 million demo applications, all publicly available. It functions as the central marketplace for the open-source AI community. When a new AI model is released, HuggingFace download counts and "likes" indicate how much real interest and adoption it is generating. Trending models on HuggingFace tell you what the AI community is excited about right now.
Website: [huggingface.co](https://huggingface.co)

**npm (Node Package Manager)**
The package registry for JavaScript, one of the world's most popular programming languages (especially for web applications). Like PyPI for Python, npm download counts tell you which JavaScript libraries developers are actually using. Comparing adoption between PyPI and npm reveals differences between the Python community (more data science and backend) and the JavaScript community (more web apps and edge computing).
Website: [npmjs.com](https://www.npmjs.com)

**OpenRouter**
A unified marketplace that gives developers access to over 350 AI models from multiple providers (Anthropic, OpenAI, Google, Meta, and others) through a single interface. It publishes real-time pricing for all models, making it a valuable source of competitive intelligence. By comparing prices across providers, you can see how the model market is stratifying -- who charges premium prices, who is competing on cost, and where the "commodity" price level sits.
Website: [openrouter.ai](https://openrouter.ai)

**PyPI (Python Package Index)**
The official repository for Python software packages, containing over 600,000 packages. When a developer types `pip install anthropic`, they are downloading the Anthropic package from PyPI. Weekly and monthly download counts reveal actual developer adoption -- not interest, not hype, but real usage. If a package's downloads spike 40% in a week, something real happened (a new feature, a viral tutorial, a competitor's outage).
Website: [pypi.org](https://pypi.org)

**SEC EDGAR**
The Electronic Data Gathering, Analysis, and Retrieval system operated by the U.S. Securities and Exchange Commission. Every public company in the United States must file financial documents here -- annual reports (10-K), quarterly reports (10-Q), and material event disclosures (8-K). These filings contain concrete numbers about revenue, expenses, investments, partnerships, and strategic direction. Unlike press releases, companies are legally required to be accurate in SEC filings. EDGAR is free and requires no registration.
Website: [sec.gov/edgar](https://www.sec.gov/cgi-bin/browse-edgar)

### AI Industry Terms

**Agentic AI / AI Agents**
AI systems that can take actions autonomously -- not just answer questions, but actually do things like write code, search the web, read files, call APIs, and make decisions about what to do next. An "agentic loop" is when an AI repeatedly thinks, acts, observes the result, and decides its next action. This is different from a simple chatbot that just responds to prompts.

**AI-Cake (Jensen Huang's Framework)**
A framework described by NVIDIA CEO Jensen Huang at the World Economic Forum in Davos (January 2026) that breaks the AI industry into five layers, like a cake:

1. **Energy** -- the power needed to run AI data centers (the "binding constraint")
2. **Chips** -- semiconductors and GPUs that perform AI computations (NVIDIA, AMD, TSMC)
3. **Infrastructure** -- cloud data centers, networking, and storage
4. **Models** -- the AI software itself (Claude, GPT, Gemma, Llama)
5. **Applications** -- products and services built on top of AI models

Investment at the top (applications) creates demand that cascades down through all layers. This project uses a simplified four-layer version: Hardware, System Software, Platform Software, Applications.

**Context Window**
The amount of text an AI model can process in a single conversation, measured in "tokens" (roughly 4 characters per token). A model with a 1,000,000-token context window can read about 750,000 words at once -- roughly 10 full-length novels. Larger context windows allow AI to work with more information simultaneously.

**LLM (Large Language Model)**
The type of AI that powers systems like Claude, ChatGPT, and Gemini. These models are trained on vast amounts of text and can generate human-like responses, analyze documents, write code, and reason about complex problems. "Large" refers to the number of parameters (internal settings) -- modern LLMs have billions to trillions of parameters.

**Prompt Caching**
A cost-saving technique where parts of the instructions sent to an AI model are stored ("cached") so they do not need to be resent and re-processed on subsequent calls. This system caches the analysis framework (the "system prompt") so that each briefing run only pays full price for the new data, not for the instructions that stay the same every time. Prompt caching can reduce costs by up to 90% for the cached portion.

**Quantization**
A technique for making AI models smaller and faster by reducing the precision of their internal numbers (for example, from 32-bit to 4-bit). Quantized models run on less powerful hardware (including consumer laptops) with minimal quality loss. When you see model names with "GGUF", "4-bit", or "quantized" on HuggingFace, these are community-created smaller versions of larger models.

**RAG (Retrieval-Augmented Generation)**
A pattern where an AI model looks up relevant information from an external source before generating its response, rather than relying solely on what it learned during training. This project is essentially a RAG data source -- it gathers structured information that an AI can reference when producing briefings.

**Token**
The basic unit of text that AI models process. Roughly 4 characters or 0.75 words per token in English. AI model pricing is measured in cost per million tokens. When this project says a briefing costs "$0.06", that is based on the total number of tokens sent to and received from the AI models.

---

*Built in a single session on April 13, 2026. The entire project -- from first prompt to working pipeline -- took about 6 hours of collaborative work between a human and Claude.*

*Repository: [github.com/rafaelknuthLLM/news-test](https://github.com/rafaelknuthLLM/news-test)*
