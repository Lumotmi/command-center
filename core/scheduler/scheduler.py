#!/usr/bin/env python3
"""Livesystems AG Workspace Scheduler — automated reminders and briefings."""

import json
import logging
import os
from datetime import datetime, date
from pathlib import Path

import requests
import schedule
import time
from dotenv import load_dotenv

ENV_FILE = Path.home() / "workspace" / ".env"
DATA_FILE = Path.home() / "workspace" / "data.json"
LOG_FILE = Path.home() / "workspace" / "scheduler.log"

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


def send_telegram(text: str) -> bool:
    token = os.getenv("TELEGRAM_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or token == "your_bot_token_here":
        log.warning("Telegram not configured — skipping")
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
    api_key = os.getenv("RESEND_API_KEY", "")
    from_addr = os.getenv("SMTP_FROM", "")
    to_addr = os.getenv("SMTP_TO", "")
    if not api_key or api_key == "re_your_key_here":
        log.warning("Resend not configured — skipping email")
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


def _load_data() -> dict:
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error(f"Failed to load data.json: {e}")
        return {}


def _save_data(data: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def process_due_reminders() -> None:
    data = _load_data()
    now = datetime.now()
    changed = False
    for r in data.get("reminders", []):
        if r.get("sent"):
            continue
        try:
            due = datetime.fromisoformat(r["send_at"])
            if now >= due:
                send_telegram(f"⏰ Reminder: {r['text']}")
                r["sent"] = True
                changed = True
        except Exception as e:
            log.error(f"Reminder parse error: {e}")
    if changed:
        _save_data(data)


def morning_briefing() -> None:
    data = _load_data()
    today = date.today().isoformat()

    open_tasks = [t for t in data.get("tasks", []) if not t.get("done")]
    high_tasks = [t for t in open_tasks if t.get("priority") == "high"]
    urgent_spoc = [e for e in data.get("spoc_log", []) if e.get("status") == "urgent"]
    low_health = [m for m in data.get("team", []) if m.get("health", 10) <= 5]

    lines = [f"\U0001f305 Good morning! Daily briefing {today}"]
    lines.append(f"\U0001f4cb {len(open_tasks)} open tasks, {len(high_tasks)} high-priority")
    for t in high_tasks[:3]:
        lines.append(f"  \U0001f534 {t['text']}")
    if urgent_spoc:
        lines.append(f"⚡ {len(urgent_spoc)} urgent SPOC items")
        for e in urgent_spoc[:2]:
            lines.append(f"  • {e['title']}")
    if low_health:
        lines.append(f"\U0001f465 {len(low_health)} team member(s) need attention")
        for m in low_health:
            lines.append(f"  ⚠️ {m['name']} ({m['health']}/10)")

    send_telegram("\n".join(lines))
    log.info("Morning briefing sent")


def monday_outlook_reminder() -> None:
    if date.today().weekday() != 0:
        return
    send_telegram(
        "\U0001f4c5 Monday 07:30 — Start of week!\n"
        "Open Command Center and set your weekly goals.\n"
        "http://localhost:8080/command-center.html"
    )
    log.info("Monday outlook sent")


def friday_lookback_reminder() -> None:
    if date.today().weekday() != 4:
        return
    send_telegram(
        "\U0001f3c1 Friday 16:30 — End of week!\n"
        "Complete your weekly lookback and archive the week.\n"
        "http://localhost:8080/weekly-rhythm.html"
    )
    log.info("Friday lookback sent")


def wednesday_team_checkin() -> None:
    if date.today().weekday() != 2:
        return
    data = _load_data()
    low_health = [m for m in data.get("team", []) if m.get("health", 10) <= 6]
    msg = "\U0001f465 Wednesday check-in reminder — how is your team doing?\n"
    if low_health:
        msg += f"⚠️ Needs attention: {', '.join(m['name'] for m in low_health)}"
    else:
        msg += "All team members look healthy ✅"
    send_telegram(msg)
    log.info("Wednesday team check-in sent")


def main() -> None:
    log.info("Scheduler starting up…")

    send_telegram(
        "\U0001f916 Livesystems AG scheduler is online.\n"
        "Daily briefing: 08:00 | Reminders: checked every minute"
    )

    schedule.every(1).minutes.do(process_due_reminders)
    schedule.every().day.at("08:00").do(morning_briefing)
    schedule.every().monday.at("07:30").do(monday_outlook_reminder)
    schedule.every().friday.at("16:30").do(friday_lookback_reminder)
    schedule.every().wednesday.at("09:00").do(wednesday_team_checkin)

    log.info("Scheduled jobs active. Running…")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
