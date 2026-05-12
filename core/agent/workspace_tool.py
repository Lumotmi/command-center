#!/usr/bin/env python3
"""Livesystems AG Workspace Tool — routes every action through the REST API."""

import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path.home() / "workspace" / ".env")

API_BASE = os.getenv("CC_API_BASE", "http://localhost:5001/api")


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _get(path: str, params: dict = None) -> dict:
    r = requests.get(f"{API_BASE}{path}", params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def _post(path: str, body: dict) -> dict:
    r = requests.post(f"{API_BASE}{path}", json=body, timeout=10)
    r.raise_for_status()
    return r.json()


def _patch(path: str, body: dict) -> dict:
    r = requests.patch(f"{API_BASE}{path}", json=body, timeout=10)
    r.raise_for_status()
    return r.json()


def _delete(path: str) -> dict:
    r = requests.delete(f"{API_BASE}{path}", timeout=10)
    r.raise_for_status()
    return r.json()


# ── Tasks ─────────────────────────────────────────────────────────────────────

def add_task(text: str, tag: str = "General", priority: str = "medium") -> str:
    t = _post("/tasks", {"text": text, "tag": tag, "priority": priority})
    return f"Task #{t['id']} added: {text} [{tag}] ({priority})"


def complete_task(task_id: int = None, text_match: str = None) -> str:
    if task_id is None and text_match:
        tasks = _get("/tasks")["tasks"]
        match = next(
            (t for t in tasks if text_match.lower() in t["text"].lower()), None
        )
        if match is None:
            return f"No task matching '{text_match}'"
        task_id = match["id"]
    if task_id is None:
        return "Provide task_id or text_match"
    t = _patch(f"/tasks/{task_id}", {"done": True})
    return f"Task #{task_id} marked complete: {t['text']}"


def delete_task(task_id: int) -> str:
    _delete(f"/tasks/{task_id}")
    return f"Task #{task_id} deleted"


def list_tasks(show_done: bool = False) -> str:
    tasks = _get("/tasks", {"done": "true"} if show_done else {})["tasks"]
    if not show_done:
        tasks = [t for t in tasks if not t.get("done")]
    if not tasks:
        return "No open tasks."
    lines = []
    for t in tasks:
        status = "✅" if t.get("done") else "⬜"
        prio = f"[{t['priority'].upper()}]" if t.get("priority") else ""
        lines.append(f"{status} #{t['id']} {prio} {t['text']} ({t.get('tag','')})")
    return "\n".join(lines)


# ── Team ──────────────────────────────────────────────────────────────────────

def update_health(member: str, health: int, note: str = None) -> str:
    body = {"health": max(1, min(10, int(health)))}
    if note:
        body["notes"] = note
    m = _patch(f"/team/{member}", body)
    return f"Updated {m['name']} health to {health}/10"


def add_member_note(member: str, note: str) -> str:
    m = _patch(f"/team/{member}", {"notes": note})
    return f"Note added to {m['name']}: {note}"


def get_team_status() -> str:
    members = _get("/team")["team"]
    lines = ["Team health snapshot:"]
    for m in members:
        h = m.get("health", 5)
        bar = "█" * h + "░" * (10 - h)
        notes = m.get("notes", [])
        note_str = f" ⚠ {notes[0]}" if notes else ""
        lines.append(f"  {m.get('avatar','👤')} {m['name']:15} {bar} {h}/10{note_str}")
    return "\n".join(lines)


# ── SPOC log ──────────────────────────────────────────────────────────────────

def add_spoc_log(title: str, body: str, status: str = "open", keywords: list = None) -> str:
    entry = _post("/spoc", {
        "title": title, "body": body, "status": status,
        "kws": keywords or [],
    })
    return f"SPOC entry #{entry['id']} logged: {title} [{status}]"


def update_spoc_status(entry_id: int, status: str) -> str:
    e = _patch(f"/spoc/{entry_id}", {"status": status})
    return f"SPOC #{entry_id} status → {status}"


def get_spoc_summary() -> str:
    entries = _get("/spoc")["spoc_log"]
    if not entries:
        return "No SPOC entries."
    lines = ["SPOC log:"]
    for e in entries:
        lines.append(f"  [{e['status'].upper():8}] #{e['id']} {e['date']} — {e['title']}")
        if e.get("body"):
            lines.append(f"           {e['body'][:80]}")
    return "\n".join(lines)


# ── Projects ──────────────────────────────────────────────────────────────────

def update_project(project_id: str, status: str = None, progress: int = None, note: str = None) -> str:
    body = {}
    if status:
        body["status"] = status
    if progress is not None:
        body["progress"] = max(0, min(100, int(progress)))
    if note:
        body["notes"] = note
    p = _patch(f"/projects/{project_id}", body)
    return f"Project '{p['name']}' updated: status={p['status']}, progress={p['progress']}%"


def update_milestone(project_id: str, milestone_text: str, status: str) -> str:
    p = _patch(f"/projects/{project_id}/milestones",
               {"milestone_text": milestone_text, "status": status})
    return f"Milestone '{milestone_text}' → {status} in {project_id}"


def get_project_summary() -> str:
    projects = _get("/projects")["projects"]
    status_icons = {"ontrack": "✅", "atrisk": "⚠️", "blocked": "🔴", "done": "🏁"}
    lines = ["Projects:"]
    for p in projects:
        icon = status_icons.get(p["status"], "❓")
        prog = p.get("progress", 0)
        bar = "█" * (prog // 10) + "░" * (10 - prog // 10)
        lines.append(f"  {icon} {p['name']:30} {bar} {prog}%")
        notes = p.get("notes", [])
        if notes:
            lines.append(f"     └ {notes[0]}")
    return "\n".join(lines)


# ── Comms ─────────────────────────────────────────────────────────────────────

def send_telegram(message: str) -> str:
    token = os.getenv("TELEGRAM_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or token == "your_bot_token_here":
        return "Telegram not configured — skipping"
    try:
        import requests as req
        r = req.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message},
            timeout=10,
        )
        r.raise_for_status()
        return "Telegram message sent"
    except Exception as e:
        return f"Telegram failed: {e}"


def send_email(subject: str, body: str) -> str:
    api_key = os.getenv("RESEND_API_KEY", "")
    from_addr = os.getenv("SMTP_FROM", "")
    to_addr = os.getenv("SMTP_TO", "")
    if not api_key or api_key == "re_your_key_here":
        return "Resend not configured — skipping email"
    try:
        import requests as req
        r = req.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"from": from_addr, "to": [to_addr], "subject": subject, "text": body},
            timeout=10,
        )
        r.raise_for_status()
        return f"Email sent: {subject}"
    except Exception as e:
        return f"Resend failed: {e}"


# ── Reminders ─────────────────────────────────────────────────────────────────

def schedule_reminder(message: str, send_at: str, channel: str = "telegram") -> str:
    r = _post("/reminders", {"message": message, "send_at": send_at, "channel": channel})
    return f"Reminder scheduled for {send_at}: {message}"


# ── Weekly archive ────────────────────────────────────────────────────────────

def save_weekly_entry(entry_type: str, content: str, week: str = None) -> str:
    body = {"type": entry_type, "content": content}
    if week:
        body["week"] = week
    _post("/weekly", body)
    return f"Weekly {entry_type} entry saved."


# ── Briefing + Status (aggregate from individual endpoints — NOT /api/agent) ──

def get_daily_briefing() -> str:
    from datetime import date
    today = date.today().isoformat()

    tasks = _get("/tasks")["tasks"]
    spoc = _get("/spoc")["spoc_log"]
    projects = _get("/projects")["projects"]
    team = _get("/team")["team"]

    open_tasks = [t for t in tasks if not t.get("done")]
    high_tasks = [t for t in open_tasks if t.get("priority") == "high"]
    urgent_spoc = [e for e in spoc if e.get("status") == "urgent"]
    blocked_proj = [p for p in projects if p.get("status") == "blocked"]
    low_health = [m for m in team if m.get("health", 10) <= 5]

    lines = [
        "╔══════════════════════════════════════════════════════╗",
        f"║  DAILY BRIEFING — {today}                     ║",
        "╚══════════════════════════════════════════════════════╝",
        "",
        f"📋 TASKS: {len(open_tasks)} open, {len(high_tasks)} high-priority",
    ]
    for t in high_tasks:
        lines.append(f"  🔴 {t['text']} ({t.get('tag','')})")

    lines.append(f"\n🏢 SPOC: {len(urgent_spoc)} urgent items")
    for e in urgent_spoc:
        lines.append(f"  ⚡ {e['title']}")

    lines.append(f"\n🗂  PROJECTS:")
    status_icons = {"ontrack": "✅", "atrisk": "⚠️", "blocked": "🔴", "done": "🏁"}
    for p in projects:
        icon = status_icons.get(p.get("status", ""), "❓")
        prog = p.get("progress", 0)
        bar = "█" * (prog // 10) + "░" * (10 - prog // 10)
        lines.append(f"  {icon} {p['name']:30} {bar} {prog}%")

    lines.append(f"\n👥 TEAM: {len(low_health)} need attention")
    for m in low_health:
        h = m.get("health", 0)
        lines.append(f"  ⚠️  {m['name']} — health {h}/10")
        notes = m.get("notes", [])
        if notes:
            lines.append(f"      {notes[0]}")

    return "\n".join(lines)


def get_status() -> str:
    tasks = _get("/tasks")["tasks"]
    spoc = _get("/spoc")["spoc_log"]
    projects = _get("/projects")["projects"]
    team = _get("/team")["team"]

    open_t = sum(1 for t in tasks if not t.get("done"))
    urgent_s = sum(1 for e in spoc if e.get("status") == "urgent")
    blocked_p = sum(1 for p in projects if p.get("status") == "blocked")
    low_h = sum(1 for m in team if m.get("health", 10) <= 5)

    return (
        f"Workspace status: {open_t} open tasks | {urgent_s} urgent SPOC | "
        f"{blocked_p} blocked projects | {low_h} team members need attention"
    )


# ── Dispatcher ────────────────────────────────────────────────────────────────

def run(action: str, **kwargs) -> str:
    dispatch = {
        "add_task": add_task,
        "complete_task": complete_task,
        "delete_task": delete_task,
        "list_tasks": list_tasks,
        "update_health": update_health,
        "add_member_note": add_member_note,
        "get_team_status": get_team_status,
        "add_spoc_log": add_spoc_log,
        "update_spoc_status": update_spoc_status,
        "get_spoc_summary": get_spoc_summary,
        "update_project": update_project,
        "update_milestone": update_milestone,
        "get_project_summary": get_project_summary,
        "send_telegram": send_telegram,
        "send_email": send_email,
        "get_daily_briefing": get_daily_briefing,
        "schedule_reminder": schedule_reminder,
        "save_weekly_entry": save_weekly_entry,
        "get_status": get_status,
    }
    fn = dispatch.get(action)
    if fn is None:
        return f"Unknown action '{action}'. Available: {', '.join(dispatch)}"
    return fn(**kwargs)


if __name__ == "__main__":
    print(run("get_daily_briefing"))
