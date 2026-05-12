# Agent Command Reference

Natural language examples mapped to workspace_tool actions and the API calls they make.
Send any command to `POST /api/agent` with `{"action": "<action>", ...params}`.

Discover all available actions at runtime: `GET /api/agent/actions`

## Command examples

| Natural language | Action | API call |
|---|---|---|
| "What's on my plate today?" | `get_daily_briefing` | `GET /api/tasks` · `GET /api/spoc` · `GET /api/projects` · `GET /api/team` |
| "Show me all open tasks" | `list_open_tasks` | `GET /api/tasks?done=false` |
| "Add a task: follow up with Marco on Q3 review" | `add_task` | `POST /api/tasks` `{text, tag, priority}` |
| "Mark the HubSpot onboarding task as done" | `complete_task` | `PATCH /api/tasks/{id}` `{done: true}` |
| "How is the team doing?" | `get_team_status` | `GET /api/team` |
| "Set Alina's health to 6, she seems stressed" | `update_team_health` | `PATCH /api/team/lk` `{health: 6}` |
| "Add a note for Marco: discussed Q3 targets today" | `add_member_note` | `PATCH /api/team/mb` `{notes: "..."}` |
| "Log a SPOC note: Post CH AG requested timeline update by Friday" | `log_spoc_note` | `POST /api/spoc` `{title, body, status: "open"}` |
| "Mark SPOC entry 3 as urgent" | `update_spoc_status` | `PATCH /api/spoc/3` `{status: "urgent"}` |
| "The OMS project is blocked — infrastructure access still pending" | `add_blocker` | `PATCH /api/projects/oms` `{notes: "BLOCKER: ..."}` |
| "Set HubSpot progress to 65%" | `update_project` | `PATCH /api/projects/hubspot` `{progress: 65}` |
| "Mark the HubSpot kickoff milestone as done" | `update_milestone` | `PATCH /api/projects/hubspot/milestones` `{milestone_text, status: "done"}` |
| "Show me all projects" | `get_project_summary` | `GET /api/projects` |
| "Remind me to prep for Monday standup at 08:00 tomorrow" | `schedule_reminder` | `POST /api/reminders` `{message, send_at, channel}` |
| "Save my Friday lookback: shipped the config refactor, team in good shape" | `save_weekly_entry` | `POST /api/weekly` `{type: "friday", content, week}` |

## Param reference

```
add_task            text* tag priority
complete_task       task_id | text_match
list_open_tasks     —
delete_task         task_id*
update_team_health  member* health* note
add_member_note     member* note*
get_team_status     —
log_spoc_note       title* body* status
add_spoc_log        title* body* status keywords
update_spoc_status  entry_id* status*
get_spoc_summary    —
add_blocker         project_id* blocker*
update_project      project_id* status progress note
update_milestone    project_id* milestone_text* status*
get_project_summary —
schedule_reminder   message* send_at* channel
save_weekly_entry   entry_type* content* week
send_telegram       message*
send_email          subject* body*
get_daily_briefing  —
get_status          —
```

`*` = required · all others optional
