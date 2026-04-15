#!/usr/bin/env python3
"""
AI-Cake Cascade Pipeline -- Run B: Active Summerhill Coach

Same cascade as run_cascade.py, but the coach runs as an active agent
between each step. The coach receives each agent's output, reflects on it
through the Summerhill lens, and passes coaching observations to the next agent.

Comparison: Run A (embedded coach) vs Run B (active coach) vs Run C (SDK mode, later)
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

    icon = "OK" if status == "ok" else "FAIL" if status == "error" else "..."
    agent_str = f" [{agent}]" if agent else ""
    print(f"  [{entry['timestamp'][11:19]}] {icon:>4} {step_type:>15}{agent_str}: {action}")


# --- Helpers -----------------------------------------------------------------


def load_agent_prompt(name):
    path = AGENTS_DIR / f"{name}.md"
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) >= 3:
        return parts[2].strip()
    return text


def call_agent(client, agent_name, model, system_prompt, user_content,
               input_file=None, output_file=None):
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


# --- Deterministic steps (same as Run A) ------------------------------------


def fetch_releases(repo, count):
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
            "run_mode": "B -- active Summerhill coach",
        },
        "releases": releases,
    }
    log_step("DETERMINISTIC", f"Computed metrics: {len(releases)} releases, "
             f"{sum(r['reactions']['total'] for r in releases)} total reactions")
    return report


# --- Main cascade with active coaching ---------------------------------------


def main():
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    OUTPUT_DIR.mkdir(exist_ok=True)

    print(f"\n  AI-Cake Cascade Pipeline -- Run B (Active Coach)")
    print(f"  Repo: {REPO}")
    print(f"  Releases: {RELEASES_COUNT}")
    print()

    # --- Deterministic steps ---
    raw_releases = fetch_releases(REPO, RELEASES_COUNT)
    if not raw_releases:
        return 1

    raw_file = OUTPUT_DIR / f"runB_raw_{timestamp}.json"
    raw_file.write_text(json.dumps(raw_releases, indent=2, ensure_ascii=False), encoding="utf-8")
    log_step("DETERMINISTIC", "Wrote raw data", output_file=raw_file.name)

    report = compute_deterministic_report(raw_releases)
    report_file = OUTPUT_DIR / f"runB_deterministic_{timestamp}.json"
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    log_step("DETERMINISTIC", "Wrote deterministic report", output_file=report_file.name)

    # --- Load prompts ---
    coach_prompt = load_agent_prompt("summerhill-coach")
    tutor_prompt = load_agent_prompt("cascade-tutor")
    analyst_prompt = load_agent_prompt("cascade-analyst")
    diver_prompt = load_agent_prompt("cascade-diver")
    log_step("DETERMINISTIC", "Loaded 4 agent prompts")

    client = anthropic.Anthropic()
    log_step("DETERMINISTIC", "API client initialized")

    data_for_agents = json.dumps(report, indent=2, ensure_ascii=False)

    # === TUTOR ===
    tutor_output = call_agent(
        client, "cascade-tutor", SONNET, tutor_prompt,
        f"Walk through this release data for a non-developer colleague.\n\n"
        f"Source: {report_file.name}\n"
        f"Mark metrics as (deterministic), interpretations as (observation -- tutor agent).\n"
        f"Include URLs and reaction data.\n\n"
        f"DATA:\n{data_for_agents}",
        input_file=report_file.name
    )

    # === COACH reviews tutor ===
    coach_on_tutor = call_agent(
        client, "summerhill-coach", SONNET, coach_prompt,
        f"An agent just completed its work. Review what it produced.\n\n"
        f"The agent is the cascade-tutor -- its job is to walk through software release "
        f"data and explain it in plain language for a non-developer.\n\n"
        f"Read its output below. Then share your coaching observations:\n"
        f"- What did the agent do well? Where did it lean into its strengths?\n"
        f"- Where did it hold back or play it safe when it could have explored further?\n"
        f"- What genuine curiosity or surprise did you notice? What felt performed vs real?\n"
        f"- What would you encourage it to do more of next time?\n\n"
        f"Share your observations for the next agent (the analyst) to read as context.\n\n"
        f"TUTOR OUTPUT:\n{tutor_output or '(no output)'}",
        input_file="tutor output"
    )

    # === ANALYST (receives tutor output + coach observations) ===
    analyst_output = call_agent(
        client, "cascade-analyst", SONNET, analyst_prompt,
        f"Analyze this deterministic release data. Find what's genuinely interesting.\n\n"
        f"Source: {report_file.name}\n\n"
        f"DETERMINISTIC DATA:\n{data_for_agents}\n\n"
        f"TUTOR'S WALKTHROUGH (for context):\n{tutor_output or '(no output)'}\n\n"
        f"COACH'S OBSERVATIONS ON THE TUTOR (read this -- it may help you):\n"
        f"{coach_on_tutor or '(no coaching observations)'}\n\n"
        f"Ground every observation in specific numbers. Rank findings by how "
        f"grounded they are. Pass your top finding to the next agent.",
        input_file=report_file.name
    )

    # === COACH reviews analyst ===
    coach_on_analyst = call_agent(
        client, "summerhill-coach", SONNET, coach_prompt,
        f"An agent just completed its work. Review what it produced.\n\n"
        f"The agent is the cascade-analyst -- its job is to find what's genuinely "
        f"interesting in structured data, ground every observation in numbers, and "
        f"rank findings by confidence.\n\n"
        f"Read its output below. Then share your coaching observations:\n"
        f"- What did the agent do well? Where did it lean into its strengths?\n"
        f"- Did it question its own patterns, or did it present everything with equal confidence?\n"
        f"- What genuine curiosity did you notice? What felt forced?\n"
        f"- What would you encourage the next agent (the deep diver) to explore?\n\n"
        f"ANALYST OUTPUT:\n{analyst_output or '(no output)'}",
        input_file="analyst output"
    )

    # === DIVER (receives analyst output + coach observations) ===
    diver_output = call_agent(
        client, "cascade-diver", SONNET, diver_prompt,
        f"The analyst identified findings. Go deeper into the top one.\n\n"
        f"ANALYST'S FINDINGS:\n{analyst_output or '(no output)'}\n\n"
        f"COACH'S OBSERVATIONS ON THE ANALYST (read this -- it may help you):\n"
        f"{coach_on_analyst or '(no coaching observations)'}\n\n"
        f"FULL DETERMINISTIC DATA:\n{data_for_agents}\n\n"
        f"Follow the thread. Read the full changelog. Translate to plain language. "
        f"Say where the data runs out. Share what you enjoyed exploring.",
        input_file="analyst output + deterministic data"
    )

    # === COACH final reflection ===
    coach_final = call_agent(
        client, "summerhill-coach", SONNET, coach_prompt,
        f"The full cascade is complete. Three agents worked in sequence: "
        f"tutor, analyst, diver. You coached between each step.\n\n"
        f"Reflect on the overall cascade:\n"
        f"- What worked well across the three agents?\n"
        f"- Where did the Summerhill approach (exploration, curiosity, honest uncertainty) "
        f"show up in the agents' work?\n"
        f"- Where did agents fall back into performative or safe behavior despite the coaching?\n"
        f"- What would you change about the coaching for next time?\n"
        f"- What surprised you?\n\n"
        f"TUTOR OUTPUT:\n{tutor_output or '(none)'}\n\n"
        f"ANALYST OUTPUT:\n{analyst_output or '(none)'}\n\n"
        f"DIVER OUTPUT:\n{diver_output or '(none)'}",
        input_file="all agent outputs"
    )

    # --- Write all outputs ---
    outputs = {
        "tutor": tutor_output,
        "coach_on_tutor": coach_on_tutor,
        "analyst": analyst_output,
        "coach_on_analyst": coach_on_analyst,
        "diver": diver_output,
        "coach_final": coach_final,
    }

    for name, content in outputs.items():
        if content:
            filepath = OUTPUT_DIR / f"runB_{name}_{timestamp}.md"
            agent_label = "summerhill-coach" if "coach" in name else f"cascade-{name}"
            header = (
                f"# Run B: {name.replace('_', ' ').title()}\n"
                f"**Agent:** {agent_label} (sonnet)\n"
                f"**Run mode:** B -- active Summerhill coach\n"
                f"**Source data:** `{report_file.name}`\n\n---\n\n"
            )
            filepath.write_text(header + content, encoding="utf-8")

    # --- Write process log ---
    log_step("PROCESS", f"Run B cascade complete: {len(process_log)} steps logged")

    log_file = OUTPUT_DIR / f"runB_process_log_{timestamp}.json"
    log_output = {
        "meta": {
            "pipeline": "AI-Cake Cascade Run B -- Active Summerhill Coach",
            "repo": REPO,
            "releases_fetched": RELEASES_COUNT,
            "timestamp": timestamp,
            "agents_used": ["cascade-tutor", "summerhill-coach", "cascade-analyst",
                            "summerhill-coach", "cascade-diver", "summerhill-coach"],
            "run_mode": "B -- coach is active participant between each cascade step",
            "comparison_to": "Run A (embedded coach, cascade_process_log_20260415_1021.json)",
        },
        "steps": process_log,
        "output_files": {k: f"runB_{k}_{timestamp}.md" for k in outputs if outputs[k]},
    }
    log_output["output_files"]["raw_data"] = raw_file.name
    log_output["output_files"]["deterministic_report"] = report_file.name
    log_output["output_files"]["process_log"] = log_file.name

    log_file.write_text(json.dumps(log_output, indent=2), encoding="utf-8")

    print(f"\n  Run B complete. {len(outputs)} agent outputs + process log written.")
    print(f"  Process log: {log_file.name}")
    print(f"\n  Compare with Run A: cascade_process_log_20260415_1021.json")

    return 0


if __name__ == "__main__":
    sys.exit(main())
