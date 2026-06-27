"""Deck Builder — creates 7-slide pitch decks for client meetings. OWNER: Arman.

The agent owns only the deck_result lane. It reads CRM context from data/,
generates a fixed 7-slide pitch structure, saves markdown/JSON, and can export
the latest saved deck to a dependency-free PPTX file.
"""

from __future__ import annotations

import io
import json
import os
import re
import sys
import time
import zipfile
from datetime import date, datetime, timezone
from html import escape
from pathlib import Path
from typing import NamedTuple

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

try:
    from agentkit import AgentResult, run_agent, tool
except ModuleNotFoundError:
    class AgentResult(NamedTuple):
        text: str
        turns: int
        tool_calls: list
        usage: dict
        cost_usd: float
        latency_s: float
        messages: list

    def tool(fn=None, *, description=None):
        def wrap(f):
            f._tool_schema = {"function": {"name": f.__name__, "description": description or (f.__doc__ or "")}}
            return f
        return wrap(fn) if fn else wrap

    def run_agent(*args, **kwargs):
        raise RuntimeError("agentkit dependencies are not installed; using deck_builder soft fallback")
from interfaces import CompanyProfile, MeetingNote, OutreachRecord, PitchDeck

DATA_DIR = HERE / "data"
DECK_DIR = DATA_DIR / "decks"

SYSTEM = """You are a Pitch Deck specialist — a strategic storyteller who builds
compelling 7-slide decks for sales meetings. Every slide earns its place.
You lead with the client's problem, quantify the cost of inaction, keep slide
copy short, and end with one clear ask. Use the deck tools to load context,
generate, save, edit, and export the deck."""

SLIDE_STRUCTURE = [
    {"slide": 1, "title": "Title / Hook", "prompt": "Attention-grabbing headline about their world, not yours."},
    {"slide": 2, "title": "Their Problem", "prompt": "Name the pain clearly. Use their language. Make them feel it."},
    {"slide": 3, "title": "Cost of Inaction", "prompt": "What does this problem cost them in time, money, or risk?"},
    {"slide": 4, "title": "Our Solution", "prompt": "One clear sentence on what you do for them."},
    {"slide": 5, "title": "How It Works", "prompt": "3 steps maximum. Concrete, simple, no jargon."},
    {"slide": 6, "title": "Pricing / Offer", "prompt": "Clear offer. Remove friction. Use placeholders if unknown."},
    {"slide": 7, "title": "CTA", "prompt": "One ask. One next step. One date."},
]


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "target_account"


def _ensure_data_dirs() -> None:
    for name in ("prospects", "meetings", "outreach", "decks"):
        (DATA_DIR / name).mkdir(parents=True, exist_ok=True)


def _extract_company_name(task: str) -> str:
    patterns = [
        r"(?:for|to)\s+([A-Z][A-Za-z0-9&.\- ]+?)(?:\s+(?:meeting|focused|focus|next|about)\b|$)",
        r"deck\s+([A-Z][A-Za-z0-9&.\- ]+?)(?:\s|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, task)
        if match:
            return match.group(1).strip(" .")
    return "Target Account"


def _split_notes(value: str) -> list[str]:
    if not value:
        return []
    parts = re.split(r"[\n;]+", value)
    return [p.strip(" -") for p in parts if p.strip(" -")]


def _load_context_dict(company_name: str) -> dict:
    _ensure_data_dirs()
    context: dict = {"company": company_name, "profile": None, "meetings": [], "outreach": []}

    try:
        context["profile"] = CompanyProfile.load(company_name).__dict__
    except Exception:
        context["profile"] = None

    try:
        context["meetings"] = [n.__dict__ for n in MeetingNote.load_for_client(company_name)]
    except Exception:
        context["meetings"] = []

    try:
        context["outreach"] = [r.__dict__ for r in OutreachRecord.load_for_company(company_name)]
    except Exception:
        context["outreach"] = []

    return context


def _context_signal(context: dict, focus: str) -> dict[str, str]:
    profile = context.get("profile") or {}
    meetings = context.get("meetings") or []
    outreach = context.get("outreach") or []
    latest_meeting = meetings[-1] if meetings else {}
    latest_outreach = outreach[-1] if outreach else {}

    raw_notes = latest_meeting.get("extracted_insights") or latest_meeting.get("raw_notes") or focus
    notes = _split_notes(raw_notes)
    pain = notes[0] if notes else (focus or "the team needs a faster way to turn sales context into momentum")
    next_step = latest_meeting.get("next_steps") or "Book a 30-minute pilot planning call next week"
    industry = profile.get("industry") or "their market"
    buyer = profile.get("decision_maker_title") or "the buying team"
    size = profile.get("size") or "their team"
    company = context.get("company", "Target Account")

    return {
        "company": company,
        "industry": industry,
        "buyer": buyer,
        "size": size,
        "pain": pain,
        "next_step": next_step,
        "outreach": latest_outreach.get("message", ""),
        "source": profile.get("source", "manual/offline"),
    }


def _build_slides(company_name: str, focus: str, context: dict | None = None) -> list[dict]:
    context = context or _load_context_dict(company_name)
    signal = _context_signal(context, focus)
    company = signal["company"]
    pain = signal["pain"]
    buyer = signal["buyer"]
    industry = signal["industry"]
    next_step = signal["next_step"]

    return [
        {
            "slide": 1,
            "title": "Title / Hook",
            "content": f"{company} can turn every sales conversation into a sharper next step.\n\nFor {buyer} teams in {industry}.",
            "speaker_notes": f"Open by anchoring the pitch in {company}'s workflow, then confirm whether this is the right priority.",
            "needs_input": [],
        },
        {
            "slide": 2,
            "title": "Their Problem",
            "content": f"- {pain}\n- Meeting context gets scattered across notes and follow-ups.\n- Decks take too long to personalize before buyer interest fades.",
            "speaker_notes": "Ask the buyer which pain is most expensive today. Use their answer to steer the rest of the deck.",
            "needs_input": [],
        },
        {
            "slide": 3,
            "title": "Cost of Inaction",
            "content": "- Slower follow-up means fewer warm conversations turn into meetings.\n- Sellers rebuild context instead of moving deals forward.\n- Leadership gets less visibility into what will close.",
            "speaker_notes": "Position this as the practical cost of delay. Do not invent ROI numbers unless the user provides them.",
            "needs_input": ["validated impact metric"],
        },
        {
            "slide": 4,
            "title": "Our Solution",
            "content": "- Capture prospect, outreach, and meeting context in one flow.\n- Generate pre-meeting briefs and 7-slide pitch decks.\n- Keep follow-up emails aligned with the same buyer narrative.",
            "speaker_notes": "Explain the product as a workflow outcome, not a feature list.",
            "needs_input": [],
        },
        {
            "slide": 5,
            "title": "How It Works",
            "content": "1. Select the account and meeting context.\n2. Generate a brief, pitch deck, and follow-up plan.\n3. Edit with chat and export the final PPTX.",
            "speaker_notes": "Make implementation feel simple and demo-friendly.",
            "needs_input": [],
        },
        {
            "slide": 6,
            "title": "Pricing / Offer",
            "content": "- Start with a 14-day pilot for one account team.\n- Measure prep time saved and follow-up quality.\n- needs_input: add pricing or package details.",
            "speaker_notes": "If pricing is unknown, sell the pilot as a low-risk way to prove value.",
            "needs_input": ["pricing/package"],
        },
        {
            "slide": 7,
            "title": "CTA",
            "content": f"{next_step}.\n\nOwner: seller + {buyer}. Outcome: confirm pilot fit and success criteria.",
            "speaker_notes": "End with one ask and one calendar-worthy next step.",
            "needs_input": [],
        },
    ]


def _deck_markdown(company_name: str, slides: list[dict]) -> str:
    lines = [f"# Pitch Deck — {company_name}", f"*Generated {date.today()}*", ""]
    for slide in slides:
        lines.append(f"## Slide {slide.get('slide', '?')}: {slide.get('title', '')}")
        lines.append(slide.get("content", ""))
        if slide.get("speaker_notes"):
            lines.append(f"\nSpeaker notes: {slide['speaker_notes']}")
        if slide.get("needs_input"):
            lines.append(f"\nNeeds input: {', '.join(slide['needs_input'])}")
        lines.append("")
    lines.append("*Saved to data/decks/. Run export_to_pptx for .pptx version.*")
    return "\n".join(lines)


def _paragraph_xml(text: str, size: int = 1800, bold: bool = False, color: str = "1E293B") -> str:
    b = "<a:b/>" if bold else ""
    return (
        f'<a:p><a:r><a:rPr lang="en-US" sz="{size}">{b}'
        f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill></a:rPr>'
        f"<a:t>{escape(text)}</a:t></a:r><a:endParaRPr lang=\"en-US\" sz=\"{size}\"/></a:p>"
    )


def _textbox_xml(
    idx: int,
    name: str,
    x: int,
    y: int,
    cx: int,
    cy: int,
    paragraphs: list[str],
    size: int,
    bold: bool = False,
    color: str = "1E293B",
    fill: str | None = None,
    line: str | None = None,
    radius: bool = False,
) -> str:
    body = "".join(_paragraph_xml(p, size=size, bold=bold, color=color) for p in paragraphs)
    geom = "roundRect" if radius else "rect"
    fill_xml = f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>' if fill else "<a:noFill/>"
    line_xml = f'<a:ln w="9000"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>' if line else "<a:ln><a:noFill/></a:ln>"
    return f"""
      <p:sp>
        <p:nvSpPr><p:cNvPr id="{idx}" name="{escape(name)}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
        <p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="{geom}"><a:avLst/></a:prstGeom>{fill_xml}{line_xml}</p:spPr>
        <p:txBody><a:bodyPr wrap="square" anchor="t" lIns="125000" tIns="90000" rIns="125000" bIns="90000"/><a:lstStyle/>{body}</p:txBody>
      </p:sp>
    """


def _rect_xml(idx: int, name: str, x: int, y: int, cx: int, cy: int, fill: str, line: str | None = None, radius: bool = False) -> str:
    geom = "roundRect" if radius else "rect"
    line_xml = f'<a:ln w="9000"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>' if line else "<a:ln><a:noFill/></a:ln>"
    return f"""
      <p:sp>
        <p:nvSpPr><p:cNvPr id="{idx}" name="{escape(name)}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
        <p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="{geom}"><a:avLst/></a:prstGeom><a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>{line_xml}</p:spPr>
      </p:sp>
    """


def _line_xml(idx: int, x: int, y: int, cx: int, color: str = "CBD5E1") -> str:
    return _rect_xml(idx, "Rule", x, y, cx, 18000, color)


def _clean_lines(content: str) -> list[str]:
    lines = []
    for raw in str(content or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"^[-*]\s*", "", line)
        line = re.sub(r"^\d+\.\s*", "", line)
        lines.append(line)
    return lines[:6]


def _kicker_xml(idx: int, label: str, color: str = "2563EB") -> str:
    return (
        _rect_xml(idx, "kicker-marker", 620000, 410000, 90000, 90000, color, radius=True)
        + _textbox_xml(idx + 1, "kicker-label", 735000, 360000, 2500000, 210000, [label.upper()], 780, True, "64748B")
    )


def _footer_xml(idx: int, company_name: str, slide_num: int, dark: bool = False) -> str:
    color = "CBD5E1" if dark else "64748B"
    return _textbox_xml(idx, "Footer", 7900000, 6320000, 3600000, 260000, [f"{company_name} / slide {slide_num}"], 820, False, color)


def _visual_xml(slide_num: int, lines: list[str]) -> str:
    if slide_num == 2:
        cards = []
        colors = ["FEE2E2", "FFEDD5", "FEF3C7"]
        for i, text in enumerate((lines + ["", "", ""])[:3]):
            y = 2140000 + i * 860000
            cards.append(_textbox_xml(20 + i, f"Problem {i + 1}", 7060000, y, 3840000, 600000, [text], 1180, True, "7F1D1D", colors[i], "FED7AA", True))
        return "".join(cards) + _textbox_xml(27, "Problem Caption", 7060000, 4860000, 3840000, 500000, ["Buyer friction concentrates here."], 980, False, "64748B")
    if slide_num == 3:
        labels = ["Pipeline drag", "Prep rework", "Visibility gap"]
        widths = [3000000, 2350000, 1800000]
        out = []
        for i, label in enumerate(labels):
            y = 2300000 + i * 760000
            out.append(_textbox_xml(30 + i * 3, f"Impact Label {i}", 7040000, y - 30000, 1700000, 310000, [label], 950, True, "334155"))
            out.append(_rect_xml(31 + i * 3, f"Impact Track {i}", 8800000, y, 2550000, 130000, "E2E8F0", radius=True))
            out.append(_rect_xml(32 + i * 3, f"Impact Bar {i}", 8800000, y, widths[i], 130000, ["2563EB", "14B8A6", "F97316"][i], radius=True))
        return "".join(out) + _textbox_xml(42, "Impact Note", 7040000, 4720000, 4000000, 520000, ["Qualitative impact until validated metrics are provided."], 980, False, "64748B")
    if slide_num == 4:
        nodes = ["Context", "Brief", "Deck", "Follow-up"]
        out = []
        for i, node in enumerate(nodes):
            x = 6550000 + i * 1320000
            out.append(_rect_xml(50 + i * 2, f"Solution Node {i}", x, 2800000, 920000, 920000, ["DBEAFE", "CCFBF1", "FFEDD5", "DCFCE7"][i], ["93C5FD", "5EEAD4", "FDBA74", "86EFAC"][i], True))
            out.append(_textbox_xml(51 + i * 2, f"Solution Label {i}", x + 60000, 3100000, 800000, 300000, [node], 880, True, "0F172A"))
            if i < len(nodes) - 1:
                out.append(_line_xml(70 + i, x + 950000, 3250000, 350000, "94A3B8"))
        return "".join(out) + _textbox_xml(80, "Workflow Outcome", 6640000, 4300000, 3920000, 560000, ["One narrative travels from research to meeting to recap."], 1040, False, "475569")
    if slide_num == 5:
        out = [_line_xml(90, 6900000, 3380000, 3950000, "CBD5E1")]
        for i, text in enumerate((lines + ["", "", ""])[:3]):
            x = 6750000 + i * 1650000
            out.append(_rect_xml(91 + i * 3, f"Step Dot {i}", x, 3180000, 420000, 420000, "2563EB", radius=True))
            out.append(_textbox_xml(92 + i * 3, f"Step Num {i}", x + 85000, 3270000, 250000, 180000, [str(i + 1)], 900, True, "FFFFFF"))
            out.append(_textbox_xml(93 + i * 3, f"Step Text {i}", x - 360000, 3760000, 1160000, 700000, [text], 850, False, "334155"))
        return "".join(out)
    if slide_num == 6:
        return (
            _textbox_xml(110, "Offer Card", 6900000, 2100000, 3800000, 2200000, lines[:3], 1180, True, "0F172A", "FFFFFF", "BFDBFE", True)
            + _rect_xml(111, "Offer Accent", 6900000, 2100000, 120000, 2200000, "2563EB")
            + _textbox_xml(112, "Risk Reducer", 7150000, 4650000, 3300000, 520000, ["Start small. Prove value. Expand after the pilot."], 980, False, "475569", "F8FAFC", "E2E8F0", True)
        )
    return ""


def _slide_xml(company_name: str, slide: dict) -> str:
    slide_num = int(slide.get("slide", 1) or 1)
    lines = _clean_lines(slide.get("content", ""))
    notes = slide.get("speaker_notes", "")
    title = slide.get("title", "")
    accent = {
        1: "38BDF8",
        2: "F97316",
        3: "EF4444",
        4: "14B8A6",
        5: "2563EB",
        6: "A855F7",
        7: "22C55E",
    }.get(slide_num, "2563EB")

    if slide_num in (1, 7):
        body_lines = lines[:3] if slide_num == 1 else [lines[0] if lines else "Confirm the next step.", "Owner, timing, and success criteria are explicit."]
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:bg><p:bgPr><a:solidFill><a:srgbClr val="0B1220"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      {_rect_xml(2, "Hero Accent", 0, 0, 12192000, 360000, accent)}
      {_rect_xml(3, "Hero Block", 7600000, 1200000, 3500000, 4300000, "111C31", "1F2A44", True)}
      {_textbox_xml(4, "Kicker", 680000, 700000, 2600000, 240000, ["MEETING PITCH"], 850, True, accent)}
      {_textbox_xml(5, "Hero Title", 680000, 1340000, 6400000, 1700000, [company_name if slide_num == 1 else "Recommended next step"], 4200, True, "FFFFFF")}
      {_textbox_xml(6, "Hero Body", 720000, 3240000, 6100000, 1300000, body_lines, 1550, False, "D8E1EA")}
      {_textbox_xml(7, "Hero Metric 1", 7900000, 1700000, 2700000, 540000, ["7 slides"], 1900, True, "FFFFFF", "1E293B", "334155", True)}
      {_textbox_xml(8, "Hero Metric 2", 7900000, 2550000, 2700000, 540000, ["1 buyer story"], 1900, True, "FFFFFF", "1E293B", "334155", True)}
      {_textbox_xml(9, "Hero Metric 3", 7900000, 3400000, 2700000, 540000, ["1 clear CTA"], 1900, True, "FFFFFF", "1E293B", "334155", True)}
      {_textbox_xml(10, "Speaker Notes", 760000, 5850000, 7200000, 350000, [f"Speaker note: {notes}"], 820, False, "94A3B8")}
      {_footer_xml(11, company_name, slide_num, True)}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>"""

    left_lines = lines[:4]
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:bg><p:bgPr><a:solidFill><a:srgbClr val="F7F9FC"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      {_rect_xml(2, "Top Rule", 0, 0, 12192000, 105000, accent)}
      {_kicker_xml(3, f"Slide {slide_num}", accent)}
      {_textbox_xml(5, "Title", 620000, 780000, 6100000, 760000, [title], 3100, True, "0F172A")}
      {_line_xml(6, 620000, 1670000, 5400000, "CBD5E1")}
      {_textbox_xml(7, "Main Points", 690000, 2100000, 5200000, 2350000, left_lines, 1350, False, "1E293B")}
      {_textbox_xml(8, "Speaker Notes", 690000, 5120000, 5600000, 620000, [f"Speaker note: {notes}"], 900, False, "64748B", "FFFFFF", "E2E8F0", True)}
      {_rect_xml(9, "Visual Plane", 6600000, 1440000, 4800000, 4050000, "FFFFFF", "E2E8F0", True)}
      {_visual_xml(slide_num, lines)}
      {_footer_xml(150, company_name, slide_num)}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>"""


def _write_pptx(company_name: str, slides: list[dict], out_path: Path) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rels = ['<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>']
    slide_ids = []
    overrides = [
        '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>',
        '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>',
        '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>',
        '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>',
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
    ]
    for i, _ in enumerate(slides, start=1):
        rid = i + 1
        rels.append(f'<Relationship Id="rId{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>')
        slide_ids.append(f'<p:sldId id="{255 + i}" r:id="rId{rid}"/>')
        overrides.append(f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>')

    content_types = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>{''.join(overrides)}</Types>"""
    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>"""
    presentation = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst><p:sldIdLst>{''.join(slide_ids)}</p:sldIdLst><p:sldSz cx="12192000" cy="6858000" type="wide"/><p:notesSz cx="6858000" cy="9144000"/><p:defaultTextStyle/></p:presentation>"""
    pres_rels = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{''.join(rels)}</Relationships>"""
    slide_master = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/><p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst><p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles></p:sldMaster>"""
    master_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/></Relationships>"""
    slide_layout = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1"><p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>"""
    slide_layout_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/></Relationships>"""
    theme = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="deal-closah"><a:themeElements><a:clrScheme name="deal-closah"><a:dk1><a:srgbClr val="0F172A"/></a:dk1><a:lt1><a:srgbClr val="F8FAFC"/></a:lt1><a:dk2><a:srgbClr val="1E293B"/></a:dk2><a:lt2><a:srgbClr val="E2E8F0"/></a:lt2><a:accent1><a:srgbClr val="2563EB"/></a:accent1><a:accent2><a:srgbClr val="14B8A6"/></a:accent2><a:accent3><a:srgbClr val="F97316"/></a:accent3><a:accent4><a:srgbClr val="A855F7"/></a:accent4><a:accent5><a:srgbClr val="64748B"/></a:accent5><a:accent6><a:srgbClr val="22C55E"/></a:accent6><a:hlink><a:srgbClr val="2563EB"/></a:hlink><a:folHlink><a:srgbClr val="7C3AED"/></a:folHlink></a:clrScheme><a:fontScheme name="Aptos"><a:majorFont><a:latin typeface="Aptos Display"/></a:majorFont><a:minorFont><a:latin typeface="Aptos"/></a:minorFont></a:fontScheme><a:fmtScheme name="deal-closah"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="6350"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme></a:themeElements></a:theme>"""
    core = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>{escape(company_name)} Pitch Deck</dc:title><dc:creator>deal-closah deck_builder</dc:creator><cp:lastModifiedBy>deal-closah deck_builder</cp:lastModifiedBy><dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified></cp:coreProperties>"""
    app_props = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>deal-closah</Application><PresentationFormat>On-screen Show (16:9)</PresentationFormat><Slides>7</Slides></Properties>"""

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("docProps/core.xml", core)
        z.writestr("docProps/app.xml", app_props)
        z.writestr("ppt/presentation.xml", presentation)
        z.writestr("ppt/_rels/presentation.xml.rels", pres_rels)
        z.writestr("ppt/slideMasters/slideMaster1.xml", slide_master)
        z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", master_rels)
        z.writestr("ppt/slideLayouts/slideLayout1.xml", slide_layout)
        z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", slide_layout_rels)
        z.writestr("ppt/theme/theme1.xml", theme)
        for i, slide in enumerate(slides[:7], start=1):
            z.writestr(f"ppt/slides/slide{i}.xml", _slide_xml(company_name, slide))
            z.writestr(
                f"ppt/slides/_rels/slide{i}.xml.rels",
                """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/></Relationships>""",
            )


@tool
def load_client_context(company_name: str) -> str:
    """Load everything known about a client to personalize the pitch deck.
    Returns profile, meeting history, and outreach history as structured JSON.
    Always call this first before generating a deck.
    """
    return json.dumps(_load_context_dict(company_name), indent=2)


@tool
def get_slide_structure() -> str:
    """Return the required 7-slide structure for the pitch deck.
    Use this before drafting so the final deck has exactly seven slides.
    """
    return json.dumps(SLIDE_STRUCTURE, indent=2)


@tool
def generate_deck(company_name: str, focus: str = "") -> str:
    """Generate a deterministic 7-slide deck JSON array for a company.
    Use this when the user asks to build a pitch deck or when offline mode needs
    a reliable demo output without depending on a live model response.
    """
    slides = _build_slides(company_name, focus)
    return json.dumps(slides, indent=2)


@tool
def apply_deck_edit(company_name: str, edit_request: str) -> str:
    """Apply a chat-style edit to the latest saved deck.
    Supports changing the CTA, changing a slide title, replacing phrases, and
    adding a bullet to a slide. Saves the updated markdown and JSON deck.
    """
    try:
        deck = PitchDeck.load_latest(company_name)
        if not deck:
            slides = _build_slides(company_name, edit_request)
        else:
            slides = deck.slides

        lower = edit_request.lower()
        slide_match = re.search(r"slide\s+([1-7])", lower)
        slide = slides[int(slide_match.group(1)) - 1] if slide_match else None

        title_match = re.search(r"title\s+(?:to|as)\s+['\"]?(.+?)['\"]?$", edit_request, flags=re.I)
        if slide and title_match:
            slide["title"] = title_match.group(1).strip()
        elif (cta := re.search(r"(?:change|set|make)\s+(?:the\s+)?cta\s+(?:to|as)\s+(.+)", edit_request, flags=re.I)):
            slides[6]["content"] = cta.group(1).strip(" .'\"")
        elif (replace := re.search(r"replace\s+['\"](.+?)['\"]\s+with\s+['\"](.+?)['\"]", edit_request, flags=re.I)):
            old, new = replace.groups()
            for item in slides:
                item["title"] = item.get("title", "").replace(old, new)
                item["content"] = item.get("content", "").replace(old, new)
                item["speaker_notes"] = item.get("speaker_notes", "").replace(old, new)
        elif slide and (bullet := re.search(r"add\s+(?:a\s+)?bullet\s+(?:to\s+)?(?:slide\s+[1-7]\s*)?[:\-]?\s*(.+)", edit_request, flags=re.I)):
            slide["content"] = f"{slide.get('content', '').rstrip()}\n- {bullet.group(1).strip()}"
        elif "shorter" in lower or "more concise" in lower:
            for item in slides:
                lines = [line for line in item.get("content", "").splitlines() if line.strip()]
                item["content"] = "\n".join(lines[:3])
        else:
            slides[0]["speaker_notes"] = f"{slides[0].get('speaker_notes', '')} Seller edit request: {edit_request}"

        return save_deck(company_name, json.dumps(slides))
    except Exception as e:
        return f"ERROR: apply_deck_edit failed: {e}"


@tool
def save_deck(company_name: str, slides_json: str) -> str:
    """Save the generated pitch deck to data/decks/.
    slides_json must be a JSON array of seven slide objects.
    Returns the saved JSON and markdown file paths.
    """
    _ensure_data_dirs()
    try:
        slides = json.loads(slides_json)
    except Exception:
        return "ERROR: slides_json must be a valid JSON array"
    if not isinstance(slides, list) or len(slides) != 7:
        return "ERROR: slides_json must contain exactly 7 slides"

    deck = PitchDeck(company_name=company_name, created_date=str(date.today()), slides=slides, format="markdown")
    deck.save()

    md_path = DECK_DIR / f"{_slug(company_name)}_{date.today()}.md"
    md_path.write_text(_deck_markdown(company_name, slides), encoding="utf-8")
    json_path = DECK_DIR / f"{_slug(company_name)}_{date.today()}.json"
    return f"Deck saved: {json_path}\nMarkdown saved: {md_path}"


@tool
def export_to_pptx(company_name: str) -> str:
    """Export the latest saved deck to a .pptx PowerPoint file.
    Uses a dependency-free Office XML writer so offline demos work without
    python-pptx. Returns the .pptx file path.
    """
    _ensure_data_dirs()
    deck = PitchDeck.load_latest(company_name)
    if not deck:
        slides = _build_slides(company_name, "")
        save_deck(company_name, json.dumps(slides))
        deck = PitchDeck.load_latest(company_name)
    if not deck:
        return "ERROR: no deck available to export"

    out_path = DECK_DIR / f"{_slug(company_name)}_{date.today()}.pptx"
    _write_pptx(company_name, deck.slides, out_path)
    return f"PPTX exported: {out_path}"


def _fallback_result(task: str, error: str | None = None) -> AgentResult:
    t0 = time.perf_counter()
    company_name = _extract_company_name(task)
    slides = _build_slides(company_name, task)
    save_msg = save_deck(company_name, json.dumps(slides))
    pptx_msg = export_to_pptx(company_name)
    text = _deck_markdown(company_name, slides) + f"\n\n{save_msg}\n{pptx_msg}"
    if error:
        text += f"\n\nSoft fallback used because the model loop failed: {error}"
    return AgentResult(
        text=text,
        turns=0,
        tool_calls=[("generate_deck", {"company_name": company_name}, "offline deterministic deck")],
        usage={"prompt_tokens": 0, "completion_tokens": 0},
        cost_usd=0.0,
        latency_s=round(time.perf_counter() - t0, 2),
        messages=[],
    )


def run(task: str, skill=None) -> AgentResult:
    """Generate a pitch deck for the company/meeting described in the task."""
    if os.getenv("AGENT_OFFLINE") == "1":
        return _fallback_result(task)
    try:
        result = run_agent(
            task,
            tools=[load_client_context, get_slide_structure, generate_deck, apply_deck_edit, save_deck, export_to_pptx],
            skill=skill,
            system=SYSTEM,
            tier="default",
        )
        if "Slide 7" not in result.text and "CTA" not in result.text:
            return _fallback_result(task)
        return result
    except Exception as e:
        return _fallback_result(task, str(e))
