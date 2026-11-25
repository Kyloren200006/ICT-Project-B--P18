#!/usr/bin/env python3
"""Run every WP3 test suite and time the main commands, for the report's validation and reproducibility sections.

Writes (inside reports/wp3/):
  figures/data/test_results.csv     suite, folder, tests run, failures, errors, skipped, seconds, python version
  figures/data/command_timings.csv  command, seconds (wall clock, this computer, one run each)

Runs the suites with the same command the READMEs give: python -m unittest discover -s tests -t .  (inside each folder).
Timings are measured once on whatever computer this runs on; they are for orientation, not a benchmark.

Run:  py scripts/run_all_tests.py [--root DIR]
"""
import argparse
import csv
import os
import re
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.dirname(HERE)
DATA = os.path.join(REPORT, "figures", "data")

SUITES = [
    ("scoring engine", "wp3_scoring_engine"),
    ("aggregation scripts", "wp3_aggregation_scripts"),
    ("calibration and validation", "wp3_calibration"),
    ("dashboard", "wp3_dashboard"),
]


def run(cmd, cwd):
    t0 = time.perf_counter()
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p, time.perf_counter() - t0


def parse_unittest(text):
    ran = re.search(r"Ran (\d+) tests? in ([\d.]+)s", text)
    fails = re.search(r"FAILED \((.*?)\)", text)
    f = e = s = 0
    if fails:
        for part in fails.group(1).split(","):
            k, _, v = part.strip().partition("=")
            if k == "failures":
                f = int(v)
            elif k == "errors":
                e = int(v)
    sk = re.search(r"skipped=(\d+)", text)
    if sk:
        s = int(sk.group(1))
    return (int(ran.group(1)) if ran else 0), f, e, s


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=os.path.abspath(os.path.join(REPORT, "..", "..")))
    args = ap.parse_args(argv)
    py = sys.executable
    pyver = "%d.%d.%d" % sys.version_info[:3]
    os.makedirs(DATA, exist_ok=True)

    results, bad = [], 0
    for label, folder in SUITES:
        cwd = os.path.join(args.root, folder)
        p, secs = run([py, "-m", "unittest", "discover", "-s", "tests", "-t", "."], cwd)
        n, f, e, s = parse_unittest(p.stderr + p.stdout)
        if p.returncode != 0 or n == 0:
            bad += 1
        results.append([label, folder, n, f, e, s, "%.1f" % secs, pyver, "pass" if p.returncode == 0 else "FAIL"])
        print("%-28s %3d tests, %d failures, %d errors, %.1fs" % (label, n, f, e, secs))

    with open(os.path.join(DATA, "test_results.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["suite", "folder", "tests_run", "failures", "errors", "skipped", "seconds", "python", "result"])
        w.writerows(results)
        w.writerow(["TOTAL", "", sum(r[2] for r in results), sum(r[3] for r in results),
                    sum(r[4] for r in results), sum(r[5] for r in results), "", pyver,
                    "pass" if bad == 0 else "FAIL"])

    timings = []
    eng = os.path.join(args.root, "wp3_scoring_engine")
    agg = os.path.join(args.root, "wp3_aggregation_scripts")
    cal = os.path.join(args.root, "wp3_calibration")
    dash = os.path.join(args.root, "wp3_dashboard")
    with tempfile.TemporaryDirectory() as tmp:
        steps = [
            ("score the engine's 3 example runs (score_logs.py)",
             [py, "score_logs.py", "examples/example_runs.json", "--scenarios", "examples/scenario_lookup.csv",
              "--out", os.path.join(tmp, "engine")], eng),
            ("aggregate the 22-run test pack (aggregate_summaries.py)",
             [py, "aggregate_summaries.py", "examples/scored_runs.csv", "--scenarios", "examples/scenario_lookup.csv",
              "--out", os.path.join(tmp, "agg")], agg),
            ("calibration: score both validation sets and compare (run_calibration.py)",
             [py, "run_calibration.py", "--engine", eng, "--out", os.path.join(tmp, "cal")], cal),
            ("dashboard: export all 13 pages (dashboard.py --export)",
             [py, "dashboard.py", "--export", os.path.join(tmp, "site")], dash),
        ]
        for label, cmd, cwd in steps:
            p, secs = run(cmd, cwd)
            if p.returncode != 0:
                bad += 1
                print("FAILED:", label, p.stderr[-400:])
            timings.append([label, "%.2f" % secs, p.returncode])
            print("%-75s %.2fs (exit %d)" % (label, secs, p.returncode))
    with open(os.path.join(DATA, "command_timings.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["command", "seconds", "exit_code"])
        w.writerows(timings)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
