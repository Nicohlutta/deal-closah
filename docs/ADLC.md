# ADLC Worksheet — deal-closah

## 1. Scope
**Task:** A sales/GTM agent that finds ideal customers, writes outreach, manages CRM, and builds pitch decks.
**Users:** SDRs, founders, and sales leaders doing outbound GTM.
**Success case:** User inputs "Find SaaS companies in Boston, 50-200 employees" → gets a list of companies with contact details, an outreach email, and a pre-meeting brief — all from one command.
**Out of scope:** Autonomous email sending (human reviews all drafts), CRM sync to Salesforce/HubSpot (manual export only for v1).

## 2. Design
```
user input
    │
    ▼
orchestrator (routes by keyword)
    ├── icp_scout     → skills/icp-profile, skills/event-scout
    ├── outreach      → skills/cold-email
    ├── meeting_intel → skills/meeting-brief
    └── deck_builder  → skills/pitch-deck
```
Model per task:
- ICP search: local (granite4:micro) — structured extraction, fast
- Email drafting: local → strong tier fallback (tone-sensitive)
- Meeting brief: local (structured extraction)
- Pitch deck: strong tier preferred (judgment + creativity)

## 3. Build
- Framework: agentkit (vendored from AgentDay-Example — 4 modules, ~450 lines)
- License: MIT
- Zero required API keys — all agents run on granite4:micro locally
- Four agents, five skills, one orchestrator

## 4. Evaluate ← run this loop at least once
```bash
uv run python -m agentkit.evals evals/icp
uv run python -m agentkit.evals evals/outreach
uv run python -m agentkit.evals evals/meeting
uv run python -m agentkit.evals evals/deck
```
*Fill in benchmark.json results after first run.*

| Agent | With skill | Without skill | Delta |
|-------|-----------|--------------|-------|
| icp-scout    | ?/3 | ?/3 | ? |
| outreach     | ?/3 | ?/3 | ? |
| meeting-intel| ?/3 | ?/3 | ? |
| deck-builder | ?/3 | ?/3 | ? |

## 5. Deploy
```bash
git clone <repo> && cd deal-closah
uv sync
ollama pull granite4:micro
cp .env.example .env
python agent.py "Find SaaS companies in Boston with 50-200 employees"
```

## 6. Observe
Each agent run prints: turns, tokens (prompt+completion), cost ($0.00 local), latency (s), tools called.
*Fill in: one thing a trace taught us during the event.*

## 7. Iterate
*Fill in after first eval run: what changed, what we'd do with day two.*
