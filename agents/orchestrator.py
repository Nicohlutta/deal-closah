"""Orchestrator — hub agent. OWNER: Nicholas.

Pattern from hack-125/legal-letter-triage:
  1. classify_intent()  — understand what the user wants
  2. route()            — delegate to the right specialist
  3. assemble()         — fold the specialist's result into final_output

Each specialist writes to its OWN slot in SalesState (icp_result, outreach_result,
meeting_result, deck_result) — never another agent's slot. Zero write conflicts.

The orchestrator is the ONLY agent allowed to write: classification, routed_to, final_output.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import re

from agentkit import chat_raw, resolve
from schemas import Classification, Intent, SalesState, initial_state
from agents import deck_builder, icp_scout, meeting_intel, outreach

SKILLS_DIR = HERE / "skills"

# ── Step 1: classify intent ───────────────────────────────────────────────────

_CLASSIFY_SYSTEM = """You are a sales assistant router. Given a task, classify the intent.

Intent values:
- icp       : find companies, search prospects, filter by industry/location/size
- outreach  : write email, draft message, follow up, event outreach
- meeting   : log notes, pre-meeting brief, CRM, schedule, client history
- deck      : pitch deck, slides, presentation, ppt
- event     : find events, conference, scrape events page
- crm       : pipeline summary, all prospects, overview

Respond ONLY with valid JSON matching:
{"intent": "<value>", "company_name": "<name or null>", "contact_name": "<name or null>", "confidence": "low|medium|high", "summary": "<one line>"}
"""


def classify_intent(state: SalesState) -> SalesState:
    """Classify the user's intent from the task. Writes to state['classification']."""
    t0 = time.perf_counter()
    try:
        messages = [
            {"role": "system", "content": _CLASSIFY_SYSTEM},
            {"role": "user", "content": state["task"]},
        ]
        _, result = chat_raw(messages, handle=resolve(), json_mode=True)
        # Strip markdown code fences (Claude wraps JSON in ```json ... ``` without json_mode)
        raw = re.sub(r"```(?:json)?\s*|\s*```", "", result.text).strip()
        c = Classification.model_validate_json(raw)
        state["classification"] = c.model_dump()
    except Exception as e:
        state["errors"].append(f"classify_intent: {e}")
        state["classification"] = {
            "intent": "unknown",
            "company_name": None,
            "contact_name": None,
            "confidence": "low",
            "summary": "Classification failed — defaulting to ICP search.",
        }
    state["latencies"]["orchestrator_classify"] = round(time.perf_counter() - t0, 2)
    state["model_calls"] += 1
    return state


# ── Step 2: route to specialist ───────────────────────────────────────────────

def route(state: SalesState) -> SalesState:
    """Delegate to the right specialist. Each specialist writes ONLY its own slot."""
    intent: Intent = (state["classification"] or {}).get("intent", "unknown")
    state["routed_to"] = intent
    t0 = time.perf_counter()

    try:
        if intent == "icp":
            result = icp_scout.run(state["task"], skill=SKILLS_DIR / "icp-profile")
            state["icp_result"] = {"text": result.text, "tool_calls": len(result.tool_calls)}
            state["model_calls"] += result.turns

        elif intent == "event":
            result = icp_scout.run_events(state["task"], skill=SKILLS_DIR / "event-scout")
            state["icp_result"] = {"text": result.text, "tool_calls": len(result.tool_calls)}
            state["model_calls"] += result.turns

        elif intent == "outreach":
            result = outreach.run(state["task"], skill=SKILLS_DIR / "cold-email")
            state["outreach_result"] = {"text": result.text, "tool_calls": len(result.tool_calls)}
            state["model_calls"] += result.turns

        elif intent in ("meeting", "crm"):
            result = meeting_intel.run(state["task"], skill=SKILLS_DIR / "meeting-brief")
            state["meeting_result"] = {"text": result.text, "tool_calls": len(result.tool_calls)}
            state["model_calls"] += result.turns

        elif intent == "deck":
            result = deck_builder.run(state["task"], skill=SKILLS_DIR / "pitch-deck")
            state["deck_result"] = {"text": result.text, "tool_calls": len(result.tool_calls)}
            state["model_calls"] += result.turns

        else:
            state["errors"].append(f"Unknown intent '{intent}' — no agent routed.")
            result = None

        if result:
            state["latencies"][intent] = round(time.perf_counter() - t0, 2)

    except Exception as e:
        state["errors"].append(f"route({intent}): {e}")

    return state


# ── Step 3: assemble final output ─────────────────────────────────────────────

def assemble(state: SalesState) -> SalesState:
    """Fold specialist results into final_output. Orchestrator writes this slot."""
    intent = state.get("routed_to", "unknown")

    slot_map = {
        "icp":     state.get("icp_result"),
        "event":   state.get("icp_result"),
        "outreach":state.get("outreach_result"),
        "meeting": state.get("meeting_result"),
        "crm":     state.get("meeting_result"),
        "deck":    state.get("deck_result"),
    }
    result = slot_map.get(intent)

    if result and result.get("text"):
        state["final_output"] = result["text"]
    elif state["errors"]:
        state["final_output"] = (
            "One or more agents encountered errors:\n"
            + "\n".join(f"- {e}" for e in state["errors"])
        )
    else:
        state["final_output"] = "No output produced. Try rephrasing your task."

    return state


# ── Pipeline entry point ──────────────────────────────────────────────────────

def run_pipeline(task: str) -> SalesState:
    """Full pipeline: classify → route → assemble. Returns the final SalesState."""
    state = initial_state(task)
    state = classify_intent(state)
    state = route(state)
    state = assemble(state)
    return state


# ── Routing table printer (for CLI output) ───────────────────────────────────

def print_routing_table(state: SalesState):
    rows = [
        ("step", "latency (s)", "model calls"),
        *[(k, f"{v:.2f}", "") for k, v in state["latencies"].items()],
        ("TOTAL model calls", "", str(state["model_calls"])),
    ]
    col_w = [max(len(r[i]) for r in rows) for i in range(3)]
    print(file=sys.stderr)
    for row in rows:
        print("  ".join(r.ljust(col_w[i]) for i, r in enumerate(row)), file=sys.stderr)
    if state["errors"]:
        print(f"\nErrors: {state['errors']}", file=sys.stderr)


# ── Legacy run() kept for agentkit.evals compatibility ───────────────────────

def run(task: str, skill=None):
    """Thin wrapper so agentkit.evals can call run(task, skill) on the orchestrator."""
    from agentkit import AgentResult
    state = run_pipeline(task)
    # Wrap in AgentResult shape so evals engine works unchanged
    return AgentResult(
        text=state["final_output"] or "",
        turns=state["model_calls"],
        tool_calls=[],
        usage={"prompt_tokens": 0, "completion_tokens": 0},
        cost_usd=0.0,
        latency_s=sum(state["latencies"].values()),
        messages=[],
    )
