#!/usr/bin/env python3
"""Livesystems AG Workspace Scheduler — automated reminders and weekly rhythm nudges."""

import json
import logging
import os
import time
from datetime import datetime, date
from pathlib import Path

import requests
import schedule
from dotenv import load_dotenv

ENV_FILE   = Path.home() / "workspace" / ".env"
LOG_FILE   = Path.home() / "workspace" / "scheduler.log"
TICK_FILE  = Path.home() / "workspace" / "scheduler_tick.json"
API_BASE   = os.getenv("CC_API_BASE", "http://localhost:5001/api")

load_dotenv(ENV_FILE)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ── Tick tracking ─────────────────────────────────────────────────────────────

def _write_tick() -> None:
    TICK_FILE.write_text(
        json.dumps({"last_tick": datetime.now().isoformat()}),
        encoding="utf-8",
    )


# ── Notification helpers ───────────────────────────────────────────────────────

def send_telegram(text: str) -> bool:
    token = os.getenv("TELEGRAM_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or token == "your_bot_token_here":
        log.debug("Telegram not configured — skipping")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        r.raise_for_status()
        log.info(f"Telegram sent: {text[:60]}")
        return True
    except Exception as e:
        log.error(f"Telegram failed: {e}")
        return False


def send_email(subject: str, body: str) -> bool:
    api_key  = os.getenv("RESEND_API_KEY", "")
    from_addr = os.getenv("SMTP_FROM", "")
    to_addr  = os.getenv("SMTP_TO", "")
    if not api_key or api_key == "re_your_key_here":
        log.debug("Resend not configured — skipping email")
        return False
    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"from": from_addr, "to": [to_addr], "subject": subject, "text": body},
            timeout=10,
        )
        r.raise_for_status()
        log.info(f"Resend email sent: {subject}")
        return True
    except Exception as e:
        log.error(f"Resend failed: {e}")
        return False


def _dispatch(reminder: dict) -> None:
    """Fire a reminder via its configured channel."""
    msg     = reminder.get("message", "")
    channel = reminder.get("channel", "")
    if channel in ("telegram", "both"):
        send_telegram(f"⏰ Reminder: {msg}")
    if channel in ("email", "both"):
        send_email("Reminder", msg)
    if not channel:
        log.info(f"Reminder #{reminder.get('id')} (no channel): {msg}")


# ── Core poll loop ────────────────────────────────────────────────────────────

def process_due_reminders() -> None:
    """Poll GET /api/reminders?sent=false, dispatch and mark due reminders sent."""
    _write_tick()
    try:
        resp = requests.get(f"{API_BASE}/reminders", params={"sent": "false"}, timeout=10)
        resp.raise_for_status()
        reminders = resp.json().get("reminders", [])
    except Exception as e:
        log.error(f"Failed to fetch reminders: {e}")
        return

    now = datetime.now()
    for r in reminders:
        try:
            due = datetime.fromisoformat(r["send_at"])
        except Exception:
            log.warning(f"Reminder #{r.get('id')} has unparseable send_at: {r.get('send_at')}")
            continue
        if now < due:
            continue
        log.info(f"Due reminder #{r['id']}: {r.get('message', '')}")
        _dispatch(r)
        try:
            requests.patch(
                f"{API_BASE}/reminders/{r['id']}",
                json={"sent": True},
                timeout=10,
            ).raise_for_status()
        except Exception as e:
            log.error(f"Failed to mark reminder #{r['id']} sent: {e}")


# ── Weekly rhythm nudges ──────────────────────────────────────────────────────

def _post_rhythm_nudge() -> None:
    """POST an immediate reminder entry for the weekly rhythm entry prompt."""
    try:
        requests.post(
            f"{API_BASE}/reminders",
            json={
                "message": "Time for your weekly rhythm entry",
                "send_at":  datetime.now().isoformat(),
                "channel":  "",
            },
            timeout=10,
        ).raise_for_status()
        log.info("Weekly rhythm nudge posted to reminders")
    except Exception as e:
        log.error(f"Failed to post rhythm nudge: {e}")


def friday_rhythm_nudge() -> None:
    if date.today().weekday() != 4:
        return
    _post_rhythm_nudge()


def monday_rhythm_nudge() -> None:
    if date.today().weekday() != 0:
        return
    _post_rhythm_nudge()


# ── Other scheduled jobs ──────────────────────────────────────────────────────

def morning_briefing() -> None:
    try:
        tasks    = requests.get(f"{API_BASE}/tasks",  params={"done": "false"}, timeout=10).json().get("tasks", [])
        spoc_log = requests.get(f"{API_BASE}/spoc",   timeout=10).json().get("spoc_log", [])
        team     = requests.get(f"{API_BASE}/team",   timeout=10).json().get("team", [])
    except Exception as e:
        log.error(f"Morning briefing fetch failed: {e}")
        return

    high_tasks   = [t for t in tasks    if t.get("priority") == "high"]
    urgent_spoc  = [e for e in spoc_log if e.get("status")   == "urgent"]
    low_health   = [m for m in team     if m.get("health", 10) <= 5]

    lines = [f"🌅 Good morning! Daily briefing {date.today().isoformat()}"]
    lines.append(f"📋 {len(tasks)} open tasks, {len(high_tasks)} high-priority")
    for t in high_tasks[:3]:
        lines.append(f"  🔴 {t['text']}")
    if urgent_spoc:
        lines.append(f"⚡ {len(urgent_spoc)} urgent SPOC item(s)")
        for e in urgent_spoc[:2]:
            lines.append(f"  • {e['title']}")
    if low_health:
        lines.append(f"👥 {len(low_health)} team member(s) need attention")
        for m in low_health:
            lines.append(f"  ⚠️ {m['name']} ({m['health']}/10)")

    send_telegram("\n".join(lines))
    log.info("Morning briefing sent")


def wednesday_team_checkin() -> None:
    if date.today().weekday() != 2:
        return
    try:
        team = requests.get(f"{API_BASE}/team", timeout=10).json().get("team", [])
    except Exception as e:
        log.error(f"Team check-in fetch failed: {e}")
        return
    low_health = [m for m in team if m.get("health", 10) <= 6]
    msg = "👥 Wednesday check-in reminder — how is your team doing?\n"
    msg += (f"⚠️ Needs attention: {', '.join(m['name'] for m in low_health)}"
            if low_health else "All team members look healthy ✅")
    send_telegram(msg)
    log.info("Wednesday team check-in sent")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    log.info("Scheduler starting up…")
    _write_tick()

    schedule.every(60).seconds.do(process_due_reminders)
    schedule.every().day.at("08:00").do(morning_briefing)
    schedule.every().friday.at("17:00").do(friday_rhythm_nudge)
    schedule.every().monday.at("08:00").do(monday_rhythm_nudge)
    schedule.every().wednesday.at("09:00").do(wednesday_team_checkin)

    log.info("Scheduled jobs active. Running…")
    while True:
        schedule.run_pending()
        time.sleep(15)


if __name__ == "__main__":
    main()
