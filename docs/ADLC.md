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
| icp-scout    | 3/3 | 1/3 | **+0.67** |
| outreach     | 3/3 | 2/3 | **+0.33** *(skill bans "quick call" CTA; base model uses it)* |
| meeting-intel| TBD | TBD | TBD |
| deck-builder | TBD | TBD | TBD |

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

Key trace observations:
- **ICP scout** evaluated import-time env var bug: `OFFLINE = os.getenv(...)` evaluated at module load — fixed with `_use_fixtures()` helper that checks at call time.
- **Cascade routing**: granite4:micro self-grades 0.90–1.00 on outreach tasks; threshold set to 0.90. `[cascade] resolved locally` appears on most runs, preserving $0 cost.
- **SerpAPI → fixtures fallback**: `_SERP_LIMIT = 20` rate guard + 2–5s jitter prevents API hammering during demos.
- **Skill delta on ICP**: without-skill model hallucinated "Adverity" (training knowledge) instead of returning fixture data. With skill, the model follows the workflow and returns only fixture-matched companies.

## 7. Iterate
What changed after first eval run:
- Added `_use_fixtures()` call-time check (was import-time, broke `--offline` flag)
- Fixed Anthropic compat: `json_object` response_format rejected; now skipped for Anthropic provider
- Added code-fence stripping in orchestrator classify (Claude returns ` ```json ``` ` without json_mode)
- Cold-email SKILL.md: added "No-Dump Rule", Stage Calibration, banned CTA "quick call" → drove +0.33 outreach skill delta

Day two priorities: frontier eval run (MODEL_PROVIDER=anthropic) to measure cascade quality uplift, meeting and deck evals.
