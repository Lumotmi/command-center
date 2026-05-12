# Command Center

A personal AI-powered workspace OS for managers. One REST API, a conversational agent, a notification scheduler, and six purpose-built dashboards — all running locally, no SaaS required.

## Quick start

```bash
git clone https://github.com/Lumotmi/command-center.git
cd command-center
chmod +x setup.sh && ./setup.sh
```

That's it. `setup.sh` installs dependencies, scaffolds `~/workspace/`, starts the API server, and opens the onboarding wizard in your browser.

## Architecture

```
command-center/
├── core/
│   ├── api/
│   │   └── app.py          ← Flask REST API  (port 5001)
│   ├── agent/
│   │   └── workspace_tool.py  ← Agent action dispatcher
│   └── scheduler/
│       └── scheduler.py    ← Reminder & cron jobs
├── dashboard/
│   ├── command-center.html ← Home / space navigator
│   ├── team-lead.html      ← Team health & 1:1s
│   ├── project-hub.html    ← Project tracker
│   ├── spoc-hub.html       ← SPOC communication log
│   ├── crm-hubspot.html    ← CRM / HubSpot overlay
│   ├── email-analytics.html← Email metrics
│   ├── weekly-rhythm.html  ← Friday lookback / Monday outlook
│   ├── onboarding.html     ← First-run setup wizard
│   └── shared/
│       ├── api.js          ← Fetch wrapper for all API calls
│       └── styles.css
├── docs/
│   └── agent-zero-setup.md ← Agent Zero integration guide
├── config.example.json     ← Seeded into ~/workspace/data.json
├── config.schema.json      ← Full data.json contract (types + constraints)
├── .env.template           ← Seeded into ~/workspace/.env
└── setup.sh                ← One-command setup

~/workspace/               ← Runtime data (gitignored)
├── data.json              ← Live store: tasks, team, projects, SPOC, config
├── .env                   ← API keys and service config
├── api.pid                ← PID of the running server
└── api.log                ← Server stdout/stderr
```

```
Browser → dashboard HTML
             │
             └── shared/api.js ──► Flask API (:5001)
                                       │
                              ┌────────┴────────┐
                              │                 │
                        ~/workspace/       Ollama / Anthropic
                          data.json          (AI inference)
```

## What the dashboards do

| Dashboard | Purpose |
|---|---|
| Command Center | Home page — space navigator with live badges |
| Team Lead | Health scores, 1:1 notes, check-in cadence |
| Project Hub | Status, progress bars, milestone tracker |
| SPOC Hub | Communication log with keyword extraction |
| CRM / HubSpot | CRM project overlay and email pipeline |
| Email Analytics | Team communication metrics |
| Weekly Rhythm | Friday lookback and Monday outlook with AI summary |

## Talking to the agent

Send natural language via the dashboard chat or directly:

```bash
curl -s -X POST http://localhost:5001/api/agent \
  -H "Content-Type: application/json" \
  -d '{"message": "What is on my plate today?"}'
```

Examples:
- `"Add a follow-up task for the Q3 review with Marco"`
- `"Mark the HubSpot milestone as done"`
- `"Schedule a reminder: Monday standup prep at 08:30"`
- `"Show all open SPOC items"`
- `"How is the team doing this week?"`

For Agent Zero integration see [docs/agent-zero-setup.md](docs/agent-zero-setup.md).

## Configuration

All workspace configuration lives in `~/workspace/data.json` under the `config` key and is served by `GET /api/config`. Change values there or via the onboarding wizard — no server restart needed.

Key fields:

| Key | Description |
|---|---|
| `config.org` | Organisation name shown in dashboards |
| `config.ollama_base` | Ollama server URL (default `http://localhost:11434`) |
| `config.spaces` | Ordered list of space cards on the home page |

## Troubleshooting

**Port 5001 already in use**
```bash
fuser -k 5001/tcp && python3 core/api/app.py
```

**Ollama not found / AI calls fail**
- Install Ollama: https://ollama.com/download
- Pull a model: `ollama pull qwen3:14b`
- Or switch to Anthropic: set `ANTHROPIC_API_KEY` in `~/workspace/.env` and choose a cloud model in the onboarding wizard

**`~/workspace/data.json` missing or corrupt**
```bash
cp config.example.json ~/workspace/data.json
```
Then restart the server. All dashboard state will reset to example values.

**Server won't start — check the log**
```bash
cat ~/workspace/api.log
```

**Restart the server**
```bash
kill $(cat ~/workspace/api.pid) 2>/dev/null; python3 core/api/app.py > ~/workspace/api.log 2>&1 &
```
