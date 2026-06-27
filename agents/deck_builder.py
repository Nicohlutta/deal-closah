"""Deck Builder — creates 7-slide pitch decks for client meetings. OWNER: Teammate 4.

Tools to implement:
  load_client_context(company_name)  — pull profile + history for personalization
  generate_deck(company_name, focus) — produce 7-slide structure
  save_deck_markdown(company_name, slides_json) — save to data/decks/
  export_to_pptx(company_name)       — convert markdown deck to .pptx (optional)

The 7-slide structure:
  1. Title / Hook
  2. Their Problem (make them feel it)
  3. The Cost of Inaction
  4. Our Solution
  5. How It Works (3 steps max)
  6. Pricing / Offer
  7. CTA (one ask, one next step)
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

import sys
sys.path.insert(0, str(HERE))

from agentkit import AgentResult, run_agent, tool
from interfaces import CompanyProfile, MeetingNote, OutreachRecord, PitchDeck

OFFLINE = os.getenv("AGENT_OFFLINE", "0") == "1"

SYSTEM = """You are a Pitch Deck specialist — a strategic storyteller who builds
compelling 7-slide decks for sales meetings. Every slide earns its place.
You lead with the client's problem (never your features), quantify the cost of
inaction, and end with one clear ask. Decks are concise, visual-friendly, and
tailored to the specific company you're pitching."""

SLIDE_STRUCTURE = [
    {"slide": 1, "title": "Title / Hook",         "prompt": "Attention-grabbing headline about their world, not yours."},
    {"slide": 2, "title": "Their Problem",         "prompt": "Name the pain clearly. Use their language. Make them feel it."},
    {"slide": 3, "title": "Cost of Inaction",      "prompt": "What does this problem cost them in time, money, or risk?"},
    {"slide": 4, "title": "Our Solution",          "prompt": "One clear sentence on what you do for them."},
    {"slide": 5, "title": "How It Works",          "prompt": "3 steps maximum. Concrete, simple, no jargon."},
    {"slide": 6, "title": "Pricing / Offer",       "prompt": "Clear offer. Remove friction. Optional: limited-time hook."},
    {"slide": 7, "title": "Call to Action",        "prompt": "One ask. One next step. One date."},
]


# ── tools ─────────────────────────────────────────────────────────────────────

@tool
def load_client_context(company_name: str) -> str:
    """Load everything known about a client to personalize the pitch deck.
    Returns profile, meeting history, and outreach history as structured JSON.
    Always call this first before generating a deck.
    """
    context: dict = {"company": company_name, "profile": None, "meetings": [], "outreach": []}

    try:
        p = CompanyProfile.load(company_name)
        context["profile"] = p.__dict__
    except Exception:
        pass

    context["meetings"] = [n.__dict__ for n in MeetingNote.load_for_client(company_name)]
    context["outreach"] = [r.__dict__ for r in OutreachRecord.load_for_company(company_name)]

    return json.dumps(context, indent=2)


@tool
def get_slide_structure() -> str:
    """Return the required 7-slide structure for the pitch deck.
    Each slide has a title, purpose, and what content belongs there.
    Use this to understand what to generate for each slide.
    """
    return json.dumps(SLIDE_STRUCTURE, indent=2)


@tool
def save_deck(company_name: str, slides_json: str) -> str:
    """Save the generated pitch deck to data/decks/.
    slides_json: JSON array of {slide, title, content} objects.
    Returns the file path.
    """
    try:
        slides = json.loads(slides_json)
    except Exception:
        return "ERROR: slides_json must be a valid JSON array"

    deck = PitchDeck(
        company_name=company_name,
        created_date=str(date.today()),
        slides=slides,
        format="markdown",
    )
    deck.save()

    # Also write a readable markdown version
    md_path = HERE / "data" / "decks" / f"{company_name.lower().replace(' ', '_')}_{date.today()}.md"
    md_lines = [f"# Pitch Deck — {company_name}\n*Generated {date.today()}*\n"]
    for s in slides:
        md_lines.append(f"\n## Slide {s.get('slide', '?')}: {s.get('title', '')}\n")
        md_lines.append(s.get("content", "") + "\n")
    md_path.write_text("\n".join(md_lines))

    return f"Deck saved: {md_path}"


@tool
def export_to_pptx(company_name: str) -> str:
    """Export the latest saved deck to a .pptx PowerPoint file.
    Requires python-pptx: pip install python-pptx
    Returns the .pptx file path.
    """
    # TODO Teammate 4: implement with python-pptx
    # pip install python-pptx
    # from pptx import Presentation
    # from pptx.util import Inches, Pt
    return (
        f"PPTX export not yet implemented. "
        f"Install python-pptx and implement in agents/deck_builder.py::export_to_pptx. "
        f"Markdown deck is available in data/decks/"
    )


# ── agent entry point ─────────────────────────────────────────────────────────

def run(task: str, skill=None) -> AgentResult:
    """Generate a pitch deck for the company/meeting described in the task."""
    return run_agent(
        task,
        tools=[load_client_context, get_slide_structure, save_deck, export_to_pptx],
        skill=skill,
        system=SYSTEM,
        tier="default",  # deck quality matters — use strong tier if available
    )
