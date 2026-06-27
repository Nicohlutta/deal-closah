# Model Selection — deal-closah

## Routing strategy: hybrid (upfront routing + cascade where it matters)

deal-closah uses **two routing strategies** combined:

- **Upfront routing** for agents where task difficulty is predictable from the intent
  label — ICP search and classification are always structured extraction; local is fine.
- **Cascade** for the outreach agent, where quality is the sensitive dimension:
  granite4:micro answers first, self-grades its confidence, and escalates to the
  strong tier only when confidence falls below the threshold. This delivers $0 cost
  for simple follow-up bumps and frontier quality for complex initial cold emails.

## Who does what

| Agent / Step | Strategy | Local model | Frontier (if key set) | Why |
|---|---|---|---|---|
| `orchestrator.classify_intent` | upfront → cheap | granite4:micro | claude-haiku-4-5 | JSON classification, 6 intents — templated; haiku is overkill |
| `icp_scout` (search + format) | upfront → cheap | granite4:micro | claude-haiku-4-5 | SerpAPI results → company table: structured extraction, not judgment |
| `outreach` (cold email) | **cascade** | granite4:micro first | claude-opus-4-8 if confidence < 0.93 | Cold email tone is quality-sensitive; cascade uses local for simple bumps, escalates for complex initial drafts |
| `meeting_intel` (Deepthi) | upfront → cheap | granite4:micro | claude-haiku-4-5 | Meeting note parsing — templated extraction, well-scoped |
| `deck_builder` (Arman) | upfront → strong | granite4:micro | claude-opus-4-8 | 7-slide narrative synthesis — local struggles with creative slide judgment |

## Cascade implementation (outreach agent)

```python
# agents/outreach.py
cheap = run_agent(task, ..., provider="local", tier="default")  # granite4:micro, $0
confidence, _ = self_grade(task, cheap.text, provider="local")  # local grades itself
if confidence < CASCADE_THRESHOLD:                                # default: 0.93
    strong = run_agent(task, ..., tier="strong")                 # claude-opus-4-8 when key set
```

**Threshold calibration:** granite4:micro self-grades 0.90–1.00 on most tasks
(documented in model-matchmakah benchmark). Setting threshold at 0.93 means:
- Simple follow-up bumps (granite grades 0.94+) → stay local, $0.00
- Complex initial cold emails requiring No-Dump Rule (granite grades 0.90–0.92) → escalate

Override with `CASCADE_THRESHOLD=0.99` env var to force nearly all outreach to frontier.

**Graceful degradation:** if the strong tier is unavailable (no API key, offline mode),
the local answer is returned with a stderr note — never a crash.

## Measured (local only, offline, warm model)

All agents run at $0.00 locally. The cost cells are meaningful only when
`MODEL_PROVIDER=anthropic|openai|gemini` is configured in .env.

| Agent | Turns | Latency | Cost |
|---|---|---|---|
| icp_scout (offline spine test) | 3 | ~55 s | $0.00 |
| outreach | TBD | TBD | $0.00 |

*Cold-start note: first run after `ollama serve` takes 3–5× longer (model load dominates).*

## Frontier economics (hypothetical — using agentkit published prices)

Prices from `agentkit/llm.py`: claude-haiku-4-5 $1/$5 per 1M tok, claude-opus-4-8 $5/$25 per 1M tok.

| Task | Model (frontier) | Est. cost per run |
|---|---|---|
| classify_intent (~200 prompt + 50 completion tok) | claude-haiku-4-5 | ~$0.0003 |
| icp_scout (~800 prompt + 400 completion tok) | claude-haiku-4-5 | ~$0.0028 |
| outreach (~1200 prompt + 600 completion tok) | claude-opus-4-8 | ~$0.021 |
| Full pipeline (icp + outreach) | mixed | ~$0.024 |

The outreach draft costs ~7× the search step by design — pay for quality where quality matters.

## What the skill buys (fill in after eval run)

```bash
uv run python -m agentkit.evals evals/icp
uv run python -m agentkit.evals evals/outreach
```

| Agent | With skill | Without skill | Delta |
|---|---|---|---|
| icp-scout | ?/3 | ?/3 | TBD |
| outreach | ?/3 | ?/3 | TBD |

## Rejected alternatives

| Option | Rejected because |
|---|---|
| LangGraph / LangChain | Framework overhead; agentkit's 450-line harness is readable and sufficient for sequential routing |
| Cascade for all agents | Over-engineered for tasks with predictable difficulty; adds a grading call that rarely triggers escalation |
| Apollo API (B2B lead search) | Paid-only at scale, complex OAuth; SerpAPI is simpler and sufficient for hackathon search volume |
| Crunchbase API | Free tier too restrictive; SerpAPI Google search covers the same companies with no schema lock-in |
