"""agentkit — the tiny shared harness for the AgentDay-Example starters.

Four readable modules, ~400 lines total, zero framework magic:

- ``agentkit.llm``   one OpenAI-SDK client, four providers (local default)
- ``agentkit.loop``  the agent loop: @tool, load_skill, run_agent
- ``agentkit.route`` cascade routing (cheap first, escalate when unsure)
- ``agentkit.evals`` the house eval runner (with/without skill -> benchmark.json)

Read the source — it's the curriculum. Then fork a project and make it yours.
"""

from .llm import ChatResult, ModelHandle, chat, chat_raw, estimate_cost, resolve
from .loop import AgentResult, DEFAULT_SYSTEM, Skill, load_skill, run_agent, tool
from .route import RouteResult, cascade, self_grade

__version__ = "0.1.0"

__all__ = [
    "AgentResult", "ChatResult", "DEFAULT_SYSTEM", "ModelHandle", "RouteResult",
    "Skill", "cascade", "chat", "chat_raw", "estimate_cost", "load_skill",
    "resolve", "run_agent", "self_grade", "tool", "__version__",
]
