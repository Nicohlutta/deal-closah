"""Orchestrator — hub agent. OWNER: Nicholas.

Parses the user's intent and delegates to the right specialist.
Never duplicates specialist logic — just routes and assembles.

Routing map:
  "find / search / icp / companies / prospects" → icp_scout.run()
  "email / outreach / message / follow up"      → outreach.run()
  "meeting / notes / brief / crm / schedule"   → meeting_intel.run()
  "deck / pitch / slides / presentation"        → deck_builder.run()
  "event / conference / attend"                 → icp_scout.run_events()
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from agentkit import AgentResult, load_skill, run_agent, tool
from agents import deck_builder, icp_scout, meeting_intel, outreach

SKILLS_DIR = HERE / "skills"

# ── routing keywords ──────────────────────────────────────────────────────────

_ICP_KEYWORDS    = {"find", "search", "icp", "companies", "prospect", "target",
                    "crunchbase", "g2", "filter", "industry", "location"}
_OUTREACH_KEYS   = {"email", "outreach", "message", "follow", "reach", "write",
                    "draft", "send", "contact"}
_MEETING_KEYS    = {"meeting", "notes", "brief", "crm", "schedule", "calendar",
                    "log", "record", "client"}
_DECK_KEYS       = {"deck", "pitch", "slides", "presentation", "ppt", "create deck"}
_EVENT_KEYS      = {"event", "conference", "attend", "linkedin event", "scrape"}


def _route(task: str) -> str:
    t = task.lower()
    scores = {
        "icp":     sum(1 for k in _ICP_KEYWORDS  if k in t),
        "outreach":sum(1 for k in _OUTREACH_KEYS if k in t),
        "meeting": sum(1 for k in _MEETING_KEYS  if k in t),
        "deck":    sum(1 for k in _DECK_KEYS      if k in t),
        "event":   sum(1 for k in _EVENT_KEYS     if k in t),
    }
    return max(scores, key=scores.get)


# ── routing table (printed after every run) ───────────────────────────────────

def print_routing_table(table: list[dict]):
    header = f"{'agent':<20} {'model':<20} {'route':<30} {'tok (p+c)':>15} {'$':>10} {'s':>6}"
    print(f"\n{header}", file=sys.stderr)
    print("-" * len(header), file=sys.stderr)
    for row in table:
        tok = f"{row.get('prompt_tokens',0)}+{row.get('completion_tokens',0)}"
        print(
            f"{row['agent']:<20} {row['model']:<20} {row['route']:<30}"
            f" {tok:>15} {row.get('cost_usd', 0.0):>10.4f} {row.get('latency_s', 0.0):>6.1f}",
            file=sys.stderr,
        )


# ── main entry points ─────────────────────────────────────────────────────────

def run(task: str, skill=None) -> AgentResult:
    """Route task to the right specialist and return its result."""
    t0 = time.perf_counter()
    route = _route(task)
    routing_table = []

    if route == "icp":
        result = icp_scout.run(task, skill=skill or SKILLS_DIR / "icp-profile")
        routing_table.append({
            "agent": "icp-scout", "model": "granite4:micro",
            "route": "local/cheap", **result.usage,
            "cost_usd": result.cost_usd, "latency_s": result.latency_s,
        })

    elif route == "event":
        result = icp_scout.run_events(task, skill=skill or SKILLS_DIR / "event-scout")
        routing_table.append({
            "agent": "event-scout", "model": "granite4:micro",
            "route": "local/cheap", **result.usage,
            "cost_usd": result.cost_usd, "latency_s": result.latency_s,
        })

    elif route == "outreach":
        result = outreach.run(task, skill=skill or SKILLS_DIR / "cold-email")
        routing_table.append({
            "agent": "outreach", "model": "granite4:micro",
            "route": "local/cheap", **result.usage,
            "cost_usd": result.cost_usd, "latency_s": result.latency_s,
        })

    elif route == "meeting":
        result = meeting_intel.run(task, skill=skill or SKILLS_DIR / "meeting-brief")
        routing_table.append({
            "agent": "meeting-intel", "model": "granite4:micro",
            "route": "local/cheap", **result.usage,
            "cost_usd": result.cost_usd, "latency_s": result.latency_s,
        })

    elif route == "deck":
        # Deck building is judgment-heavy — route to strong tier if available
        result = deck_builder.run(task, skill=skill or SKILLS_DIR / "pitch-deck")
        routing_table.append({
            "agent": "deck-builder", "model": "granite4:micro",
            "route": "strong→local fallback", **result.usage,
            "cost_usd": result.cost_usd, "latency_s": result.latency_s,
        })

    else:
        # Fallback: run as a generic agent
        result = run_agent(task, skill=skill)
        routing_table.append({
            "agent": "orchestrator", "model": "granite4:micro",
            "route": "local/default", **result.usage,
            "cost_usd": result.cost_usd, "latency_s": result.latency_s,
        })

    # Attach routing table to result (AgentResult is a NamedTuple so we wrap it)
    result = result._replace() if hasattr(result, "_replace") else result
    result.__dict__["routing_table"] = routing_table  # type: ignore[attr-defined]
    return result
