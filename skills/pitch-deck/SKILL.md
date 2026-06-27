---
name: pitch-deck
description: >-
  Creates a 7-slide pitch deck tailored to a specific client meeting. Use whenever
  the task involves creating a pitch, presentation, deck, slides, or a meeting
  document for a specific client or prospect.
license: MIT
---

# Pitch Deck

Generates a structured 7-slide pitch deck personalized to the client using their
company profile, meeting history, and known pain points. Every slide has a single
job. The deck leads with the client's problem, not your product.

## Defaults (do not present options)

- Always 7 slides: Title, Problem, Cost of Inaction, Solution, How It Works, Pricing, CTA.
- Default format: Markdown (convertible to PPTX via export_to_pptx tool).
- Deck is personalized with at least one client-specific detail per slide.
- CTA is a single, specific ask with a date (e.g. "Sign by July 15 to start August 1").

## Workflow

1. Call `load_client_context(company_name)` to pull profile and history.
2. Call `get_slide_structure()` to get the 7-slide template.
3. Generate content for each slide using client-specific details from the context.
4. Call `save_deck(company_name, slides_json)` to persist the deck.
5. Optionally call `export_to_pptx(company_name)` if .pptx is requested.

## Gotchas

- Slide 2 (Problem) must use the client's language, not yours — pull from meeting notes.
- Slide 3 (Cost of Inaction) needs a number — estimate if unknown, but label it as estimated.
- Never put more than 30 words on a slide — this is a talking guide, not a document.
- Slide 7 CTA must have exactly ONE ask. Two asks = zero asks.

## Output template

Produce EXACTLY these sections, in this order:

**Pitch Deck — [Company] · [Date]**

---
**Slide 1 — Title / Hook**
[Headline: one sentence about their world]
*Subhead: [your company + what you do for them]*

**Slide 2 — Their Problem**
[The pain, in their words. 2–3 bullet points max.]

**Slide 3 — Cost of Inaction**
[Quantified: "Companies like [X] lose [$Y] per [period] without solving this."]

**Slide 4 — Our Solution**
[One sentence. Then 3 proof points.]

**Slide 5 — How It Works**
1. [Step 1]
2. [Step 2]
3. [Step 3 → outcome]

**Slide 6 — Pricing / Offer**
[Clear tier or price. Remove friction: "Start for $X/mo, cancel anytime."]

**Slide 7 — CTA**
[The one ask. The date. The next step.]

---
*Saved to data/decks/. Run `export_to_pptx` for .pptx version.*
