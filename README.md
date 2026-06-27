# deal-closah — sales & GTM multi-agent system

**TOA Agent Build Day · June 27, 2026 · Lane 3**

*Four cooperating agents. Five skills. Zero cold leads left untouched.*

A hub-and-spoke sales intelligence system: find your ideal customers, write personalized outreach, manage your CRM, and walk into every meeting with a sharp brief and a 7-slide deck — all from the command line, all local by default.

## Agents

| Agent | Owner | Does |
|-------|-------|------|
| `orchestrator` | Nicholas | Routes tasks to the right specialist |
| `icp_scout` | Nicholas | Finds companies (SerpAPI/Google), events, decision makers |
| `outreach` | Nicholas | Drafts cold emails, follow-ups, event outreach |
| `meeting_intel` | Deepthi | Logs meeting notes, generates pre-meeting briefs, CRM |
| `deck_builder` | Arman | Builds 7-slide pitch decks |

## Skills

| Skill | Owner | Validates |
|-------|-------|-----------|
| `icp-profile` | Nicholas | ICP search output format |
| `event-scout` | Nicholas | Event finding + pre-event outreach |
| `cold-email` | Nicholas | Awareness-stage outreach framework (No-Dump Rule) |
| `meeting-brief` | Deepthi | Pre-meeting brief + notes extraction |
| `pitch-deck` | Arman | 7-slide deck structure |

## Quick start

```bash
git clone https://github.com/Nicohlutta/deal-closah && cd deal-closah
uv sync
ollama pull granite4:micro          # ~2 GB local model
cp .env.example .env

# Find ICP companies
python agent.py "Find B2B SaaS companies in Boston, 50-200 employees, target VP Sales"

# Write outreach
python agent.py "Write a cold email to Acme Corp, contact Jane Chen"

# Log meeting notes
python agent.py "Log meeting notes for Acme Corp 2026-06-27: <paste notes>"

# Pre-meeting brief
python agent.py "Generate pre-meeting brief for Acme Corp"

# Build a pitch deck
python agent.py "Build a pitch deck for Acme Corp"

# Find events
python agent.py "Find events my ICP attends in the Boston fintech space"

# CRM overview
python agent.py --crm

# Eval baseline (no skill)
python agent.py "..." --no-skill

# Offline mode (fixtures only)
python agent.py "..." --offline
```

## Architecture

```
user input
    │
    ▼
orchestrator.py   (Nicholas — routes by intent keyword)
    ├── icp_scout.py      → skills/icp-profile, skills/event-scout
    ├── outreach.py       → skills/cold-email
    ├── meeting_intel.py  → skills/meeting-brief
    └── deck_builder.py   → skills/pitch-deck
```

Data flows through `interfaces.py` (CompanyProfile, OutreachRecord, MeetingNote, PitchDeck) and persists to `data/`.

## File ownership (no merge conflicts)

Each teammate owns exactly one agent file and their skill directories:

| File | Owner |
|------|-------|
| `agents/orchestrator.py` | Nicholas |
| `agents/icp_scout.py` + `skills/icp-profile/` + `skills/event-scout/` | Teammate 1 |
| `agents/outreach.py` + `skills/cold-email/` | Teammate 2 |
| `agents/meeting_intel.py` + `skills/meeting-brief/` | Deepthi |
| `agents/deck_builder.py` + `skills/pitch-deck/` | Arman |
| `interfaces.py`, `agent.py`, `docs/` | Nicholas (shared) |
| `app/` (frontend — 4-page web UI) | Jon Paul |

## Run evals

```bash
uv run python -m agentkit.evals evals/icp
uv run python -m agentkit.evals evals/outreach
uv run python -m agentkit.evals evals/meeting
uv run python -m agentkit.evals evals/deck
```

## Tech stack

- **Model framework:** agentkit (vendored, 4 modules, ~450 lines)
- **Local model:** granite4:micro via Ollama (zero cost, fully offline)
- **Frontier (optional):** Claude Sonnet 4.6 / Opus 4.8 via `MODEL_PROVIDER=anthropic`
- **Data sources:** SerpAPI (Google search, 100 free/mo), Hunter.io (email verify, 25/mo free)
- **Storage:** JSON files in `data/` (no database dependency)
- **Language:** Python 3.11+, managed by uv

## License

MIT
