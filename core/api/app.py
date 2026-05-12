#!/usr/bin/env python3
"""Command Center REST API — single read/write interface for data.json."""

import json
import os
import sys
from datetime import datetime, date
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# ── Paths ──────────────────────────────────────────────────────────────────────
DATA_FILE     = Path.home() / "workspace" / "data.json"
AUDIT_LOG     = Path.home() / "workspace" / "audit.log"
DASHBOARD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "dashboard",
)

# ── workspace_tool import (works from core/api/ or ~/workspace/) ───────────────
for _p in [
    Path(__file__).resolve().parent.parent / "agent",
    Path.home() / "command-center" / "core" / "agent",
]:
    if _p.exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
        break

try:
    import workspace_tool
except ImportError:
    workspace_tool = None

# ── App ────────────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app, origins=["http://localhost", "http://127.0.0.1", "null"],
     supports_credentials=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load() -> dict:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    data["_meta"]["last_updated"] = datetime.utcnow().isoformat() + "Z"
    data["_meta"]["updated_by"] = "command-center-api"
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _audit(method: str, endpoint: str, summary: str) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().isoformat() + "Z"
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(f"{ts} | {method} | {endpoint} | {summary}\n")


def _err(msg: str, status: int = 400):
    return jsonify({"error": msg}), status


def _today() -> str:
    return date.today().isoformat()


def _next_id(items: list) -> int:
    return max((item["id"] for item in items), default=0) + 1


# ── Dashboard static files ────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(DASHBOARD_DIR, "command-center.html")


@app.route("/dashboard/shared/<path:filename>")
def shared_static(filename):
    return send_from_directory(os.path.join(DASHBOARD_DIR, "shared"), filename)


@app.route("/dashboard/<path:filename>")
def dashboard_static(filename):
    return send_from_directory(DASHBOARD_DIR, filename)


# ── Status ────────────────────────────────────────────────────────────────────

@app.route("/api/status")
def api_status():
    data = _load()
    return jsonify({
        "status": "ok",
        "last_updated": data["_meta"]["last_updated"],
        "task_count": len(data.get("tasks", [])),
        "team_count": len(data.get("team", [])),
        "project_count": len(data.get("projects", [])),
    })


# ── Full data ─────────────────────────────────────────────────────────────────

@app.route("/api/data")
def api_data():
    return jsonify(_load())


# ── Tasks ─────────────────────────────────────────────────────────────────────

@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    data = _load()
    tasks = data.get("tasks", [])
    done_filter = request.args.get("done")
    if done_filter is not None:
        want_done = done_filter.lower() not in ("false", "0", "no")
        tasks = [t for t in tasks if t.get("done") == want_done]
    return jsonify({"tasks": tasks})


@app.route("/api/tasks", methods=["POST"])
def create_task():
    body = request.get_json() or {}
    text = body.get("text", "").strip()
    if not text:
        return _err("'text' is required")
    data = _load()
    task = {
        "id": _next_id(data["tasks"]),
        "text": text,
        "tag": body.get("tag", ""),
        "priority": body.get("priority", "medium"),
        "done": False,
        "created": _today(),
    }
    data["tasks"].append(task)
    _save(data)
    _audit("POST", "/api/tasks", f"created task #{task['id']}: {text}")
    return jsonify(task), 201


@app.route("/api/tasks/<int:task_id>", methods=["PATCH"])
def patch_task(task_id):
    body = request.get_json() or {}
    data = _load()
    for t in data["tasks"]:
        if t["id"] == task_id:
            for k in ("text", "tag", "priority", "done"):
                if k in body:
                    t[k] = body[k]
            _save(data)
            _audit("PATCH", f"/api/tasks/{task_id}", f"updated task #{task_id}")
            return jsonify(t)
    return _err(f"Task {task_id} not found", 404)


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    data = _load()
    before = len(data["tasks"])
    data["tasks"] = [t for t in data["tasks"] if t["id"] != task_id]
    if len(data["tasks"]) == before:
        return _err(f"Task {task_id} not found", 404)
    _save(data)
    _audit("DELETE", f"/api/tasks/{task_id}", f"deleted task #{task_id}")
    return jsonify({"deleted": True, "id": task_id})


# ── Team ──────────────────────────────────────────────────────────────────────

@app.route("/api/team")
def get_team():
    return jsonify({"team": _load().get("team", [])})


@app.route("/api/team/<member_id>", methods=["PATCH"])
def patch_team(member_id):
    body = request.get_json() or {}
    data = _load()
    for m in data["team"]:
        if m["id"].lower() == member_id.lower():
            for k in ("health", "lastCheck", "moods"):
                if k in body:
                    m[k] = body[k]
            if "notes" in body:
                note = body["notes"]
                if isinstance(note, str):
                    m.setdefault("notes", []).insert(0, f"{_today()}: {note}")
                else:
                    m["notes"] = note
            _save(data)
            _audit("PATCH", f"/api/team/{member_id}", f"updated member {member_id}")
            return jsonify(m)
    return _err(f"Member '{member_id}' not found", 404)


# ── SPOC ──────────────────────────────────────────────────────────────────────

@app.route("/api/spoc")
def get_spoc():
    data = _load()
    entries = data.get("spoc_log", [])
    status_filter = request.args.get("status")
    if status_filter:
        entries = [e for e in entries if e.get("status") == status_filter]
    return jsonify({"spoc_log": entries})


@app.route("/api/spoc", methods=["POST"])
def create_spoc():
    body = request.get_json() or {}
    title = body.get("title", "").strip()
    if not title:
        return _err("'title' is required")
    data = _load()
    entry = {
        "id": _next_id(data.get("spoc_log", [])),
        "title": title,
        "body": body.get("body", ""),
        "status": body.get("status", "open"),
        "kws": body.get("kws", []),
        "date": _today(),
    }
    data.setdefault("spoc_log", []).append(entry)
    _save(data)
    _audit("POST", "/api/spoc", f"created SPOC #{entry['id']}: {title}")
    return jsonify(entry), 201


@app.route("/api/spoc/<int:entry_id>", methods=["PATCH"])
def patch_spoc(entry_id):
    body = request.get_json() or {}
    data = _load()
    for e in data.get("spoc_log", []):
        if e["id"] == entry_id:
            for k in ("title", "body", "status", "kws"):
                if k in body:
                    e[k] = body[k]
            _save(data)
            _audit("PATCH", f"/api/spoc/{entry_id}", f"updated SPOC #{entry_id}")
            return jsonify(e)
    return _err(f"SPOC entry {entry_id} not found", 404)


# ── Projects ──────────────────────────────────────────────────────────────────

@app.route("/api/projects")
def get_projects():
    return jsonify({"projects": _load().get("projects", [])})


@app.route("/api/projects/<project_id>", methods=["PATCH"])
def patch_project(project_id):
    body = request.get_json() or {}
    data = _load()
    for p in data.get("projects", []):
        if p["id"].lower() == project_id.lower():
            for k in ("status", "progress", "name", "desc", "tags", "color"):
                if k in body:
                    p[k] = body[k]
            if "notes" in body:
                note = body["notes"]
                if isinstance(note, str):
                    p.setdefault("notes", []).insert(0, f"{_today()}: {note}")
                else:
                    p["notes"] = note
            _save(data)
            _audit("PATCH", f"/api/projects/{project_id}", f"updated project {project_id}")
            return jsonify(p)
    return _err(f"Project '{project_id}' not found", 404)


@app.route("/api/projects/<project_id>/milestones", methods=["PATCH"])
def patch_milestone(project_id):
    body = request.get_json() or {}
    milestone_text = body.get("milestone_text", "").strip()
    new_status = body.get("status", "").strip()
    if not milestone_text or not new_status:
        return _err("'milestone_text' and 'status' are required")
    data = _load()
    for p in data.get("projects", []):
        if p["id"].lower() == project_id.lower():
            target = next(
                (m for m in p.get("milestones", [])
                 if milestone_text.lower() in m.get("text", "").lower()),
                None,
            )
            if target is None:
                return _err(f"No milestone matching '{milestone_text}'", 404)
            target["status"] = new_status
            _save(data)
            _audit("PATCH", f"/api/projects/{project_id}/milestones",
                   f"milestone '{milestone_text}' → {new_status}")
            return jsonify(p)
    return _err(f"Project '{project_id}' not found", 404)


# ── Reminders ─────────────────────────────────────────────────────────────────

@app.route("/api/reminders")
def get_reminders():
    data = _load()
    reminders = data.get("reminders", [])
    sent_filter = request.args.get("sent")
    if sent_filter is not None:
        want_sent = sent_filter.lower() not in ("false", "0", "no")
        reminders = [r for r in reminders if r.get("sent") == want_sent]
    return jsonify({"reminders": reminders})


@app.route("/api/reminders", methods=["POST"])
def create_reminder():
    body = request.get_json() or {}
    message = body.get("message", "").strip()
    send_at = body.get("send_at", "").strip()
    if not message or not send_at:
        return _err("'message' and 'send_at' are required")
    data = _load()
    reminders = data.setdefault("reminders", [])
    reminder = {
        "id": _next_id(reminders),
        "message": message,
        "send_at": send_at,
        "channel": body.get("channel", ""),
        "sent": False,
        "created": _today(),
    }
    reminders.append(reminder)
    _save(data)
    _audit("POST", "/api/reminders", f"created reminder #{reminder['id']}: {message}")
    return jsonify(reminder), 201


# ── Weekly archive ────────────────────────────────────────────────────────────

@app.route("/api/weekly")
def get_weekly():
    return jsonify({"weekly_archive": _load().get("weekly_archive", [])})


@app.route("/api/weekly", methods=["POST"])
def create_weekly():
    body = request.get_json() or {}
    content = body.get("content", "").strip()
    if not content:
        return _err("'content' is required")
    data = _load()
    archive = data.setdefault("weekly_archive", [])
    entry = {
        "id": len(archive) + 1,
        "type": body.get("type", "summary"),
        "content": content,
        "week": body.get("week", date.today().isocalendar()[1]),
        "date": _today(),
    }
    archive.insert(0, entry)
    data["weekly_archive"] = archive[:52]
    _save(data)
    _audit("POST", "/api/weekly", f"weekly entry week {entry['week']}")
    return jsonify(entry), 201


# ── Agent ─────────────────────────────────────────────────────────────────────

@app.route("/api/agent", methods=["POST"])
def agent():
    if workspace_tool is None:
        return _err("workspace_tool not available — check sys.path", 500)
    body = request.get_json() or {}
    action = body.pop("action", "").strip()
    if not action:
        return _err("'action' is required")
    try:
        result = workspace_tool.run(action, **body)
        return jsonify({"result": result})
    except TypeError as e:
        return _err(f"Bad params for action '{action}': {e}", 400)
    except Exception as e:
        return _err(str(e), 500)


# ── Config ────────────────────────────────────────────────────────────────────

@app.route("/api/config")
def api_config():
    return jsonify(_load().get("config", {}))


@app.route("/api/config", methods=["PATCH"])
def patch_config():
    body = request.get_json() or {}
    data = _load()
    cfg = data.setdefault("config", {})
    for k, v in body.items():
        cfg[k] = v
    _save(data)
    _audit("PATCH", "/api/config", "updated config")
    return jsonify(cfg)


# ── Dashboard catch-all (serves /*.html and /shared/* from dashboard/) ────────

@app.route("/<path:filename>")
def root_files(filename):
    if filename.endswith(".html"):
        return send_from_directory(DASHBOARD_DIR, filename)
    if filename.startswith("shared/"):
        return send_from_directory(DASHBOARD_DIR, filename)
    return {"error": "endpoint not found"}, 404


# ── Error handlers ────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return {"error": "endpoint not found"}, 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": str(e)}), 500


# ── Startup ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not DATA_FILE.exists():
        print(f"\nWARNING: {DATA_FILE} not found — run setup.sh first\n")

    print("\nRegistered routes:")
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        methods = ",".join(sorted(m for m in rule.methods if m not in ("HEAD", "OPTIONS")))
        print(f"  {methods:25} {rule.rule}")

    print(f"\nStarting on http://0.0.0.0:5001\n")
    app.run(host="0.0.0.0", port=5001, debug=False)
