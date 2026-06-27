"""deal-closah — sales & GTM agent. Lane 3: hub-and-spoke multi-agent system.

Four cooperating agents, five skills. The orchestrator routes every task to the
right specialist: ICP Scout, Outreach, Meeting Intel, or Deck Builder.

Commands:
    python agent.py "Find SaaS companies in Boston with 50-200 employees"
    python agent.py "Write a cold email to Acme Corp, contact: Jane Smith"
    python agent.py "Log meeting notes for Acme Corp: <paste notes>"
    python agent.py "Generate pre-meeting brief for Acme Corp"
    python agent.py "Build a pitch deck for Acme Corp"
    python agent.py "Find events my ICP attends in the fintech space"
    python agent.py --crm        (pipeline overview)
    python agent.py --no-skill   (eval baseline)
    python agent.py --offline    (use fixtures, no network)
"""

import argparse
import io
import os
import sys
from pathlib import Path

# Windows Unicode fix — model output can contain non-ASCII characters
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from agents import orchestrator

DEFAULT_SKILL = HERE / "skills" / "icp-profile"  # overridden by orchestrator routing


def run(task: str, skill=DEFAULT_SKILL):
    """The agent contract: run(task, skill=...) -> AgentResult."""
    return orchestrator.run(task, skill=skill)


def main():
    ap = argparse.ArgumentParser(description="deal-closah — sales & GTM agent")
    ap.add_argument("task", nargs="?", default="",
                    help='e.g. "Find SaaS companies in Boston with 50-200 employees"')
    ap.add_argument("--crm", action="store_true",
                    help="Show full CRM pipeline summary")
    ap.add_argument("--no-skill", action="store_true",
                    help="Run without skill (eval baseline)")
    ap.add_argument("--offline", action="store_true",
                    help="Use fixtures only — no network calls")
    args = ap.parse_args()

    if args.offline:
        os.environ["AGENT_OFFLINE"] = "1"

    task = "Show me the full CRM pipeline summary" if args.crm else args.task
    if not task:
        ap.print_help()
        sys.exit(0)

    result = run(task, skill=None if args.no_skill else DEFAULT_SKILL)
    print(result.text)

    routing_table = getattr(result, "__dict__", {}).get("routing_table", [])
    if routing_table:
        orchestrator.print_routing_table(routing_table)
    else:
        print(
            f"\n[{result.turns} turns · "
            f"{result.usage.get('prompt_tokens', 0)}+{result.usage.get('completion_tokens', 0)} tok"
            f" · ${result.cost_usd} · {result.latency_s}s]",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
