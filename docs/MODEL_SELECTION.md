# Model Selection — deal-closah

| Task | Model | Tier | Why |
|------|-------|------|-----|
| ICP search & filtering | granite4:micro | local | Structured extraction; data stays on-device; $0 |
| Email drafting | granite4:micro → claude-sonnet-4-6 | local → strong | Tone-sensitive; escalate when quality matters |
| Meeting brief | granite4:micro | local | Template-driven; local 3B handles structured output |
| Pitch deck | granite4:micro → claude-opus-4-8 | local → strong | Creativity + judgment; strong tier preferred |
| Event search | granite4:micro | local | Tool-calling + aggregation; local sufficient |

**Routing:** Static per-task assignment. `deck_builder` uses `tier="default"` which routes to strong if `MODEL_PROVIDER=anthropic` is set, otherwise local.

**Measured** (fill in after eval run):

| Config | $ / run | latency / run | eval pass rate |
|--------|---------|--------------|---------------|
| local-only (granite4:micro) | $0.00 | ?s | ?/12 |
| frontier (claude-sonnet-4-6) | $? | ?s | ?/12 |

**Rejected:** LangChain/LangGraph — adds framework overhead; agentkit's 450-line harness is readable and sufficient for this scope.
