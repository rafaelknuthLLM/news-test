#!/usr/bin/env python3
"""
AI-Cake News Aggregator -- Layer 1 (FETCH: APIs)
Pulls structured data from machine-native APIs. No web search. No scraping.
"""

import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# --- Watchlists --------------------------------------------------------------

PYPI_PACKAGES = [
    "anthropic",
    "openai",
    "langchain",
    "langchain-core",
    "transformers",
    "crewai",
    "autogen",
    "llama-index",
    "vllm",
    "together",
]

NPM_PACKAGES = [
    "@anthropic-ai/sdk",
    "openai",
    "langchain",
    "@langchain/core",
    "ai",              # Vercel AI SDK
    "@huggingface/inference",
]

DOCKER_IMAGES = [
    "nvidia/cuda",
    "pytorch/pytorch",
    "vllm/vllm-openai",
    "huggingface/transformers-pytorch-gpu",
    "ollama/ollama",
]

GITHUB_REPOS = [
    "anthropics/claude-code",
    "anthropics/anthropic-sdk-python",
    "openai/openai-python",
    "huggingface/transformers",
    "NVIDIA/TensorRT",
    "langchain-ai/langchain",
    "crewAIInc/crewAI",
    "microsoft/autogen",
    "ollama/ollama",
    "vllm-project/vllm",
]

HF_MODEL_LIMIT = 20

USER_AGENT = "AI-Cake-Fetcher/1.0 (+https://github.com/rafaelknuthLLM/news-test)"

# --- Helpers -----------------------------------------------------------------


def api_get(url):
    """Fetch JSON from a URL. Returns (data, error_msg)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read()), None
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        return None, str(e)


# --- Fetchers ----------------------------------------------------------------


def fetch_pypi(packages):
    """Fetch download stats and latest version for each package."""
    results = []
    for i, pkg in enumerate(packages):
        if i > 0:
            time.sleep(1)  # pypistats.org rate-limits rapid requests
        stats, err = api_get(f"https://pypistats.org/api/packages/{pkg}/recent")
        meta, meta_err = api_get(f"https://pypi.org/pypi/{pkg}/json")

        entry = {"package": pkg}

        if err:
            entry["error"] = err
            entry["downloads"] = None
        else:
            entry["downloads"] = stats.get("data", {})

        if meta_err:
            entry["latest_version"] = None
            entry["latest_date"] = None
        else:
            entry["latest_version"] = meta["info"]["version"]
            releases = meta.get("releases", {})
            latest_files = releases.get(meta["info"]["version"], [])
            if latest_files:
                entry["latest_date"] = latest_files[0].get("upload_time", "")[:10]
            else:
                entry["latest_date"] = None

        ok = "OK" if not err else "FAIL"
        print(f"  {ok:>4}  PyPI: {pkg}")
        results.append(entry)

    return results


def fetch_npm(packages):
    """Fetch download stats for npm packages."""
    results = []
    for pkg in packages:
        # npm API uses URL-encoded package names for scoped packages
        encoded = pkg.replace("/", "%2F")
        week_data, week_err = api_get(
            f"https://api.npmjs.org/downloads/point/last-week/{encoded}"
        )
        month_data, month_err = api_get(
            f"https://api.npmjs.org/downloads/point/last-month/{encoded}"
        )

        entry = {"package": pkg}

        if week_err and month_err:
            entry["error"] = week_err
            entry["downloads"] = None
            print(f"  FAIL  npm: {pkg}")
        else:
            entry["downloads"] = {
                "last_week": week_data.get("downloads", 0) if week_data else None,
                "last_month": month_data.get("downloads", 0) if month_data else None,
            }
            print(f"    OK  npm: {pkg}")

        results.append(entry)

    return results


def fetch_docker(images):
    """Fetch pull counts from Docker Hub."""
    results = []
    for image in images:
        data, err = api_get(f"https://hub.docker.com/v2/repositories/{image}/")

        if err:
            print(f"  FAIL  Docker: {image}: {err}")
            results.append({"image": image, "error": err})
            continue

        entry = {
            "image": image,
            "pull_count": data.get("pull_count", 0),
            "star_count": data.get("star_count", 0),
            "last_updated": data.get("last_updated", "")[:10],
        }
        print(f"    OK  Docker: {image}")
        results.append(entry)

    return results


def fetch_github(repos):
    """Fetch repo stats for each repo."""
    results = []
    for repo in repos:
        data, err = api_get(f"https://api.github.com/repos/{repo}")

        if err:
            print(f"  FAIL  GitHub: {repo}: {err}")
            results.append({"repo": repo, "error": err})
            continue

        entry = {
            "repo": repo,
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "open_issues": data.get("open_issues_count", 0),
            "watchers": data.get("subscribers_count", 0),
            "pushed_at": data.get("pushed_at", ""),
            "created_at": data.get("created_at", "")[:10],
        }
        print(f"    OK  GitHub: {repo}")
        results.append(entry)

    return results


def fetch_huggingface(limit):
    """Fetch trending models from HuggingFace."""
    data, err = api_get(
        f"https://huggingface.co/api/models?sort=likes7d&direction=-1&limit={limit}"
    )
    if err:
        print(f"  FAIL  HuggingFace models: {err}")
        return []

    results = []
    for m in data:
        results.append({
            "model_id": m.get("id", "unknown"),
            "downloads": m.get("downloads", 0),
            "likes": m.get("likes", 0),
            "pipeline_tag": m.get("pipeline_tag", "n/a"),
            "created_at": m.get("createdAt", "")[:10] if m.get("createdAt") else None,
        })

    print(f"    OK  HuggingFace: {len(results)} trending models")
    return results


# --- Main --------------------------------------------------------------------


def main():
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d_%H%M")

    print("Fetching PyPI stats...")
    pypi = fetch_pypi(PYPI_PACKAGES)

    print("Fetching npm stats...")
    npm = fetch_npm(NPM_PACKAGES)

    print("Fetching Docker Hub stats...")
    docker = fetch_docker(DOCKER_IMAGES)

    print("Fetching GitHub stats...")
    github = fetch_github(GITHUB_REPOS)

    print("Fetching HuggingFace trending...")
    huggingface = fetch_huggingface(HF_MODEL_LIMIT)

    output = {
        "meta": {
            "generated_at": now.isoformat(),
            "sources": {
                "pypi_packages": len(PYPI_PACKAGES),
                "npm_packages": len(NPM_PACKAGES),
                "docker_images": len(DOCKER_IMAGES),
                "github_repos": len(GITHUB_REPOS),
                "huggingface_models": len(huggingface),
            },
        },
        "pypi": pypi,
        "npm": npm,
        "docker": docker,
        "github": github,
        "huggingface": huggingface,
    }

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f"ai_cake_apis_{timestamp}.json"
    output_file.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    total = len(pypi) + len(npm) + len(docker) + len(github) + len(huggingface)
    print(f"\n  Done: {total} data points across 5 sources")
    print(f"  Output: {output_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
