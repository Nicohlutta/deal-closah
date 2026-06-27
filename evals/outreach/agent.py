"""Eval shim: exposes outreach.run for the agentkit eval runner."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from agents.outreach import run  # noqa: F401
