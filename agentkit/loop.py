"""agentkit.loop — an agent is a model in a loop with tools. That's the trick.

``run_agent()`` is the event's pillar-one definition in ~50 lines: send the
task, let the model call tools, feed results back, repeat until it answers.

Skills are procedural knowledge dropped into the system prompt — progressive
disclosure means the body is only loaded because the task matched. Passing
``skill=None`` IS the without-skill eval baseline; there is no second code path.
"""

from __future__ import annotations

import inspect
import json
import re
import sys
import time
from pathlib import Path
from typing import Callable, NamedTuple

import yaml

from . import llm

_PY2JSON = {str: "string", int: "integer", float: "number", bool: "boolean"}

DEFAULT_SYSTEM = (
    "You are a capable, concise agent. Use your tools when they help; "
    "answer directly once you have what you need."
)


def tool(fn: Callable | None = None, *, description: str | None = None):
    """Decorator: turn a plain function into an agent tool.

    The JSON schema is built from the signature (str/int/float/bool params)
    and the docstring — which means YOUR DOCSTRING IS A PROMPT. Write it for
    the model: what the tool does, and when to use it.
    """

    def wrap(f: Callable):
        props, required = {}, []
        for name, param in inspect.signature(f).parameters.items():
            ann = param.annotation if param.annotation is not inspect.Parameter.empty else str
            props[name] = {"type": _PY2JSON.get(ann, "string")}
            if param.default is inspect.Parameter.empty:
                required.append(name)
        f._tool_schema = {
            "type": "function",
            "function": {
                "name": f.__name__,
                "description": (description or f.__doc__ or f.__name__).strip(),
                "parameters": {"type": "object", "properties": props, "required": required},
            },
        }
        return f

    return wrap(fn) if fn else wrap


class Skill(NamedTuple):
    name: str
    description: str
    body: str
    dir: Path


def load_skill(skill_dir: str | Path) -> Skill:
    """Parse a SKILL.md (YAML frontmatter + markdown body) from a skill dir."""
    d = Path(skill_dir)
    text = (d / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not m:
        raise ValueError(f"{d}/SKILL.md has no YAML frontmatter (--- ... ---)")
    meta = yaml.safe_load(m.group(1)) or {}
    name = str(meta.get("name", ""))
    if name != d.name:
        raise ValueError(
            f"skill name {name!r} must match its directory name {d.name!r} "
            "(skills-ref validate enforces this too)"
        )
    return Skill(name, str(meta.get("description", "")), m.group(2).strip(), d)


class AgentResult(NamedTuple):
    text: str
    turns: int
    tool_calls: list  # [(name, args, result_snippet), ...]
    usage: dict
    cost_usd: float
    latency_s: float
    messages: list  # full transcript — pass back in to continue a session


def run_agent(
    task: str,
    *,
    tools: tuple | list = (),
    skill: str | Path | Skill | None = None,
    system: str = "",
    provider: str | None = None,
    tier: str = "default",
    max_turns: int = 10,
    verbose: bool = True,
    messages: list | None = None,
) -> AgentResult:
    """THE loop. Returns when the model answers without calling a tool.

    Pass ``messages=result.messages`` from a previous call to continue a
    session (the skill/system from that session rides along in messages[0]).
    """
    handle = llm.resolve(provider, tier)
    fns = {f.__name__: f for f in tools}
    schemas = [f._tool_schema for f in tools] or None

    if messages is None:
        parts = [system or DEFAULT_SYSTEM]
        if skill is not None:
            s = skill if isinstance(skill, Skill) else load_skill(skill)
            parts.append(f"A skill is loaded. Follow it exactly.\n\n# Skill: {s.name}\n\n{s.body}")
        messages = [{"role": "system", "content": "\n\n".join(parts)}]
    messages.append({"role": "user", "content": task})

    calls: list = []
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    cost, t0 = 0.0, time.perf_counter()

    for turn in range(1, max_turns + 1):
        resp, r = llm.chat_raw(messages, tools=schemas, handle=handle)
        usage = {k: usage[k] + r.usage.get(k, 0) for k in usage}
        cost += r.cost_usd
        msg = resp.choices[0].message

        if not msg.tool_calls:  # no tool call = the final answer (also how weak
            messages.append({"role": "assistant", "content": msg.content or ""})  # local models exit gracefully)
            return AgentResult(
                msg.content or "", turn, calls, usage,
                round(cost, 6), round(time.perf_counter() - t0, 2), messages,
            )

        # Re-encode the assistant turn as a minimal dict: maximally compatible
        # across the OpenAI / Anthropic-compat / Gemini-compat / llama.cpp dialects.
        messages.append({
            "role": "assistant",
            "content": msg.content or None,
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ],
        })
        for tc in msg.tool_calls:
            name, args = tc.function.name, {}
            try:
                args = json.loads(tc.function.arguments or "{}")
                out = str(fns[name](**args)) if name in fns else f"ERROR: unknown tool {name!r}"
            except Exception as e:  # bad JSON / tool blew up: tell the model, let it self-correct
                out = f"ERROR: {e}"
            if verbose:
                print(f"  -> {name}({(tc.function.arguments or '')[:90]})", file=sys.stderr)
            calls.append((name, args, out[:200]))
            # Truncate tool output: context is a budget, not a landfill.
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": out[:8000]})

    return AgentResult(
        f"(stopped after {max_turns} turns without a final answer)",
        max_turns, calls, usage, round(cost, 6), round(time.perf_counter() - t0, 2), messages,
    )
