#!/usr/bin/env python3
"""Livesystems AG Workspace Tool — Agent Zero integration."""

import json
import os
import sys
from datetime import datetime, date
from pathlib import Path

import requests
from dotenv import load_dotenv

DATA_FILE = Path.home() / "workspace" / "data.json"
ENV_FILE = Path.home() / "workspace" / ".env"
load_dotenv(ENV_FILE)


def _load() -> dict:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    data["_meta"]["last_updated"] = datetime.utcnow().isoformat() + "Z"
    data["_meta"]["updated_by"] = "workspace_tool"
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Tasks ─────────────────────────────────────────────────────────────────────

def add_task(text: str, tag: str = "", priority: str = "medium") -> str:
    data = _load()
    tasks = data["tasks"]
    new_id = max((t["id"] for t in tasks), default=0) + 1
    tasks.append({
        "id": new_id,
        "text": text,
        "tag": tag,
        "done": False,
        "created": date.today().isoformat(),
        "priority": priority,
    })
    _save(data)
    return f"Task #{new_id} added: {text} [{tag}] ({priority})"


def complete_task(task_id: int) -> str:
    data = _load()
    for t in data["tasks"]:
        if t["id"] == task_id:
            t["done"] = True
            _save(data)
            return f"Task #{task_id} marked complete: {t['text']}"
    return f"Task #{task_id} not found"


def delete_task(task_id: int) -> str:
    data = _load()
    before = len(data["tasks"])
    data["tasks"] = [t for t in data["tasks"] if t["id"] != task_id]
    if len(data["tasks"]) < before:
        _save(data)
        return f"Task #{task_id} deleted"
    return f"Task #{task_id} not found"


def list_tasks(tag: str = "", include_done: bool = False) -> str:
    data = _load()
    tasks = data["tasks"]
    if not include_done:
        tasks = [t for t in tasks if not t["done"]]
    if tag:
        tasks = [t for t in tasks if t.get("tag", "").lower() == tag.lower()]
    if not tasks:
        return "No tasks found."
    lines = []
    for t in tasks:
        status = "✅" if t["done"] else "⬜"
        prio = f"[{t['priority'].upper()}]" if t.get("priority") else ""
        lines.append(f"{status} #{t['id']} {prio} {t['text']} ({t.get('tag','')})")
    return "\n".join(lines)


# ── Team ──────────────────────────────────────────────────────────────────────

def update_team_health(member_id: str, health: int) -> str:
    data = _load()
    for m in data["team"]:
        if m["id"].lower() == member_id.lower():
            m["health"] = max(1, min(10, health))
            m["lastCheck"] = date.today().isoformat()
            _save(data)
            return f"Updated {m['name']} health to {health}/10"
    return f"Member '{member_id}' not found"


def add_member_note(member_id: str, note: str) -> str:
    data = _load()
    for m in data["team"]:
        if m["id"].lower() == member_id.lower():
            m.setdefault("notes", []).append(note)
            _save(data)
            return f"Note added to {m['name']}: {note}"
    return f"Member '{member_id}' not found"


def get_team_status() -> str:
    data = _load()
    lines = ["Team health snapshot:"]
    for m in data["team"]:
        bar = "█" * m["health"] + "░" * (10 - m["health"])
        notes = f" ⚠ {m['notes'][-1]}" if m.get("notes") else ""
        lines.append(f"  {m['avatar']} {m['name']:15} {bar} {m['health']}/10{notes}")
    return "\n".join(lines)


# ── SPOC log ──────────────────────────────────────────────────────────────────

def add_spoc_log(title: str, body: str, status: str = "open", kws: list = None) -> str:
    data = _load()
    entries = data["spoc_log"]
    new_id = max((e["id"] for e in entries), default=0) + 1
    entries.append({
        "id": new_id,
        "title": title,
        "body": body,
        "status": status,
        "date": date.today().isoformat(),
        "kws": kws or [],
    })
    _save(data)
    return f"SPOC entry #{new_id} logged: {title} [{status}]"


def update_spoc_status(entry_id: int, status: str) -> str:
    data = _load()
    for e in data["spoc_log"]:
        if e["id"] == entry_id:
            e["status"] = status
            _save(data)
            return f"SPOC #{entry_id} status → {status}"
    return f"SPOC entry #{entry_id} not found"


def get_spoc_summary() -> str:
    data = _load()
    entries = data["spoc_log"]
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
    data = _load()
    for p in data["projects"]:
        if p["id"].lower() == project_id.lower():
            if status:
                p["status"] = status
            if progress is not None:
                p["progress"] = max(0, min(100, progress))
            if note:
                p.setdefault("notes", []).append(note)
            _save(data)
            return f"Project '{p['name']}' updated: status={p['status']}, progress={p['progress']}%"
    return f"Project '{project_id}' not found"


def update_milestone(project_id: str, milestone: str) -> str:
    return update_project(project_id, note=f"Milestone: {milestone}")


def get_project_summary() -> str:
    data = _load()
    status_icons = {"ontrack": "✅", "atrisk": "⚠️", "blocked": "🔴", "done": "🏁"}
    lines = ["Projects:"]
    for p in data["projects"]:
        icon = status_icons.get(p["status"], "❓")
        bar = "█" * (p["progress"] // 10) + "░" * (10 - p["progress"] // 10)
        lines.append(f"  {icon} {p['name']:30} {bar} {p['progress']}%")
        if p.get("notes"):
            lines.append(f"     └ {p['notes'][-1]}")
    return "\n".join(lines)


# ── Comms ─────────────────────────────────────────────────────────────────────

def send_telegram(text: str) -> bool:
    token = os.getenv("TELEGRAM_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or token == "your_bot_token_here":
        print("Telegram not configured — skipping")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"Telegram failed: {e}")
        return False


def send_email(subject: str, body: str) -> bool:
    api_key = os.getenv("RESEND_API_KEY", "")
    from_addr = os.getenv("SMTP_FROM", "")
    to_addr = os.getenv("SMTP_TO", "")
    if not api_key or api_key == "re_your_key_here":
        print("Resend not configured — skipping email")
        return False
    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"from": from_addr, "to": [to_addr], "subject": subject, "text": body},
            timeout=10,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"Resend failed: {e}")
        return False


# ── Briefing ──────────────────────────────────────────────────────────────────

def get_daily_briefing() -> str:
    data = _load()
    today = date.today().isoformat()

    open_tasks = [t for t in data["tasks"] if not t["done"]]
    high_tasks = [t for t in open_tasks if t.get("priority") == "high"]
    urgent_spoc = [e for e in data["spoc_log"] if e["status"] == "urgent"]
    blocked_proj = [p for p in data["projects"] if p["status"] == "blocked"]
    low_health = [m for m in data["team"] if m["health"] <= 5]

    lines = [
        f"╔══════════════════════════════════════════════════════╗",
        f"║  DAILY BRIEFING — {today}                     ║",
        f"╚══════════════════════════════════════════════════════╝",
        "",
        f"📋 TASKS: {len(open_tasks)} open, {len(high_tasks)} high-priority",
    ]
    for t in high_tasks:
        lines.append(f"  🔴 {t['text']} ({t.get('tag','')})")

    lines.append(f"\n🏢 SPOC: {len(urgent_spoc)} urgent items")
    for e in urgent_spoc:
        lines.append(f"  ⚡ {e['title']}")

    lines.append(f"\n🗂  PROJECTS:")
    lines.append(get_project_summary())

    lines.append(f"\n👥 TEAM: {len(low_health)} need attention")
    for m in low_health:
        lines.append(f"  ⚠️  {m['name']} — health {m['health']}/10")
        if m.get("notes"):
            lines.append(f"      {m['notes'][-1]}")

    return "\n".join(lines)


# ── Reminders ─────────────────────────────────────────────────────────────────

def schedule_reminder(text: str, send_at: str) -> str:
    data = _load()
    data.setdefault("reminders", []).append({
        "text": text,
        "send_at": send_at,
        "sent": False,
        "created": date.today().isoformat(),
    })
    _save(data)
    return f"Reminder scheduled for {send_at}: {text}"


# ── Weekly archive ────────────────────────────────────────────────────────────

def save_weekly_entry(summary: str) -> str:
    data = _load()
    data.setdefault("weekly_archive", []).append({
        "week": date.today().isocalendar()[1],
        "year": date.today().year,
        "date": date.today().isoformat(),
        "summary": summary,
    })
    _save(data)
    return "Weekly entry saved."


# ── Status ────────────────────────────────────────────────────────────────────

def get_status() -> str:
    data = _load()
    open_t = sum(1 for t in data["tasks"] if not t["done"])
    urgent_s = sum(1 for e in data["spoc_log"] if e["status"] == "urgent")
    blocked_p = sum(1 for p in data["projects"] if p["status"] == "blocked")
    low_h = sum(1 for m in data["team"] if m["health"] <= 5)
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
        "update_team_health": update_team_health,
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
        "save_weekly_entry": save_weekly_entry,
        "schedule_reminder": schedule_reminder,
        "get_status": get_status,
    }
    fn = dispatch.get(action)
    if fn is None:
        return f"Unknown action '{action}'. Available: {', '.join(dispatch)}"
    return fn(**kwargs)


if __name__ == "__main__":
    print(run("get_daily_briefing"))
