"""agentkit.llm — one client, four providers.

Every provider here speaks the OpenAI chat-completions dialect, so ONE code
path covers OpenAI, Anthropic (compat endpoint), Gemini (compat endpoint),
and any local OpenAI-compatible server: Ollama, Podman AI Lab, llama.cpp,
vLLM. Switch with a single env var:

    MODEL_PROVIDER = local | anthropic | openai | gemini      (default: local)

Tiers express the Model Selection discipline: route templated/cheap work to
``tier="cheap"`` (or local), open-ended judgment to ``tier="strong"``.
Every call returns a ChatResult with tokens, latency, and estimated cost —
the three numbers the judging rubric wants to see measured.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import NamedTuple

from openai import APIConnectionError, OpenAI

PROVIDERS = {
    "local": {
        "key_env": None,  # base_url/model come from LOCAL_* env vars
        "models": {},
        "hint": "set LOCAL_BASE_URL / LOCAL_MODEL (no API key needed)",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1/",
        "key_env": "ANTHROPIC_API_KEY",
        "models": {"default": "claude-sonnet-4-6", "strong": "claude-opus-4-8", "cheap": "claude-haiku-4-5"},
        "hint": "get a key at https://console.anthropic.com",
    },
    "openai": {
        "base_url": None,  # SDK default
        "key_env": "OPENAI_API_KEY",
        "models": {"default": "gpt-5.4-mini", "strong": "gpt-5.5", "cheap": "gpt-5.4-mini"},
        "hint": "get a key at https://platform.openai.com",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "key_env": "GEMINI_API_KEY",
        "models": {"default": "gemini-2.5-flash", "strong": "gemini-3.5-flash", "cheap": "gemini-2.5-flash-lite"},
        "hint": "free keys at https://aistudio.google.com",
    },
}

# $ per 1M tokens (input, output). Approximate, June 2026 — check current
# pricing at https://artificialanalysis.ai before quoting numbers to judges.
# Local models: ~$0 marginal, and that 2-3 orders-of-magnitude spread is the
# whole point of hybrid routing.
PRICES = {
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "gpt-5.5": (5.00, 30.00),
    "gpt-5.4-mini": (0.10, 0.60),
    "gpt-5.4": (2.50, 15.00),
    "gemini-3.5-flash": (0.50, 3.00),
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-flash-lite": (0.10, 0.40),
}

_TIER_OVERRIDES = {"default": "AGENTKIT_MODEL", "strong": "AGENTKIT_STRONG_MODEL", "cheap": "AGENTKIT_CHEAP_MODEL"}

_LOCAL_FIX = """\
Could not reach your local model at {base_url}.
  - Ollama:        ollama serve     (then: ollama pull llama3.1)
  - Podman AI Lab: Services -> your model service -> copy the port, then
                   export LOCAL_BASE_URL=http://localhost:<PORT>/v1
  - Test it:       curl {base_url}/models
Or use a frontier provider: export MODEL_PROVIDER=anthropic|openai|gemini (needs its API key)."""


class ModelHandle(NamedTuple):
    client: OpenAI
    model: str
    provider: str
    tier: str


class ChatResult(NamedTuple):
    text: str
    model: str
    provider: str
    usage: dict  # {"prompt_tokens": int, "completion_tokens": int}
    latency_s: float
    cost_usd: float
    tier: str = "default"  # which tier served this call — build routing tables for free


def _load_dotenv() -> None:
    """Tiny stdlib .env loader: repo root and cwd, never overrides real env."""
    for d in (Path.cwd(), Path(__file__).resolve().parent.parent):
        f = d / ".env"
        if f.is_file():
            for line in f.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()


def resolve(provider: str | None = None, tier: str = "default") -> ModelHandle:
    """Turn (provider, tier) into a ready client + model id.

    provider=None reads $MODEL_PROVIDER (default "local").
    tier is one of "default" | "strong" | "cheap".
    """
    name = (provider or os.getenv("MODEL_PROVIDER", "local")).lower()
    if name not in PROVIDERS:
        raise ValueError(f"unknown MODEL_PROVIDER {name!r} — pick one of {'|'.join(PROVIDERS)}")
    if tier not in _TIER_OVERRIDES:
        raise ValueError(f"unknown tier {tier!r} — pick default|strong|cheap")
    cfg = PROVIDERS[name]
    if name == "local":
        base_url = os.getenv("LOCAL_BASE_URL", "http://localhost:11434/v1")
        api_key = os.getenv("LOCAL_API_KEY", "not-needed")
        model = os.getenv("LOCAL_MODEL", "granite4:micro")  # local: every tier is the same model
    else:
        base_url = cfg["base_url"]
        api_key = os.getenv(cfg["key_env"] or "")
        if not api_key:
            raise RuntimeError(
                f"{cfg['key_env']} is not set ({cfg['hint']}). "
                f"Or run keyless: export MODEL_PROVIDER=local"
            )
        model = cfg["models"][tier]
    model = os.getenv(_TIER_OVERRIDES[tier]) or model
    return ModelHandle(OpenAI(base_url=base_url, api_key=api_key), model, name, tier)


def estimate_cost(model: str, usage: dict) -> float:
    """Estimated $ for one call; 0.0 for local/unknown models."""
    for prefix, (p_in, p_out) in PRICES.items():
        if model.startswith(prefix):
            return round(
                usage.get("prompt_tokens", 0) * p_in / 1e6
                + usage.get("completion_tokens", 0) * p_out / 1e6,
                6,
            )
    return 0.0


def chat_raw(
    messages: list[dict],
    *,
    tools: list[dict] | None = None,
    handle: ModelHandle | None = None,
    temperature: float = 0.2,
    json_mode: bool = False,
):
    """One chat-completions call. Returns (raw_response, ChatResult).

    This is the only place in the whole repo that talks to a model API.
    """
    handle = handle or resolve()
    kwargs: dict = {"model": handle.model, "messages": messages, "temperature": temperature}
    if tools:
        kwargs["tools"] = tools
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    t0 = time.perf_counter()
    try:
        resp = handle.client.chat.completions.create(**kwargs)
    except APIConnectionError as e:
        if handle.provider == "local":
            raise RuntimeError(_LOCAL_FIX.format(base_url=handle.client.base_url)) from e
        raise
    latency = round(time.perf_counter() - t0, 2)
    u = getattr(resp, "usage", None)
    usage = {
        "prompt_tokens": getattr(u, "prompt_tokens", 0) or 0,
        "completion_tokens": getattr(u, "completion_tokens", 0) or 0,
    }
    msg = resp.choices[0].message
    return resp, ChatResult(
        text=msg.content or "",
        model=handle.model,
        provider=handle.provider,
        usage=usage,
        latency_s=latency,
        cost_usd=estimate_cost(handle.model, usage),
        tier=handle.tier,
    )


def chat(
    prompt: str,
    *,
    system: str = "",
    provider: str | None = None,
    tier: str = "default",
    temperature: float = 0.2,
    json_mode: bool = False,
) -> ChatResult:
    """Single-turn convenience call (no tools)."""
    messages = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": prompt}
    ]
    _, result = chat_raw(
        messages, handle=resolve(provider, tier), temperature=temperature, json_mode=json_mode
    )
    return result
