#!/usr/bin/env python3
"""Score one run-log file, or a whole folder of logs, with the WP3 scoring engine.

Simplest use: put WP4's logs in input/logs/ and the scenario lookup in input/scenarios/scenario_lookup.csv, then run

    py score_logs.py

Results are written to output/. To use other locations, give them explicitly:

    py score_logs.py path/to/logs_or_file --scenarios path/to/scenario_lookup.csv --out path/to/results

Writes scored_runs.csv/.json, run_inventory.csv and summary.json. The same input always gives identical output.
Same as:  python -m wp3_eval score ...   (use `python` instead of `py` on Mac/Linux)
"""
import pathlib
import sys

from wp3_eval.cli import main

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_LOGS = HERE / "input" / "logs"
DEFAULT_LOOKUP = HERE / "input" / "scenarios" / "scenario_lookup.csv"
DEFAULT_OUT = HERE / "output"


def build_args(argv):
    args = list(argv)
    has_input = bool(args) and not args[0].startswith("-")
    if not has_input:
        logs = [f for f in DEFAULT_LOGS.rglob("*") if f.is_file() and f.suffix.lower() in (".json", ".jsonl")] if DEFAULT_LOGS.is_dir() else []
        if not logs:
            print(f"No run logs found in {DEFAULT_LOGS}.\n"
                  "Put WP4's .json or .jsonl log files there, or give a path: py score_logs.py <log file or folder> ...",
                  file=sys.stderr)
            return None
        args = [str(DEFAULT_LOGS)] + args
    if "--scenarios" not in args and DEFAULT_LOOKUP.is_file():
        args += ["--scenarios", str(DEFAULT_LOOKUP)]
    if "--out" not in args:
        args += ["--out", str(DEFAULT_OUT)]
    return args


if __name__ == "__main__":
    a = build_args(sys.argv[1:])
    if a is None:
        raise SystemExit(2)
    raise SystemExit(main(["score"] + a))
