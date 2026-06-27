"""agentkit.evals — the house eval method, runnable against any project.

The pattern (straight from the event guide): a few cases in evals/evals.json,
each run WITH and WITHOUT the skill, assertions that are specific, observable,
countable; PASS/FAIL with evidence; aggregated into benchmark.json so the
with-skill delta is a number you can demo.

Run:    uv run python -m agentkit.evals projects/<theme>/<name> [--cases N]
Engine: uv run python -m agentkit.evals --selftest        (no model needed)

Evals always run with AGENT_OFFLINE=1 so results are deterministic and
reproducible — live APIs are for demos, fixtures are for measurement.

Agent contract every project follows:
    agent.py defines  run(task: str, skill: Path | None = ...) -> AgentResult | str

Assertion types (optional "where": "Section name" scopes any of them to one
markdown section): regex, not_regex, contains, contains_section,
count_min {pattern, min}, numeric_present, script {path}.
A script gets the agent output on stdin and the case JSON as argv[1];
exit 0 = pass (the escape hatch for checks like "the CSV parses").
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import NamedTuple


class CheckResult(NamedTuple):
    ok: bool
    evidence: str


# Small local models love fancy typography: U+202F/U+00A0 no-break spaces and
# U+2011 non-breaking hyphens look identical to humans but silently defeat
# exact-string assertions. Fold them before matching.
_TYPOGRAPHY = {0x202F: " ", 0x00A0: " ", 0x2011: "-"}


def _normalize(text: str) -> str:
    return text.translate(_TYPOGRAPHY)


_HEAD = re.compile(r"^\s{0,3}(?:(#{1,6})\s|\*\*[^*]+\*\*[:\s]*$|\d+\.\s+\*\*)")


def _head_level(line: str) -> int | None:
    """Heading rank: 1-6 for #-headings, 9 for bold/numbered pseudo-headings."""
    m = _HEAD.match(line)
    if not m:
        return None
    return len(m.group(1)) if m.group(1) else 9


def section(output: str, name: str) -> str:
    """Lines from the heading matching `name` to the next peer heading.

    Headings are #-lines, standalone **Bold** lines, or numbered '1. **Bold**'
    items. A #-section ends only at a #-heading of the same or shallower
    depth, so bold lines and deeper ### subsections INSIDE it don't truncate
    it; a bold pseudo-heading section ends at the next heading of any kind.
    """
    lines = _normalize(output).splitlines()
    name_re = re.compile(re.escape(name), re.I)
    start = level = None
    for i, ln in enumerate(lines):
        lvl = _head_level(ln)
        if lvl is not None and name_re.search(ln):
            start, level = i, lvl
            break
    if start is None:
        return ""
    end = len(lines)
    for j in range(start + 1, len(lines)):
        lvl = _head_level(lines[j])
        if lvl is not None and lvl <= level:
            end = j
            break
    return "\n".join(lines[start:end])


def check(output: str, a: dict, *, project_dir: Path, case: dict) -> CheckResult:
    """Evaluate one assertion against one output. Returns PASS/FAIL + evidence.

    Note: `script` assertions receive the RAW (un-normalized) output on stdin —
    scripts own their own robustness.
    """
    if a["type"] != "script":
        output = _normalize(output)
    where = a.get("where")
    scope = section(output, where) if where else output
    loc = f" in section {where!r}" if where else ""
    t = a["type"]
    if t == "regex":
        ok = bool(re.search(a["value"], scope, re.I | re.M))
        return CheckResult(ok, f"regex {a['value']!r}{loc}: {'found' if ok else 'NOT found'}")
    if t == "not_regex":
        m = re.search(a["value"], scope, re.I | re.M)
        return CheckResult(not m, f"forbidden {a['value']!r}{loc}: " + (f"matched {m.group()!r}" if m else "absent (good)"))
    if t == "contains":
        ok = a["value"].lower() in scope.lower()
        return CheckResult(ok, f"substring {a['value']!r}{loc}: {'found' if ok else 'NOT found'}")
    if t == "contains_section":
        ok = bool(section(output, a["value"]).strip())
        return CheckResult(ok, f"section {a['value']!r}: {'present' if ok else 'MISSING'}")
    if t == "count_min":
        n = len(re.findall(a["pattern"], scope, re.I | re.M))
        return CheckResult(n >= a["min"], f"{a['pattern']!r}{loc}: found {n}, need >= {a['min']}")
    if t == "numeric_present":
        ok = bool(re.search(r"\d+(?:\.\d+)?\s*%?", scope))
        return CheckResult(ok, f"number{loc}: {'present' if ok else 'MISSING'}")
    if t == "script":
        p = subprocess.run(
            [sys.executable, str(project_dir / a["path"]), json.dumps(case)],
            input=output, capture_output=True, text=True, timeout=60,
        )
        tail = (p.stderr or p.stdout).strip().splitlines()[-1:] or [""]
        return CheckResult(p.returncode == 0, f"script {a['path']}: exit {p.returncode} {tail[0][:120]}")
    return CheckResult(False, f"unknown assertion type {t!r}")


def load_project_run(project_dir: Path):
    """importlib-load <project>/agent.py and return its run() function."""
    agent_py = project_dir / "agent.py"
    if not agent_py.exists():
        raise FileNotFoundError(f"no agent.py in {project_dir}")
    sys.path.insert(0, str(project_dir))  # allow project-local imports (agents/, scripts/)
    spec = importlib.util.spec_from_file_location(f"agent_{project_dir.name}", agent_py)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.run


def run_evals(
    project_dir: str | Path,
    *,
    modes: tuple = ("with_skill", "without_skill"),
    provider: str | None = None,
    tier: str = "default",
    limit: int | None = None,
) -> dict:
    project_dir = Path(project_dir).resolve()
    os.environ["AGENT_OFFLINE"] = "1"  # measurement must be reproducible
    if provider:
        os.environ["MODEL_PROVIDER"] = provider
    spec = json.loads((project_dir / "evals" / "evals.json").read_text())
    run = load_project_run(project_dir)
    skill_dir = project_dir / spec["skill"]
    outdir = project_dir / "evals" / "outputs"
    outdir.mkdir(exist_ok=True)

    results = []
    for case in spec["cases"][:limit]:
        for mode in modes:
            t0 = time.perf_counter()
            out = run(case["input"], skill=(skill_dir if mode == "with_skill" else None))
            text = getattr(out, "text", None) or str(out)
            latency = round(time.perf_counter() - t0, 2)
            cost = float(getattr(out, "cost_usd", 0.0) or 0.0)
            checks = [check(text, a, project_dir=project_dir, case=case) for a in case["assertions"]]
            (outdir / f"{case['id']}-{mode}.md").write_text(text, encoding="utf-8")
            results.append({
                "case": case["id"], "mode": mode, "pass": all(c.ok for c in checks),
                "checks": [{"type": a["type"], "ok": c.ok, "evidence": c.evidence}
                           for a, c in zip(case["assertions"], checks)],
                "cost_usd": cost, "latency_s": latency,
                "output_path": f"evals/outputs/{case['id']}-{mode}.md",
            })
            mark = "PASS" if results[-1]["pass"] else "FAIL"
            print(f"[{mark}] {case['id']} ({mode})  {latency}s  ${cost}")
            for a, c in zip(case["assertions"], checks):
                print(f"       {'ok ' if c.ok else 'XX '} {c.evidence}")

    handle_model = os.getenv("AGENTKIT_MODEL") or os.getenv("LOCAL_MODEL", "")
    bench: dict = {
        "project": project_dir.name,
        "provider": os.getenv("MODEL_PROVIDER", "local"),
        "model_hint": handle_model,
        "modes": {},
        "results": results,
    }
    for mode in modes:
        rs = [r for r in results if r["mode"] == mode]
        if rs:
            bench["modes"][mode] = {
                "passed": sum(r["pass"] for r in rs), "total": len(rs),
                "pass_rate": round(sum(r["pass"] for r in rs) / len(rs), 2),
                "cost_usd": round(sum(r["cost_usd"] for r in rs), 6),
                "latency_s_avg": round(sum(r["latency_s"] for r in rs) / len(rs), 2),
            }
    if {"with_skill", "without_skill"} <= set(bench["modes"]):
        bench["delta"] = {
            "pass_rate": round(
                bench["modes"]["with_skill"]["pass_rate"]
                - bench["modes"]["without_skill"]["pass_rate"], 2)
        }
    # A limited run (--cases N) must not clobber the committed full benchmark.
    partial = limit is not None and limit < len(spec["cases"])
    bench["partial"] = partial
    out = project_dir / "evals" / ("benchmark.partial.json" if partial else "benchmark.json")
    out.write_text(json.dumps(bench, indent=2), encoding="utf-8")
    print(f"\nwrote {out}" + ("  (partial — committed benchmark.json left intact)" if partial else ""))
    for mode, s in bench["modes"].items():
        print(f"  {mode:>14}: {s['passed']}/{s['total']} pass  (${s['cost_usd']}, avg {s['latency_s_avg']}s)")
    if "delta" in bench:
        print(f"  with-skill delta: {bench['delta']['pass_rate']:+.2f} pass rate")
    return bench


# ── selftest: prove the assertion engine works, no model required ──────────

_FIXTURE = """# Civic Brief: Rodent Activity

## Headline finding
Rodent complaints rose 12% across Boston in the last 12 months.

## What we found
**By neighborhood** — counts from the datastore.
- Dorchester logged 1,204 cases.
- Allston rose 18%.
- South End fell 3%.

### Methodology note
Counts exclude duplicates.

## Caveats
- The current month is incomplete.
- Geocoding gaps affect 4% of records.

## Reproduce it
SELECT neighborhood, count(*) FROM cases GROUP BY 1
"""

_SELFTEST = [  # (assertion, expected_ok)
    ({"type": "contains_section", "value": "Headline finding"}, True),
    ({"type": "contains_section", "value": "Missing section"}, False),
    # bold lines and ### subsections inside a ## section must not truncate it:
    ({"type": "regex", "value": r"1,204", "where": "What we found"}, True),
    ({"type": "regex", "value": r"duplicates", "where": "What we found"}, True),
    ({"type": "regex", "value": r"data\.boston\.gov"}, False),
    ({"type": "regex", "value": r"SELECT", "where": "Reproduce it"}, True),
    ({"type": "not_regex", "value": r"TODO"}, True),
    ({"type": "not_regex", "value": r"rodent", "where": "Headline finding"}, False),
    ({"type": "contains", "value": "dorchester"}, True),
    ({"type": "count_min", "pattern": r"^- ", "min": 2, "where": "Caveats"}, True),
    ({"type": "count_min", "pattern": r"^- ", "min": 4, "where": "What we found"}, False),
    ({"type": "numeric_present", "where": "Headline finding"}, True),
]


def selftest() -> int:
    failures = 0
    with tempfile.TemporaryDirectory() as td:
        script = Path(td) / "check_ok.py"
        script.write_text("import sys; sys.exit(0 if 'Headline' in sys.stdin.read() else 1)\n")
        cases = _SELFTEST + [({"type": "script", "path": "check_ok.py"}, True)]
        for a, expected in cases:
            got = check(_FIXTURE, a, project_dir=Path(td), case={"id": "selftest"})
            ok = got.ok is expected
            failures += 0 if ok else 1
            print(f"{'ok  ' if ok else 'BAD '} {a['type']:<17} expected {expected}, got {got.ok}  ({got.evidence})")
    print(f"\nselftest: {len(_SELFTEST) + 1 - failures}/{len(_SELFTEST) + 1} engine checks behave as expected")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the house evals against a project dir.")
    ap.add_argument("project_dir", nargs="?", help="e.g. projects/everyday/fridge-whisperer")
    ap.add_argument("--selftest", action="store_true", help="test the assertion engine (no model)")
    ap.add_argument("--cases", type=int, default=None, help="limit number of cases")
    ap.add_argument("--mode", choices=["both", "with_skill", "without_skill"], default="both")
    ap.add_argument("--provider", default=None, help="local|anthropic|openai|gemini")
    ap.add_argument("--tier", default="default")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.project_dir:
        ap.error("project_dir required (or --selftest)")
    modes = ("with_skill", "without_skill") if args.mode == "both" else (args.mode,)
    run_evals(args.project_dir, modes=modes, provider=args.provider, tier=args.tier, limit=args.cases)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
