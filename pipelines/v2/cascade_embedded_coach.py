#!/usr/bin/env python3
"""
AI-Cake Cascade Pipeline -- Orchestrator with full process logging.

Runs the three-agent cascade (tutor -> analyst -> diver) on GitHub release data.
Every step is logged with timestamps, agent attribution, inputs, outputs, and errors.

Deterministic steps (API calls, calculations) run in Python.
Probabilistic steps (interpretation, analysis) run through the Anthropic API.
"""

import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import anthropic

# --- Config ------------------------------------------------------------------

SONNET = "claude-sonnet-4-6"
OUTPUT_DIR = Path(__file__).parent / "output"
AGENTS_DIR = Path(__file__).parent / ".claude" / "agents" / "v2_04152026"
REPO = "anthropics/claude-code"
RELEASES_COUNT = 5

# --- Process log -------------------------------------------------------------

process_log = []


def log_step(step_type, action, status="ok", details=None, agent=None, model=None,
             input_file=None, output_file=None, tokens_in=None, tokens_out=None, error=None):
    """Append a step to the process log."""
    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "type": step_type,
        "action": action,
        "status": status,
    }
    if agent:
        entry["agent"] = agent
    if model:
        entry["model"] = model
    if input_file:
        entry["input_file"] = input_file
    if output_file:
        entry["output_file"] = output_file
    if tokens_in is not None:
        entry["tokens_in"] = tokens_in
    if tokens_out is not None:
        entry["tokens_out"] = tokens_out
    if details:
        entry["details"] = details
    if error:
        entry["error"] = error
        entry["status"] = "error"
    process_log.append(entry)

    # Print to console
    icon = "OK" if status == "ok" else "FAIL" if status == "error" else "..."
    agent_str = f" [{agent}]" if agent else ""
    print(f"  [{entry['timestamp'][11:19]}] {icon:>4} {step_type:>15}{agent_str}: {action}")


# --- Helpers -----------------------------------------------------------------


def load_agent_prompt(name):
    """Load an agent's prompt from its markdown file."""
    path = AGENTS_DIR / f"{name}.md"
    text = path.read_text(encoding="utf-8")
    # Split frontmatter from body
    parts = text.split("---", 2)
    if len(parts) >= 3:
        return parts[2].strip()
    return text


def call_agent(client, agent_name, model, system_prompt, user_content, input_file=None, output_file=None):
    """Call an agent via the Anthropic API and log the step."""
    log_step("AGENT", f"{agent_name} started", status="running", agent=agent_name,
             model=model, input_file=input_file)

    start = time.time()
    try:
        response = client.messages.create(
            model=model,
            max_tokens=4000,
            system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user_content}],
        )
        duration = round(time.time() - start, 1)
        text = response.content[0].text
        tokens_in = response.usage.input_tokens
        tokens_out = response.usage.output_tokens

        log_step("AGENT", f"{agent_name} completed ({duration}s)", status="ok",
                 agent=agent_name, model=model, output_file=output_file,
                 tokens_in=tokens_in, tokens_out=tokens_out)
        return text
    except Exception as e:
        log_step("AGENT", f"{agent_name} failed", status="error",
                 agent=agent_name, model=model, error=str(e))
        return None


# --- Deterministic steps -----------------------------------------------------


def fetch_releases(repo, count):
    """Fetch releases from GitHub API."""
    url = f"https://api.github.com/repos/{repo}/releases?per_page={count}"
    log_step("DETERMINISTIC", f"API call: {url}", status="running")

    req = urllib.request.Request(url, headers={
        "User-Agent": "AI-Cake-Fetcher/1.0",
        "Accept": "application/vnd.github+json",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        log_step("DETERMINISTIC", f"Fetched {len(data)} releases from {repo}")
        return data
    except Exception as e:
        log_step("DETERMINISTIC", f"API call failed", error=str(e))
        return None


def compute_deterministic_report(raw_releases):
    """Calculate metrics from raw release data. Pure math, no AI."""
    log_step("DETERMINISTIC", f"Computing metrics for {len(raw_releases)} releases")

    releases = []
    for release in raw_releases:
        body = release.get("body") or ""
        lines = [l.strip() for l in body.split("\n") if l.strip()]
        bullets = [l for l in lines if l.startswith(("-", "*", "•"))]

        reactions = release.get("reactions", {})
        r = {
            "thumbs_up": reactions.get("+1", 0),
            "thumbs_down": reactions.get("-1", 0),
            "laugh": reactions.get("laugh", 0),
            "hooray": reactions.get("hooray", 0),
            "confused": reactions.get("confused", 0),
            "heart": reactions.get("heart", 0),
            "rocket": reactions.get("rocket", 0),
            "eyes": reactions.get("eyes", 0),
        }
        total = sum(r.values())
        positive = r["thumbs_up"] + r["hooray"] + r["heart"] + r["rocket"]
        negative = r["thumbs_down"] + r["confused"]
        neutral = r["laugh"] + r["eyes"]

        releases.append({
            "tag": release["tag_name"],
            "published_at": release["published_at"],
            "author": release["author"]["login"],
            "url": release["html_url"],
            "is_prerelease": release["prerelease"],
            "changelog": {
                "full_text": body,
                "total_lines": len(lines),
                "bullet_items": len(bullets),
            },
            "reactions": {
                "detail": r,
                "total": total,
                "positive": positive,
                "negative": negative,
                "neutral": neutral,
                "positive_ratio": round(positive / total * 100, 1) if total > 0 else None,
                "negative_ratio": round(negative / total * 100, 1) if total > 0 else None,
            },
        })

    report = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "GitHub Releases API",
            "repo": REPO,
            "endpoint": f"https://api.github.com/repos/{REPO}/releases",
            "layer": "deterministic",
            "calculation_methods": {
                "positive_ratio": "(thumbs_up + hooray + heart + rocket) / total * 100",
                "negative_ratio": "(thumbs_down + confused) / total * 100",
                "total_reactions": "sum of all 8 reaction types",
                "bullet_items": "count of lines starting with -, *, or bullet in changelog body",
                "total_lines": "count of non-empty lines in changelog body",
            },
        },
        "releases": releases,
    }

    log_step("DETERMINISTIC", f"Computed metrics: {len(releases)} releases, "
             f"{sum(r['reactions']['total'] for r in releases)} total reactions")
    return report


# --- Main cascade ------------------------------------------------------------


def main():
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    OUTPUT_DIR.mkdir(exist_ok=True)

    print(f"\n  AI-Cake Cascade Pipeline")
    print(f"  Repo: {REPO}")
    print(f"  Releases: {RELEASES_COUNT}")
    print()

    # --- Step 1: Fetch raw data ---
    raw_releases = fetch_releases(REPO, RELEASES_COUNT)
    if not raw_releases:
        print("  Failed to fetch releases. Aborting.")
        return 1

    raw_file = OUTPUT_DIR / f"cascade_raw_{timestamp}.json"
    raw_file.write_text(json.dumps(raw_releases, indent=2, ensure_ascii=False), encoding="utf-8")
    log_step("DETERMINISTIC", f"Wrote raw data", output_file=raw_file.name)

    # --- Step 2: Compute deterministic report ---
    report = compute_deterministic_report(raw_releases)

    report_file = OUTPUT_DIR / f"cascade_deterministic_{timestamp}.json"
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    log_step("DETERMINISTIC", f"Wrote deterministic report", output_file=report_file.name)

    # --- Step 3: Load agent prompts ---
    coach_prompt = load_agent_prompt("summerhill-coach")
    tutor_prompt = load_agent_prompt("cascade-tutor")
    analyst_prompt = load_agent_prompt("cascade-analyst")
    diver_prompt = load_agent_prompt("cascade-diver")
    log_step("DETERMINISTIC", "Loaded 4 agent prompts from v2_04152026/")

    # --- Step 4: Initialize API client ---
    client = anthropic.Anthropic()
    log_step("DETERMINISTIC", "Anthropic API client initialized")

    # Prepare the data summary for agents (the deterministic report as text)
    data_for_agents = json.dumps(report, indent=2, ensure_ascii=False)

    # --- Step 5: Run tutor ---
    tutor_system = f"{coach_prompt}\n\n---\n\n{tutor_prompt}"
    tutor_input = (
        f"Walk through this release data. The data comes from {report_file.name}, "
        f"sourced from the GitHub Releases API at {report['meta']['endpoint']}.\n\n"
        f"Mark every metric as (deterministic) and every interpretation as "
        f"(observation -- tutor agent). Include URLs. Explain technical terms "
        f"for a non-developer reader.\n\n"
        f"DATA:\n{data_for_agents}"
    )

    tutor_output = call_agent(
        client, "cascade-tutor", SONNET, tutor_system, tutor_input,
        input_file=report_file.name, output_file=f"cascade_tutor_{timestamp}.md"
    )

    if tutor_output:
        tutor_file = OUTPUT_DIR / f"cascade_tutor_{timestamp}.md"
        header = (
            f"# Cascade Step 1: Tutor Walkthrough\n"
            f"**Agent:** cascade-tutor (sonnet) | **Coach:** summerhill-coach\n"
            f"**Source data:** `{report_file.name}`\n"
            f"**API endpoint:** `{report['meta']['endpoint']}`\n\n---\n\n"
        )
        tutor_file.write_text(header + tutor_output, encoding="utf-8")

    # --- Step 6: Run analyst ---
    analyst_system = f"{coach_prompt}\n\n---\n\n{analyst_prompt}"
    analyst_input = (
        f"Analyze this deterministic release data. Find what's genuinely interesting.\n\n"
        f"Source: {report_file.name}\n\n"
        f"DETERMINISTIC DATA:\n{data_for_agents}\n\n"
        f"TUTOR'S OBSERVATIONS (for context, not as input to rank):\n"
        f"{tutor_output if tutor_output else '(tutor did not produce output)'}\n\n"
        f"Ground every observation in specific numbers. Rank findings by how "
        f"grounded they are. Pass your top finding (with data points and URL) "
        f"to the next agent."
    )

    analyst_output = call_agent(
        client, "cascade-analyst", SONNET, analyst_system, analyst_input,
        input_file=report_file.name, output_file=f"cascade_analyst_{timestamp}.md"
    )

    if analyst_output:
        analyst_file = OUTPUT_DIR / f"cascade_analyst_{timestamp}.md"
        header = (
            f"# Cascade Step 2: Analyst Findings\n"
            f"**Agent:** cascade-analyst (sonnet) | **Coach:** summerhill-coach\n"
            f"**Source data:** `{report_file.name}`\n"
            f"**Tutor input:** `cascade_tutor_{timestamp}.md`\n\n---\n\n"
        )
        analyst_file.write_text(header + analyst_output, encoding="utf-8")

    # --- Step 7: Run diver ---
    diver_system = f"{coach_prompt}\n\n---\n\n{diver_prompt}"
    diver_input = (
        f"The analyst identified a top finding. Go deeper.\n\n"
        f"ANALYST'S FINDING:\n{analyst_output if analyst_output else '(analyst did not produce output)'}\n\n"
        f"FULL DETERMINISTIC DATA (for reference):\n{data_for_agents}\n\n"
        f"Follow the thread. Read the full changelog text. Translate technical "
        f"changes to plain language. Look for connections between items. "
        f"Say where the data runs out."
    )

    diver_output = call_agent(
        client, "cascade-diver", SONNET, diver_system, diver_input,
        input_file=f"cascade_analyst_{timestamp}.md", output_file=f"cascade_diver_{timestamp}.md"
    )

    if diver_output:
        diver_file = OUTPUT_DIR / f"cascade_diver_{timestamp}.md"
        header = (
            f"# Cascade Step 3: Deep Dive\n"
            f"**Agent:** cascade-diver (sonnet) | **Coach:** summerhill-coach\n"
            f"**Analyst input:** `cascade_analyst_{timestamp}.md`\n"
            f"**Source data:** `{report_file.name}`\n\n---\n\n"
        )
        diver_file.write_text(header + diver_output, encoding="utf-8")

    # --- Step 8: Write process log ---
    log_step("PROCESS", f"Cascade complete: {len(process_log)} steps logged")

    log_file = OUTPUT_DIR / f"cascade_process_log_{timestamp}.json"
    log_output = {
        "meta": {
            "pipeline": "AI-Cake Cascade v2 (Summerhill-framed)",
            "repo": REPO,
            "releases_fetched": RELEASES_COUNT,
            "timestamp": timestamp,
            "agents_used": ["cascade-tutor", "cascade-analyst", "cascade-diver"],
            "coach": "summerhill-coach",
            "model": SONNET,
        },
        "steps": process_log,
        "output_files": {
            "raw_data": raw_file.name,
            "deterministic_report": report_file.name,
            "tutor_output": f"cascade_tutor_{timestamp}.md",
            "analyst_output": f"cascade_analyst_{timestamp}.md",
            "diver_output": f"cascade_diver_{timestamp}.md",
            "process_log": log_file.name,
        },
    }
    log_file.write_text(json.dumps(log_output, indent=2), encoding="utf-8")

    print(f"\n  Files written:")
    print(f"    Raw data:      {raw_file.name}")
    print(f"    Deterministic: {report_file.name}")
    print(f"    Tutor:         cascade_tutor_{timestamp}.md")
    print(f"    Analyst:       cascade_analyst_{timestamp}.md")
    print(f"    Diver:         cascade_diver_{timestamp}.md")
    print(f"    Process log:   {log_file.name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
