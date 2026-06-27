---
name: pitch-deck
description: >-
  Creates and edits a 7-slide client-specific pitch deck for sales meetings,
  presentations, PPT exports, and chat-requested deck revisions. Use when the
  task mentions a pitch deck, slides, presentation, PPTX, client meeting deck,
  pricing/offer slide, CTA slide, or changing an existing deck.
license: MIT
---

# Pitch Deck

Generates a structured 7-slide pitch deck personalized to the client using the
company profile, meeting history, outreach history, and the user's requested
focus. The deck leads with the buyer's problem, not product features, and can be
saved as markdown/JSON or exported to PPTX.

## Defaults

- Always produce exactly 7 slides: Title / Hook, Their Problem, Cost of Inaction, Our Solution, How It Works, Pricing / Offer, CTA.
- Keep slide text short: 2-4 bullets or short lines per slide.
- Include speaker notes for each slide when saving structured JSON.
- Personalize with context from `load_client_context(company_name)` whenever available.
- Use `needs_input` for missing pricing, proof, ROI, implementation dates, or customer evidence instead of inventing facts.
- Default CTA: one concrete next step with an owner and timeline.
- Default export path: save markdown/JSON first, then call `export_to_pptx(company_name)` when the user asks for a PPT, presentation file, or demo-ready artifact.
- Default design system: dark cover and CTA slides, light editorial middle slides, one accent color per slide role, visible proof object on every middle slide, and speaker notes kept secondary.

## Workflow

1. Identify the company name and pitch focus from the task.
2. Call `load_client_context(company_name)` first.
3. Call `get_slide_structure()` to confirm the fixed seven-slide plan.
4. Call `generate_deck(company_name, focus)` for the initial structured slide JSON.
5. Call `save_deck(company_name, slides_json)` to persist the deck to `data/decks/`.
6. Call `export_to_pptx(company_name)` if the user asks for PPTX, a presentation file, export, or a webpage/demo download.
7. For chat edits, call `apply_deck_edit(company_name, edit_request)`, then export again if the user wants the PPT updated.

Design pass:

- Slide 1 should feel like a polished client-specific opener, not a title page.
- Slides 2-6 must vary layout rhythm: problem stack, impact bars, workflow map, timeline, and offer card.
- Slide 7 should be a decisive close with the CTA visually dominant.
- Do not use repeated generic bullet-only slides.
- Do not add fake logos, customer marks, or screenshots to make the deck feel designed.
- Keep every design choice tied to hierarchy, proof, or meeting flow.

## Gotchas

- Never touch another agent's data slot. The deck builder owns only deck output.
- Never import from another specialist agent.
- Do not invent proof points, pricing, ROI, customer logos, or testimonials.
- Label estimated impact as an estimate or put it in `needs_input`.
- Slide 2 must use the buyer's language from notes when available.
- Slide 3 can describe qualitative cost of inaction if no validated metric exists.
- Slide 7 must contain exactly one primary ask.
- If the model or external service is unavailable, use deterministic/offline deck generation and still save a usable deck.
- If a chat edit changes copy, keep the designed PPT layout intact on the next export.

## Output template

Produce this shape in the final answer:

**Pitch Deck — [Company] · [Date]**

**Slide 1 — Title / Hook**  
[Account-specific headline and short subhead]

**Slide 2 — Their Problem**  
[2-3 crisp bullets using meeting/context language]

**Slide 3 — Cost of Inaction**  
[Operational, revenue, risk, or time cost. Mark estimates.]

**Slide 4 — Our Solution**  
[One-sentence solution and 2-3 supporting points]

**Slide 5 — How It Works**  
1. [Step 1]  
2. [Step 2]  
3. [Step 3 -> outcome]

**Slide 6 — Pricing / Offer**  
[Clear offer, pilot, or `needs_input: pricing/package`]

**Slide 7 — CTA**  
[One ask, owner, and next step]

Then include:

- `Markdown saved: [path]`
- `PPTX exported: [path]` when exported
- `Needs input: [...]` when any factual field is missing
