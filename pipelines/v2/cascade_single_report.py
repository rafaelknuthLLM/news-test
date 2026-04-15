#!/usr/bin/env python3
"""
AI-Cake Cascade Pipeline v2 -- Single combined report, active coach, improved framing.

Produces ONE markdown file that reads like a conversation:
tutor explains -> coach reflects -> analyst finds -> coach reflects -> diver explores -> coach reflects

Plus a process log and the deterministic data.
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


def log_step(step_type, action, status="ok", agent=None, model=None,
             tokens_in=None, tokens_out=None, error=None):
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
    if tokens_in is not None:
        entry["tokens_in"] = tokens_in
    if tokens_out is not None:
        entry["tokens_out"] = tokens_out
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
    return parts[2].strip() if len(parts) >= 3 else text


def call_agent(client, agent_name, model, system_prompt, user_content):
    log_step("AGENT", f"{agent_name} started", status="running", agent=agent_name, model=model)
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
        t_in = response.usage.input_tokens
        t_out = response.usage.output_tokens
        log_step("AGENT", f"{agent_name} completed ({duration}s)",
                 agent=agent_name, model=model, tokens_in=t_in, tokens_out=t_out)
        return text
    except Exception as e:
        log_step("AGENT", f"{agent_name} failed", agent=agent_name, model=model, error=str(e))
        return None


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
        log_step("DETERMINISTIC", f"Fetched {len(data)} releases")
        return data
    except Exception as e:
        log_step("DETERMINISTIC", "API call failed", error=str(e))
        return None


def compute_metrics(raw_releases):
    log_step("DETERMINISTIC", f"Computing metrics for {len(raw_releases)} releases")
    releases = []
    for release in raw_releases:
        body = release.get("body") or ""
        lines = [l.strip() for l in body.split("\n") if l.strip()]
        bullets = [l for l in lines if l.startswith(("-", "*", "•"))]
        rx = release.get("reactions", {})
        r = {
            "thumbs_up": rx.get("+1", 0), "thumbs_down": rx.get("-1", 0),
            "laugh": rx.get("laugh", 0), "hooray": rx.get("hooray", 0),
            "confused": rx.get("confused", 0), "heart": rx.get("heart", 0),
            "rocket": rx.get("rocket", 0), "eyes": rx.get("eyes", 0),
        }
        total = sum(r.values())
        positive = r["thumbs_up"] + r["hooray"] + r["heart"] + r["rocket"]
        negative = r["thumbs_down"] + r["confused"]
        releases.append({
            "tag": release["tag_name"],
            "published_at": release["published_at"],
            "author": release["author"]["login"],
            "url": release["html_url"],
            "is_prerelease": release["prerelease"],
            "changelog": {"full_text": body, "total_lines": len(lines), "bullet_items": len(bullets)},
            "reactions": {
                "detail": r, "total": total, "positive": positive, "negative": negative,
                "neutral": r["laugh"] + r["eyes"],
                "positive_ratio": round(positive / total * 100, 1) if total > 0 else None,
                "negative_ratio": round(negative / total * 100, 1) if total > 0 else None,
            },
        })
    total_rx = sum(r["reactions"]["total"] for r in releases)
    log_step("DETERMINISTIC", f"Computed: {len(releases)} releases, {total_rx} total reactions")
    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "repo": REPO,
            "endpoint": f"https://api.github.com/repos/{REPO}/releases",
            "calculation_methods": {
                "positive_ratio": "(thumbs_up + hooray + heart + rocket) / total * 100",
                "negative_ratio": "(thumbs_down + confused) / total * 100",
                "bullet_items": "lines starting with -, *, or bullet in changelog body",
            },
        },
        "releases": releases,
    }


# --- Main --------------------------------------------------------------------


def main():
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    run_dir = OUTPUT_DIR / f"runB2_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  AI-Cake Cascade v2 -- Active Coach, Single Report")
    print(f"  Repo: {REPO}")
    print(f"  Output: {run_dir.name}/")
    print()

    # --- Fetch + compute ---
    raw = fetch_releases(REPO, RELEASES_COUNT)
    if not raw:
        return 1

    report = compute_metrics(raw)
    det_file = run_dir / "deterministic_report.json"
    det_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    log_step("DETERMINISTIC", "Wrote deterministic report")

    # --- Load prompts ---
    coach_prompt = load_agent_prompt("summerhill-coach")
    tutor_prompt = load_agent_prompt("cascade-tutor")
    analyst_prompt = load_agent_prompt("cascade-analyst")
    diver_prompt = load_agent_prompt("cascade-diver")
    log_step("DETERMINISTIC", "Loaded agent prompts")

    client = anthropic.Anthropic()
    data_json = json.dumps(report, indent=2, ensure_ascii=False)

    # --- Combined report sections ---
    sections = []
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    sections.append(
        f"# AI-Cake Cascade Report\n"
        f"**Generated:** {now_str}\n"
        f"**Repo:** {REPO}\n"
        f"**Releases:** {RELEASES_COUNT}\n"
        f"**Pipeline:** tutor -> coach -> analyst -> coach -> diver -> coach\n"
        f"**Agent team:** v2_04152026 (Summerhill-framed)\n"
        f"**Deterministic data:** `{run_dir.name}/deterministic_report.json`\n"
        f"**Process log:** `{run_dir.name}/process_log.json`\n"
        f"**Calculation methods:** all metrics are deterministic "
        f"(positive_ratio = (thumbs_up + hooray + heart + rocket) / total * 100)\n"
    )

    # === TUTOR ===
    tutor_out = call_agent(client, "cascade-tutor", SONNET, tutor_prompt,
        f"Walk through this release data for a non-developer colleague.\n"
        f"Mark metrics as (deterministic), interpretations as (observation -- tutor agent).\n"
        f"Include URLs. Translate technical terms.\n"
        f"At some point, describe a path you started and abandoned, and why.\n\n"
        f"DATA:\n{data_json}")

    if tutor_out:
        sections.append(
            f"---\n\n"
            f"## Part 1: Tutor Walkthrough\n"
            f"*Agent: cascade-tutor (sonnet)*\n\n"
            f"{tutor_out}"
        )

    # === COACH on tutor ===
    coach1 = call_agent(client, "summerhill-coach", SONNET, coach_prompt,
        f"The cascade-tutor just walked through release data for a non-developer.\n\n"
        f"Review its output. Share coaching observations:\n"
        f"- What did it do well? Where did it lean into its strengths?\n"
        f"- Where could it have explored further?\n"
        f"- What genuine curiosity did you notice?\n"
        f"- What open questions should the analyst pick up?\n\n"
        f"TUTOR OUTPUT:\n{tutor_out or '(none)'}")

    if coach1:
        sections.append(
            f"\n---\n\n"
            f"## Part 2: Coach Observations on the Tutor\n"
            f"*Agent: summerhill-coach (sonnet)*\n\n"
            f"{coach1}"
        )

    # === ANALYST ===
    analyst_out = call_agent(client, "cascade-analyst", SONNET, analyst_prompt,
        f"Find what's genuinely interesting in this release data.\n\n"
        f"DETERMINISTIC DATA:\n{data_json}\n\n"
        f"TUTOR'S WALKTHROUGH:\n{tutor_out or '(none)'}\n\n"
        f"COACH'S OBSERVATIONS:\n{coach1 or '(none)'}\n\n"
        f"Ground observations in specific numbers. Rank by confidence.\n"
        f"Pass your top finding with data points and URL to the diver.\n"
        f"At some point, describe a path you started and abandoned.")

    if analyst_out:
        sections.append(
            f"\n---\n\n"
            f"## Part 3: Analyst Findings\n"
            f"*Agent: cascade-analyst (sonnet)*\n\n"
            f"{analyst_out}"
        )

    # === COACH on analyst ===
    coach2 = call_agent(client, "summerhill-coach", SONNET, coach_prompt,
        f"The cascade-analyst just analyzed the release data.\n\n"
        f"Review its output. Share coaching observations:\n"
        f"- Did it question its own patterns?\n"
        f"- What genuine curiosity did you notice? What felt forced?\n"
        f"- What should the diver explore?\n\n"
        f"ANALYST OUTPUT:\n{analyst_out or '(none)'}")

    if coach2:
        sections.append(
            f"\n---\n\n"
            f"## Part 4: Coach Observations on the Analyst\n"
            f"*Agent: summerhill-coach (sonnet)*\n\n"
            f"{coach2}"
        )

    # === DIVER ===
    diver_out = call_agent(client, "cascade-diver", SONNET, diver_prompt,
        f"Go deeper into the analyst's top finding.\n\n"
        f"ANALYST'S FINDINGS:\n{analyst_out or '(none)'}\n\n"
        f"COACH'S OBSERVATIONS:\n{coach2 or '(none)'}\n\n"
        f"FULL DATA:\n{data_json}\n\n"
        f"Read the full changelog. Translate to plain language.\n"
        f"Say where the data runs out. Share what you enjoyed.\n"
        f"Describe a path you started and abandoned.")

    if diver_out:
        sections.append(
            f"\n---\n\n"
            f"## Part 5: Deep Dive\n"
            f"*Agent: cascade-diver (sonnet)*\n\n"
            f"{diver_out}"
        )

    # === COACH final ===
    coach_final = call_agent(client, "summerhill-coach", SONNET, coach_prompt,
        f"The full cascade is complete (tutor -> analyst -> diver).\n\n"
        f"Reflect on the whole process:\n"
        f"- What worked well?\n"
        f"- Where did agents show genuine curiosity vs performative behavior?\n"
        f"- Did the wrong-turn coaching show up? How?\n"
        f"- What surprised you?\n"
        f"- What would you change for next time?\n\n"
        f"TUTOR:\n{tutor_out or '(none)'}\n\n"
        f"ANALYST:\n{analyst_out or '(none)'}\n\n"
        f"DIVER:\n{diver_out or '(none)'}")

    if coach_final:
        sections.append(
            f"\n---\n\n"
            f"## Part 6: Coach Reflection\n"
            f"*Agent: summerhill-coach (sonnet)*\n\n"
            f"{coach_final}"
        )

    # --- Process log section ---
    log_step("PROCESS", f"Cascade complete: {len(process_log)} steps")

    total_in = sum(s.get("tokens_in", 0) for s in process_log)
    total_out = sum(s.get("tokens_out", 0) for s in process_log)

    sections.append(
        f"\n---\n\n"
        f"## Process Log\n\n"
        f"| Time (UTC) | Type | Agent | Action | Tokens |\n"
        f"|---|---|---|---|---|\n"
    )
    for s in process_log:
        t = s["timestamp"][11:19]
        agent = s.get("agent", "")
        tokens = f"{s['tokens_in']:,} in / {s['tokens_out']:,} out" if s.get("tokens_in") else ""
        sections[-1] += f"| {t} | {s['type']} | {agent} | {s['action']} | {tokens} |\n"

    sections[-1] += (
        f"\n**Totals:** {total_in:,} tokens in, {total_out:,} tokens out\n"
    )

    # --- Write combined report ---
    combined = "\n".join(sections)
    report_file = run_dir / "report.md"
    report_file.write_text(combined, encoding="utf-8")

    # --- Write process log JSON ---
    log_file = run_dir / "process_log.json"
    log_output = {
        "meta": {
            "pipeline": "AI-Cake Cascade v2 -- Active Coach, Single Report",
            "repo": REPO, "timestamp": timestamp,
            "agents": ["cascade-tutor", "summerhill-coach", "cascade-analyst",
                        "summerhill-coach", "cascade-diver", "summerhill-coach"],
            "total_tokens_in": total_in, "total_tokens_out": total_out,
        },
        "steps": process_log,
    }
    log_file.write_text(json.dumps(log_output, indent=2), encoding="utf-8")

    print(f"\n  Output: {run_dir.name}/")
    print(f"    report.md              -- single combined report")
    print(f"    deterministic_report.json")
    print(f"    process_log.json")
    print(f"  Tokens: {total_in:,} in, {total_out:,} out")

    return 0


if __name__ == "__main__":
    sys.exit(main())
