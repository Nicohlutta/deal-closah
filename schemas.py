"""Shared state schema for deal-closah agents.

Pattern from hack-125: each specialist writes to its OWN slot in SalesState.
The orchestrator reads from state, routes, and assembles the final output.
No concurrent write conflicts — each agent owns exactly one key.

Usage:
    state = initial_state("Find SaaS companies in Boston")
    state = orchestrator.run_with_state(state)
    print(state["final_output"])
"""

from __future__ import annotations

from typing import Literal, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field


# ── Intent classification ─────────────────────────────────────────────────────

Intent = Literal["icp", "outreach", "meeting", "deck", "event", "crm", "unknown"]


class Classification(BaseModel):
    intent: Intent
    company_name: Optional[str] = None   # extracted from task if present
    contact_name: Optional[str] = None
    confidence: Literal["low", "medium", "high"] = "medium"
    summary: str = ""


# ── Specialist output models ──────────────────────────────────────────────────

class ICPResult(BaseModel):
    companies: list[dict] = Field(default_factory=list)
    summary: str = ""
    error: Optional[str] = None


class OutreachResult(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    follow_up_schedule: list[str] = Field(default_factory=list)
    saved_path: Optional[str] = None
    error: Optional[str] = None


class MeetingResult(BaseModel):
    brief: Optional[str] = None
    action_items: list[str] = Field(default_factory=list)
    next_steps: Optional[str] = None
    calendar_event: Optional[dict] = None
    error: Optional[str] = None


class DeckResult(BaseModel):
    slides: list[dict] = Field(default_factory=list)
    markdown_path: Optional[str] = None
    pptx_path: Optional[str] = None
    error: Optional[str] = None


# ── Shared pipeline state ─────────────────────────────────────────────────────

class SalesState(TypedDict):
    """Shared state that flows through the deal-closah pipeline.

    Orchestrator populates `task` and `classification`.
    Each specialist writes to its OWN result slot — never another agent's.
    Orchestrator assembles `final_output` at the end.
    """
    # Input
    task: str

    # Orchestrator sets these
    classification: Optional[dict]      # Classification.model_dump()
    routed_to: Optional[str]            # which agent handled this

    # Specialist outputs — each agent writes ONLY its own slot
    icp_result: Optional[dict]          # ICPResult — written by icp_scout only
    outreach_result: Optional[dict]     # OutreachResult — written by outreach only
    meeting_result: Optional[dict]      # MeetingResult — written by meeting_intel only
    deck_result: Optional[dict]         # DeckResult — written by deck_builder only

    # Final assembly (orchestrator)
    final_output: Optional[str]

    # Observability
    latencies: dict                     # {"orchestrator": 0.3, "icp_scout": 4.1, ...}
    errors: list[str]
    model_calls: int


def initial_state(task: str) -> SalesState:
    """Create a fresh state for a new task."""
    return {
        "task": task,
        "classification": None,
        "routed_to": None,
        "icp_result": None,
        "outreach_result": None,
        "meeting_result": None,
        "deck_result": None,
        "final_output": None,
        "latencies": {},
        "errors": [],
        "model_calls": 0,
    }
