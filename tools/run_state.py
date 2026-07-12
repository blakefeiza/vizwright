#!/usr/bin/env python3
"""Persist per-run pipeline state so a crashed or resumed session keeps its
place — especially the design-iteration counter behind the 3-try escape hatch,
which otherwise lives only in conversation context and resets on a restart.

State file: runs/<run>/iteration_state.json

  {
    "run": "superstore-profit-focus",
    "iteration": 2,
    "max_iterations": 3,
    "history": [
      {"iteration": 1, "score": 56, "verdict": "ITERATE", "ts": "..."},
      {"iteration": 2, "score": 92, "verdict": "PASS", "ts": "..."}
    ],
    "status": "passed"          # in_progress | passed | exhausted
  }

Orchestrator usage:
  python3 tools/run_state.py <run> get                 # print current state
  python3 tools/run_state.py <run> bump                # start a new iteration; exits 3 if over cap
  python3 tools/run_state.py <run> record --score 92 --verdict PASS
  python3 tools/run_state.py <run> reset

`bump` returns exit code 3 (not 1) when the cap is already reached, so the
orchestrator can distinguish "stop iterating, summarize what's stuck" from an
ordinary error.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def state_path(run: str) -> Path:
    return ROOT / "runs" / run / "iteration_state.json"


def load(run: str, max_iterations: int = 3) -> dict:
    p = state_path(run)
    if p.exists():
        return json.loads(p.read_text())
    return {"run": run, "iteration": 0, "max_iterations": max_iterations,
            "history": [], "status": "in_progress"}


def save(state: dict) -> None:
    p = state_path(state["run"])
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("action", choices=["get", "bump", "record", "reset"])
    ap.add_argument("--score", type=int)
    ap.add_argument("--verdict", choices=["PASS", "ITERATE"])
    ap.add_argument("--max", type=int, default=3)
    args = ap.parse_args()

    if args.action == "reset":
        save({"run": args.run, "iteration": 0, "max_iterations": args.max,
              "history": [], "status": "in_progress"})
        print(f"reset {args.run}")
        return 0

    state = load(args.run, args.max)

    if args.action == "get":
        print(json.dumps(state, indent=2))
        return 0

    if args.action == "bump":
        if state["iteration"] >= state["max_iterations"]:
            print(f"CAP REACHED: {state['iteration']}/{state['max_iterations']} "
                  f"iterations used for '{args.run}' — stop and summarize what's stuck.")
            state["status"] = "exhausted"
            save(state)
            return 3
        state["iteration"] += 1
        save(state)
        print(f"iteration {state['iteration']}/{state['max_iterations']} for '{args.run}'")
        return 0

    if args.action == "record":
        if args.score is None or args.verdict is None:
            sys.exit("record needs --score and --verdict")
        state["history"].append({
            "iteration": state["iteration"],
            "score": args.score, "verdict": args.verdict,
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
        if args.verdict == "PASS":
            state["status"] = "passed"
        elif state["iteration"] >= state["max_iterations"]:
            state["status"] = "exhausted"
        save(state)
        print(f"recorded iteration {state['iteration']}: {args.score}/100 {args.verdict} "
              f"(status: {state['status']})")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
