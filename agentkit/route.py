"""agentkit.route — cascade routing: try cheap first, escalate when unsure.

The simplest routing pattern that earns Model Selection points: answer with
the cheap/local model, have it grade its own confidence, and only spend
frontier tokens when confidence is low. ``RouteResult.table_row`` is shaped
to paste straight into your MODEL_SELECTION.md evidence table.
"""

from __future__ import annotations

import json
import re
from typing import NamedTuple

from . import llm

_GRADER_SYSTEM = (
    "You are a strict grader. Reply with JSON only: "
    '{"confidence": <0.0-1.0 that the answer fully and correctly handles the task>}'
)


class RouteResult(NamedTuple):
    text: str
    escalated: bool
    confidence: float
    attempts: list  # ChatResults: [cheap_answer, grade, (strong_answer?)]
    total_cost_usd: float
    table_row: dict


def self_grade(task: str, answer: str, *, provider: str | None = None, tier: str = "cheap"):
    """Ask a (cheap) model how confident it is in an answer. Returns (score, ChatResult)."""
    r = llm.chat(
        f"Task:\n{task}\n\nAnswer:\n{answer}\n\nGrade the answer.",
        system=_GRADER_SYSTEM, provider=provider, tier=tier, json_mode=True,
    )
    try:
        score = float(json.loads(r.text)["confidence"])
    except Exception:  # model ignored json_mode — salvage the first number
        m = re.search(r"\d?\.\d+|[01]\b", r.text)
        score = float(m.group()) if m else 0.0
    return max(0.0, min(1.0, score)), r


def cascade(
    task: str,
    *,
    system: str = "",
    threshold: float = 0.7,
    cheap: tuple = ("local", "default"),
    strong: tuple = (None, "strong"),
) -> RouteResult:
    """Answer with `cheap`; below `threshold` self-confidence, retry with `strong`.

    cheap/strong are (provider, tier) pairs; provider None = $MODEL_PROVIDER.
    """
    first = llm.chat(task, system=system, provider=cheap[0], tier=cheap[1])
    confidence, grade = self_grade(task, first.text, provider=cheap[0])
    attempts = [first, grade]
    escalated, note = False, "confidence above threshold — stayed cheap"
    if confidence < threshold:
        try:
            final = llm.chat(task, system=system, provider=strong[0], tier=strong[1])
            attempts.append(final)
            escalated, note = True, "escalated to strong tier"
        except Exception as e:  # noqa: BLE001
            # Graceful degradation: a missing strong-tier key (or an
            # unreachable endpoint) keeps the cheap answer instead of
            # crashing the run — the table_row note records what happened.
            note = (f"wanted to escalate ({confidence:.2f} < {threshold}) but "
                    f"strong tier unavailable: {type(e).__name__}")
    text = attempts[-1].text if escalated else first.text
    cost = round(sum(a.cost_usd for a in attempts), 6)
    return RouteResult(
        text=text,
        escalated=escalated,
        confidence=round(confidence, 2),
        attempts=attempts,
        total_cost_usd=cost,
        table_row={
            "task": task[:60] + ("…" if len(task) > 60 else ""),
            "route": f"{first.model} -> {attempts[-1].model}" if escalated else first.model,
            "confidence": round(confidence, 2),
            "cost_usd": cost,
            "latency_s": round(sum(a.latency_s for a in attempts), 2),
            "note": note,
        },
    )
