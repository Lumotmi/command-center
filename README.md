# Command Center

Command Center is a personal AI-powered workspace OS built for managers. It combines a lightweight REST API, a conversational AI agent, a notification scheduler, and a set of purpose-built dashboards (SPOC, Team Lead, Projects, CRM, Email Analytics, Weekly Rhythm) into a single local-first system — giving you one place to track people, projects, and priorities without a wall of SaaS tabs.

## What you need

- Python 3.10+
- pip3
- Ollama (local LLM) **or** an Anthropic API key

## Setup

1. Clone this repo and `cd command-center`
2. Run `bash setup.sh` — it installs dependencies and scaffolds `~/workspace/`
3. Copy `.env.template` to `~/workspace/.env` and fill in your API key (done automatically by setup.sh if the file is absent)
4. Start the API server: `python3 core/api/app.py`
5. Open any dashboard from `dashboard/` in your browser

## Talking to the agent

The agent understands natural language commands. Examples:

```
"What's on my plate today?"
"Add a follow-up task for the Q3 review with Marco"
"Show me all open items for the Acme project"
"Schedule a weekly check-in reminder every Monday at 9am"
"Summarize my last 5 email threads with the leadership team"
```

Send commands via the REST API (`POST /agent`) or directly through any dashboard UI.
