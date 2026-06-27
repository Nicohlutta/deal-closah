"""Eval shim: exposes icp_scout.run for the agentkit eval runner."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from agents.icp_scout import run  # noqa: F401
