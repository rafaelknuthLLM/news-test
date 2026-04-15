#!/usr/bin/env python3
"""
AI-Cake Ritual Pipeline v3 -- Testing during the run.

The ritual:
1. Tutor presents -> Bob questions -> Tutor responds -> Coach observes
2. Analyst presents -> Bob questions -> Analyst responds -> Coach observes
3. Diver presents -> Bob questions -> Diver responds -> Coach observes
4. Coach hosts debrief -- all perspectives shared

Single combined report. Full process log.
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
AGENTS_DIR = Path(__file__).parent / ".claude" / "agents" / "v3_04152026"
REPO = "anthropics/claude-code"
RELEASES_COUNT = 5

# --- Process log -------------------------------------------------------------

process_log = []


def log_step(step_type, action, status="ok", agent=None, model=None,
             tokens_in=None, tokens_out=None, error=None):
    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "type": step_type, "action": action, "status": status,
    }
    if agent: entry["agent"] = agent
    if model: entry["model"] = model
    if tokens_in is not None: entry["tokens_in"] = tokens_in
    if tokens_out is not None: entry["tokens_out"] = tokens_out
    if error: entry["error"] = error; entry["status"] = "error"
    process_log.append(entry)
    icon = "OK" if status == "ok" else "FAIL" if status == "error" else "..."
    agent_str = f" [{agent}]" if agent else ""
    print(f"  [{entry['timestamp'][11:19]}] {icon:>4} {step_type:>15}{agent_str}: {action}")


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
            model=model, max_tokens=4000,
            system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user_content}],
        )
        duration = round(time.time() - start, 1)
        text = response.content[0].text
        t_in, t_out = response.usage.input_tokens, response.usage.output_tokens
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
        "User-Agent": "AI-Cake-Fetcher/1.0", "Accept": "application/vnd.github+json",
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
            "tag": release["tag_name"], "published_at": release["published_at"],
            "author": release["author"]["login"], "url": release["html_url"],
            "is_prerelease": release["prerelease"],
            "changelog": {"full_text": body, "total_lines": len(lines), "bullet_items": len(bullets)},
            "reactions": {
                "detail": r, "total": total, "positive": positive,
                "negative": negative, "neutral": r["laugh"] + r["eyes"],
                "positive_ratio": round(positive / total * 100, 1) if total > 0 else None,
                "negative_ratio": round(negative / total * 100, 1) if total > 0 else None,
            },
        })
    log_step("DETERMINISTIC", f"Computed: {len(releases)} releases, "
             f"{sum(r['reactions']['total'] for r in releases)} total reactions")
    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "repo": REPO, "endpoint": f"https://api.github.com/repos/{REPO}/releases",
            "calculation_methods": {
                "positive_ratio": "(thumbs_up + hooray + heart + rocket) / total * 100",
                "negative_ratio": "(thumbs_down + confused) / total * 100",
            },
        },
        "releases": releases,
    }


# --- Ritual round: present -> question -> respond -> coach observe -----------


def ritual_round(client, round_num, presenter_name, presenter_prompt,
                 bob_prompt, coach_prompt, data_json, presentation_input,
                 prior_context=""):
    """Run one round of the ritual: present, question, respond, observe."""
    sections = []

    # 1. Presenter presents
    presentation = call_agent(client, presenter_name, SONNET, presenter_prompt,
        presentation_input)

    sections.append(
        f"## Round {round_num}: {presenter_name.replace('cascade-', '').title()}\n\n"
        f"### {round_num}a. Presentation\n"
        f"*Agent: {presenter_name} (sonnet)*\n\n"
        f"{presentation or '(no output)'}\n"
    )

    # 2. Bob questions
    bob_questions = call_agent(client, "bob-questioner", SONNET, bob_prompt,
        f"An analyst just presented their work. Read it and ask exactly three questions.\n\n"
        f"PRESENTATION:\n{presentation or '(no output)'}")

    sections.append(
        f"\n### {round_num}b. Bob's Questions\n"
        f"*Agent: bob-questioner (sonnet)*\n\n"
        f"{bob_questions or '(no questions)'}\n"
    )

    # 3. Presenter responds to Bob
    response = call_agent(client, presenter_name, SONNET, presenter_prompt,
        f"Someone from outside the technology industry just read your work and "
        f"asked three questions. Answer them honestly. If you don't know the answer, "
        f"say so -- that's useful information.\n\n"
        f"YOUR ORIGINAL PRESENTATION:\n{presentation or '(none)'}\n\n"
        f"THEIR QUESTIONS:\n{bob_questions or '(none)'}\n\n"
        f"DATA (for reference):\n{data_json}")

    sections.append(
        f"\n### {round_num}c. Response to Bob\n"
        f"*Agent: {presenter_name} (sonnet)*\n\n"
        f"{response or '(no response)'}\n"
    )

    # 4. Coach observes the exchange
    coach_obs = call_agent(client, "summerhill-coach", SONNET, coach_prompt,
        f"A ritual round just completed. The {presenter_name} presented, "
        f"Bob (an outsider) asked three questions, and the presenter responded.\n\n"
        f"Observe this exchange:\n"
        f"- What did Bob's questions reveal about the presentation?\n"
        f"- How did the presenter handle the challenge?\n"
        f"- What shifted or deepened because of the questioning?\n"
        f"- What should the next presenter know?\n\n"
        f"PRESENTATION:\n{presentation or '(none)'}\n\n"
        f"BOB'S QUESTIONS:\n{bob_questions or '(none)'}\n\n"
        f"RESPONSES:\n{response or '(none)'}")

    sections.append(
        f"\n### {round_num}d. Coach Observation\n"
        f"*Agent: summerhill-coach (sonnet)*\n\n"
        f"{coach_obs or '(no observation)'}\n"
    )

    return "\n".join(sections), presentation, bob_questions, response, coach_obs


# --- Main --------------------------------------------------------------------


def main():
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    run_dir = OUTPUT_DIR / f"v3_ritual_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  AI-Cake Ritual v3 -- Testing During the Run")
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
    bob_prompt = load_agent_prompt("bob-questioner")
    log_step("DETERMINISTIC", "Loaded 5 agent prompts")

    client = anthropic.Anthropic()
    data_json = json.dumps(report, indent=2, ensure_ascii=False)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # --- Header ---
    header = (
        f"# AI-Cake Ritual Report\n"
        f"**Generated:** {now_str}\n"
        f"**Repo:** {REPO}\n"
        f"**Releases:** {RELEASES_COUNT}\n"
        f"**Ritual:** present -> Bob questions -> respond -> coach observes (x3) -> debrief\n"
        f"**Agent team:** v3_04152026\n"
        f"**Agents:** cascade-tutor, cascade-analyst, cascade-diver, bob-questioner, summerhill-coach\n"
        f"**Data:** `{run_dir.name}/deterministic_report.json`\n\n"
        f"---\n"
    )

    all_sections = [header]

    # --- Round 1: Tutor ---
    r1_text, tutor_out, bob_q1, tutor_resp, coach1 = ritual_round(
        client, 1, "cascade-tutor", tutor_prompt, bob_prompt, coach_prompt,
        data_json,
        f"Walk through this release data for a non-developer colleague.\n"
        f"Mark metrics as (deterministic), interpretations as (observation -- tutor agent).\n"
        f"Include URLs. Translate technical terms.\n"
        f"Describe a path you started and abandoned.\n\n"
        f"DATA:\n{data_json}"
    )
    all_sections.append(r1_text)

    # --- Round 2: Analyst ---
    r2_text, analyst_out, bob_q2, analyst_resp, coach2 = ritual_round(
        client, 2, "cascade-analyst", analyst_prompt, bob_prompt, coach_prompt,
        data_json,
        f"Find what's genuinely interesting in this release data.\n\n"
        f"DETERMINISTIC DATA:\n{data_json}\n\n"
        f"TUTOR'S WALKTHROUGH:\n{tutor_out or '(none)'}\n\n"
        f"COACH'S OBSERVATIONS FROM ROUND 1:\n{coach1 or '(none)'}\n\n"
        f"Ground observations in specific numbers. Rank by confidence.\n"
        f"Describe a path you started and abandoned."
    )
    all_sections.append(r2_text)

    # --- Round 3: Diver ---
    r3_text, diver_out, bob_q3, diver_resp, coach3 = ritual_round(
        client, 3, "cascade-diver", diver_prompt, bob_prompt, coach_prompt,
        data_json,
        f"Go deeper into the analyst's top finding.\n\n"
        f"ANALYST'S FINDINGS:\n{analyst_out or '(none)'}\n\n"
        f"COACH'S OBSERVATIONS FROM ROUND 2:\n{coach2 or '(none)'}\n\n"
        f"FULL DATA:\n{data_json}\n\n"
        f"Read the full changelog. Translate to plain language.\n"
        f"Say where the data runs out. Share what you enjoyed.\n"
        f"Describe a path you started and abandoned."
    )
    all_sections.append(r3_text)

    # --- Debrief ---
    debrief = call_agent(client, "summerhill-coach", SONNET, coach_prompt,
        f"The ritual is complete. Three rounds of: presentation, Bob's questions, "
        f"responses, and your observations.\n\n"
        f"Host the debrief. Reflect on the full ritual:\n\n"
        f"- What did the team learn that no single agent would have found alone?\n"
        f"- How did Bob's questions change the direction or depth of the analysis?\n"
        f"- Where did agents show genuine exploration vs performative behavior?\n"
        f"- What was the most surprising moment in the ritual?\n"
        f"- What would you change about the ritual structure for next time?\n"
        f"- What remains unresolved -- what questions are still open?\n\n"
        f"ROUND 1 (Tutor + Bob + Response + Your Obs):\n{r1_text}\n\n"
        f"ROUND 2 (Analyst + Bob + Response + Your Obs):\n{r2_text}\n\n"
        f"ROUND 3 (Diver + Bob + Response + Your Obs):\n{r3_text}")

    all_sections.append(
        f"\n---\n\n"
        f"## Debrief\n"
        f"*Agent: summerhill-coach (sonnet) -- hosting*\n\n"
        f"{debrief or '(no debrief)'}\n"
    )

    # --- Process log ---
    log_step("PROCESS", f"Ritual complete: {len(process_log)} steps")

    total_in = sum(s.get("tokens_in", 0) for s in process_log)
    total_out = sum(s.get("tokens_out", 0) for s in process_log)

    log_table = (
        f"\n---\n\n"
        f"## Process Log\n\n"
        f"| Time | Type | Agent | Action | Tokens |\n"
        f"|---|---|---|---|---|\n"
    )
    for s in process_log:
        t = s["timestamp"][11:19]
        agent = s.get("agent", "")
        tokens = f"{s['tokens_in']:,} / {s['tokens_out']:,}" if s.get("tokens_in") else ""
        log_table += f"| {t} | {s['type']} | {agent} | {s['action']} | {tokens} |\n"

    log_table += f"\n**Totals:** {total_in:,} tokens in, {total_out:,} tokens out\n"
    all_sections.append(log_table)

    # --- Write files ---
    report_file = run_dir / "report.md"
    report_file.write_text("\n".join(all_sections), encoding="utf-8")

    log_file = run_dir / "process_log.json"
    log_file.write_text(json.dumps({
        "meta": {
            "pipeline": "AI-Cake Ritual v3", "repo": REPO, "timestamp": timestamp,
            "agents": ["cascade-tutor", "bob-questioner", "cascade-analyst",
                       "cascade-diver", "summerhill-coach"],
            "total_tokens_in": total_in, "total_tokens_out": total_out,
        },
        "steps": process_log,
    }, indent=2), encoding="utf-8")

    print(f"\n  Output: {run_dir.name}/")
    print(f"    report.md")
    print(f"    deterministic_report.json")
    print(f"    process_log.json")
    print(f"  Tokens: {total_in:,} in, {total_out:,} out")

    return 0


if __name__ == "__main__":
    sys.exit(main())
