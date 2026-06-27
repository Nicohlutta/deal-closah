# Model Selection — deal-closah

## Routing strategy: upfront task-type routing

deal-closah uses **upfront routing** (not cascading): the orchestrator classifies
intent first, then each specialist picks its tier based on what the task requires
— cheap for structured extraction, strong for creative synthesis and complex
instruction-following.

This avoids the self-grading overhead of cascade while putting the right model
on the right job. Task difficulty is predictable at routing time (the intent
label tells you everything), so cascading would mostly pay for a self-grade call
that never triggers an escalation.

## Who does what

| Agent / Step | Tier | Local model | Frontier (if key set) | Why |
|---|---|---|---|---|
| `orchestrator.classify_intent` | cheap | granite4:micro | claude-haiku-4-5 | JSON classification into 6 intents — templated, well-scoped; haiku handles it |
| `icp_scout` (search + format) | cheap | granite4:micro | claude-haiku-4-5 | Formats SerpAPI results into a company table — structured extraction, not judgment |
| `outreach` (cold email drafting) | **strong** | granite4:micro | **claude-opus-4-8** | Email copy is tone-sensitive; No-Dump Rule and Stage Calibration require strong instruction-following; wrong model = bad emails |
| `meeting_intel` (Deepthi) | cheap | granite4:micro | claude-haiku-4-5 | Parsing meeting notes into structured CRM records — templated extraction |
| `deck_builder` (Arman) | strong | granite4:micro | claude-opus-4-8 | 7-slide narrative requires creative synthesis and slide-by-slide judgment |

## Why not cascade?

Cascade (cheap → self-grade → escalate on low confidence) is the right choice
when task difficulty is unknown at dispatch time. For deal-closah, the orchestrator
already knows the task type before any model call — `intent=outreach` means we need
strong tone quality, `intent=icp` means we need structured formatting. Upfront
routing is 1 call cheaper per query and avoids calibrating a confidence threshold.

Cascade would improve the `outreach` agent for follow-up bumps (simple bumps don't
need Opus). That's extension idea #1 for a second sprint.

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
