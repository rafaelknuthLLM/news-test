Last night I tried to build an AI-powered news aggregator that would search the web for AI industry news, summarize it, and email me a daily briefing. It didn't work -- three test runs burned through 70% of the session's token budget, and the output was shallow because it was essentially rehashing what tech journalists had already written.

What turned the project around was a simple question I asked Claude: "What data do you actually find easy to read that I, as a human, would never look at?" The answer was package download counts, Docker container pulls, GitHub repository metrics, SEC filings, model pricing APIs, HuggingFace trending data, and arXiv paper metadata. All of it is structured JSON, all of it is available through free public APIs, and all of it is completely boring to read as a human.

When an AI reads all of these sources at once -- PyPI and npm download statistics, Docker Hub pulls, SEC filings from NVIDIA, AMD, Microsoft, Google, Meta, and Amazon, real-time pricing across 232 AI models, and 289 research papers from arXiv -- it finds patterns that no journalist covers. For example, the briefing surfaced that Anthropic shipped 11 SDK releases in 13 days, and reading the changelogs in sequence reveals a platform being built in public. It also caught that Ollama has passed nvidia/cuda in Docker pulls (121M vs 106M), which means local AI inference is no longer experimental. And it found that Anthropic's JavaScript SDK is growing at 23% week-over-week, faster than the Python SDK, which tells you the JavaScript developer community is adopting it at a different pace than the traditional ML community.

None of this analysis exists in any news article, because it was derived entirely from structured data that is publicly available but that no human reads voluntarily.

The whole pipeline costs about $0.06 per briefing -- a cheap model scans the raw data for signals, then a more capable model writes the analysis in plain language. The data fetching itself is completely free.

The real lesson from this project wasn't technical. I kept trying to make the AI do what I do as a human, which is read articles and websites. That turned out to be expensive and mediocre. When I let the AI lead on what it is genuinely good at -- reading structured data across many sources simultaneously and spotting cross-references -- the output got dramatically better and the cost dropped by a factor of 100.

I open-sourced the project, including a detailed tutorial with a glossary for non-technical readers.

[link to Gist]
