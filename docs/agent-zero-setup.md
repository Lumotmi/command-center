# Agent Zero — Command Center Integration

## What this does

Agent Zero connects to the Command Center REST API running at `http://localhost:5001/api/agent`.
Every workspace action (tasks, team health, SPOC log, projects, reminders) goes through
a single POST endpoint. The agent never reads or writes `data.json` directly.

---

## Prerequisites

```
pip install requests python-dotenv
```

The API must be running:

```bash
cd ~/command-center/core/api
python3 app.py
```

Verify: `curl http://localhost:5001/api/status` → `{"status": "ok", ...}`

---

## System prompt

Load one of the prompts from `~/command-center/prompts/`:

| Model | File |
|---|---|
| Claude Sonnet | `prompts/sonnet.md` |
| Qwen3:14b (Ollama) | `prompts/qwen3-14b.md` |

---

## How actions work

Send a POST to `/api/agent` with `"action"` plus any parameters:

```bash
curl -s -X POST http://localhost:5001/api/agent \
  -H "Content-Type: application/json" \
  -d '{"action": "get_daily_briefing"}'
```

The full action schema (parameters, types, examples) is at:

```
~/command-center/prompts/schema.json
```

---

## workspace_tool.py (Python integration)

`~/command-center/core/agent/workspace_tool.py` is a Python wrapper that calls the API.
Import and call `run()` directly:

```python
import sys
sys.path.insert(0, "/home/ghostcat/command-center/core/agent")
import workspace_tool

print(workspace_tool.run("get_daily_briefing"))
print(workspace_tool.run("add_task", text="Review OMS contract", tag="SPOC", priority="high"))
```

Or run standalone for a quick briefing:

```bash
python3 ~/workspace/workspace_tool.py
```

---

## Environment variables

Copy `.env.example` → `~/workspace/.env` and fill in:

```
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
RESEND_API_KEY=re_your_key
SMTP_FROM=noreply@yourdomain.com
SMTP_TO=you@yourdomain.com
CC_API_BASE=http://localhost:5001/api   # optional override
```

---

## Sensitive data routing

If the user mentions **salary, contract values, Post CH AG acquisition details,
personnel termination, legal matters, or NDA** — do not process via this API.
Redirect to Lumo AI (local-only, air-gapped).

The agent system prompt enforces this automatically.

---

## Dashboard

With the API running, open in browser:

- Main dashboard: `http://localhost:5001/`
- Direct links: `http://localhost:5001/dashboard/team-lead.html`, etc.

All dashboards auto-refresh every 30 seconds from the API.
