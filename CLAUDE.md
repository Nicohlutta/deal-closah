# deal-closah — Agent Context

## What This Is
A sales & GTM multi-agent system (Lane 3). Input: a sales task (find prospects, write outreach,
log meeting notes, build a pitch deck). Output: structured results from the right specialist agent,
assembled by the orchestrator into a final response.

## Win Conditions (TOA Agent Build Day — Lane 3)
1. **Lane Merit (20 pts)** — 4+ cooperating agents with clear delegation via the orchestrator.
2. **Skill Quality (15 pts)** — 5 agentskills.io-valid SKILL.md files with measured with/without-skill deltas.
3. **ADLC (20 pts)** — filled `docs/ADLC.md` with eval evidence (run evals, capture benchmark.json).
4. **Shippability (25 pts)** — runs from README in under 5 min, MIT license, public repo.

## Stack
- **agentkit** — agent loop, skill loading, model calls (vendored in `agentkit/`, ~450 lines)
- **Pydantic** — structured agent I/O (`schemas.py`)
- **Ollama / granite4:micro** — local model, zero cost, fully offline
- **FastAPI** — backend API for the frontend (`app/api.py`) — Jon Paul owns this
- **Python 3.11+, uv** — dependency management

## Model
Default: `granite4:micro` via Ollama (local, $0.00).
Override with `MODEL_PROVIDER=anthropic` + `ANTHROPIC_API_KEY` for frontier tier.
Model routing is configured per-agent in each `agents/*.py` via `tier=` parameter.

## Core Pipeline
```
user task
    │
    ▼ orchestrator.classify_intent()   → labels intent as JSON
    ▼ orchestrator.route()             → delegates to ONE specialist
    │       ├── icp_scout.run()        → writes icp_result
    │       ├── outreach.run()         → writes outreach_result
    │       ├── meeting_intel.run()    → writes meeting_result
    │       └── deck_builder.run()     → writes deck_result
    ▼ orchestrator.assemble()          → folds result into final_output
```

## Orchestrator Rules (Nicholas owns these — everyone must comply)

1. **Every specialist agent MUST expose `run(task, skill=None)`** — this is the only entry point the orchestrator calls. No other public functions except optional `run_events()` for icp_scout.

2. **Each agent writes ONLY its own state slot** — never touch another agent's slot:
   - `icp_scout` → writes `state["icp_result"]` only
   - `outreach` → writes `state["outreach_result"]` only
   - `meeting_intel` → writes `state["meeting_result"]` only
   - `deck_builder` → writes `state["deck_result"]` only

3. **Agents must fail soft** — catch all exceptions, return an error string, never crash. The orchestrator handles errors at the assembly step.

4. **Agents must NOT import from each other** — they may only import from `agentkit`, `interfaces`, and `schemas`. Cross-agent imports create circular dependencies.

5. **Context is read from `data/`** — agents find prior context (prospect profiles, meeting notes) by reading from `data/prospects/`, `data/meetings/`, etc. via `interfaces.py`. Never pass live objects between agents.

6. **Return type is always `AgentResult`** — use `agentkit.run_agent()` as the last step. The orchestrator expects `.text`, `.turns`, `.tool_calls`, `.cost_usd`, `.latency_s`.

7. **Every tool must have a docstring** — the `@tool` decorator turns docstrings into prompts. A tool with no docstring gives the model no guidance and will be misused.

## Schemas Contract (`schemas.py` — Nicholas owns, read-only for everyone else)

```python
SalesState TypedDict:
  task              str         # the user's input
  classification    dict        # set by orchestrator.classify_intent()
  routed_to         str         # set by orchestrator.route()
  icp_result        dict|None   # set by icp_scout ONLY
  outreach_result   dict|None   # set by outreach ONLY
  meeting_result    dict|None   # set by meeting_intel ONLY
  deck_result       dict|None   # set by deck_builder ONLY
  final_output      str|None    # set by orchestrator.assemble() ONLY
  latencies         dict        # each agent appends its own key
  errors            list[str]   # each agent appends on failure
  model_calls       int         # orchestrator tallies
```

If you need a new field, ask Nicholas to add it to `schemas.py`. Do not extend SalesState yourself.

## File Ownership (no one touches another lane's files)

| File / Directory | Owner | Branch |
|---|---|---|
| `agents/orchestrator.py` | Nicholas | `master` |
| `agents/icp_scout.py` | Nicholas | `master` |
| `agents/outreach.py` | Nicholas | `master` |
| `skills/icp-profile/` | Nicholas | `master` |
| `skills/event-scout/` | Nicholas | `master` |
| `skills/cold-email/` | Nicholas | `master` |
| `schemas.py`, `interfaces.py`, `agent.py` | Nicholas | `master` |
| `agents/meeting_intel.py` | Deepthi | `feat/deepthi-meeting-intel` |
| `skills/meeting-brief/` | Deepthi | `feat/deepthi-meeting-intel` |
| `agents/deck_builder.py` | Arman | `feat/arman-deck-builder` |
| `skills/pitch-deck/` | Arman | `feat/arman-deck-builder` |
| `app/` (frontend) | Jon Paul | `feat/frontend` |
| `docs/`, `README.md` | Nicholas (shared — PR to merge) | `master` |

## Skill Rules (agentskills.io spec)

Every `SKILL.md` must have:
- YAML frontmatter: `name` (must match directory name), `description`, `license: MIT`
- Sections: `## Defaults`, `## Workflow`, `## Gotchas`, `## Output template`
- Validate with: `uv run agentskills validate skills/<skill-name>/`

The `name:` in frontmatter MUST exactly match the directory name or `load_skill()` will raise.

## Evals (run before every PR merge)

```bash
uv run python -m agentkit.evals evals/icp        # Teammate: Nicholas
uv run python -m agentkit.evals evals/outreach   # Teammate: Nicholas
uv run python -m agentkit.evals evals/meeting    # Teammate: Deepthi
uv run python -m agentkit.evals evals/deck       # Teammate: Arman
```

Each eval run writes `evals/<name>/benchmark.json`. Commit this file with your PR.
The with-skill pass rate must be HIGHER than without-skill. If it isn't, fix the skill before merging.

## The Spine (keep green at all times)

```bash
python agent.py "Find SaaS companies in Boston" --offline
```

If this command errors, fix it before adding anything new. This is the integration test.
Every agent must handle `--offline` / `AGENT_OFFLINE=1` by using fixtures instead of live APIs.

## PR Rules

- Open PRs against `master` only — never against another teammate's branch.
- PR must include: what you built, eval results (with vs without skill pass rate), and one example output.
- Never commit `.env` — check `git status` before every push.
- `data/` files are gitignored — do not commit runtime outputs.

## Offline / Fixtures Rule

Every tool that calls an external API MUST have an offline fallback:
```python
if os.getenv("AGENT_OFFLINE") == "1":
    return json.loads((FIXTURES / "your_sample.json").read_text())
```
Add your fixture file to `fixtures/`. The demo must work with no internet connection.
