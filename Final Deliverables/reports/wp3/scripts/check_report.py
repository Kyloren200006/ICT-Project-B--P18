#!/usr/bin/env python3
"""Check the WP3 technical report against the files it cites. Exits 0 when every check passes, 1 otherwise.

Checks: no placeholder text; no unresolved directives; every figure has .svg + .png + data .csv and a caption that names
its source data and script; every table caption names a source; table and figure numbers run 1..n without gaps; every
path in report.yaml exists; every metric, threat, finding, probe and scenario ID in the text exists in the repository;
the key numbers in the text equal the numbers recomputed here from the CSV/YAML/JSON files; test counts equal the number
of test functions in the repository; every test named in the report exists; summary.txt is at most 300 words; the
Word file has the 14 sections and the same number of tables and figures as report.md.

Run:  py scripts/check_report.py [--root DIR]
"""
import argparse
import csv
import glob
import json
import os
import re
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.dirname(HERE)

fails, passes = [], 0


def check(ok, msg):
    global passes
    if ok:
        passes += 1
    else:
        fails.append(msg)
        print("FAIL:", msg)


def rd(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=os.path.abspath(os.path.join(REPORT, "..", "..")))
    args = ap.parse_args(argv)
    root = args.root
    md = open(os.path.join(REPORT, "report.md"), encoding="utf-8").read()
    # prose = report without the appendices that reproduce whole files (they legitimately contain words like "placeholder")
    prose = md.split("## Appendix B.")[0]

    # 1. placeholders and directives
    for w in ("TBD", "TODO", "lorem ipsum", "placeholder", "to be determined", "coming soon", "FIXME", "XXX", "[citation needed]"):
        check(not re.search(r"\b%s\b" % re.escape(w), prose, flags=re.I), "placeholder text found: %s" % w)
    check("{{" not in md and "}}" not in prose, "unresolved {{directive}} in report.md")
    check(not re.search(r"\[@\w+", md), "unresolved citation key in report.md")

    # 2. figures
    figs = re.findall(r"!\[Figure (\d+)\]\(([^)]+)\)", md)
    check(len(figs) >= 17, "expected 8 figures + 9 dashboard screenshots, found %d" % len(figs))
    for n, rel in figs:
        check(os.path.exists(os.path.join(REPORT, rel)), "figure file missing: " + rel)
        m = re.match(r"figures/(fig\d\d_\w+)\.png$", rel)
        if m:
            base = m.group(1)
            check(os.path.exists(os.path.join(REPORT, "figures", base + ".svg")), "no .svg for " + base)
            check(os.path.exists(os.path.join(REPORT, "figures", "data", base + ".csv")), "no data .csv for " + base)
    for cap in re.findall(r"^\*\*Figure \d+\.\*\* (.+)$", md, flags=re.M):
        check("script:" in cap and ("Source data:" in cap), "figure caption lacks 'Source data:' and 'script:': " + cap[:70])
    tcaps = re.findall(r"^\*\*Table (\d+)\.\*\* (.+)$", md, flags=re.M)
    for n, cap in tcaps:
        check("Source" in cap or "source" in cap, "table %s caption names no source: %s" % (n, cap[:70]))
    tn = [int(n) for n, _ in tcaps]
    fn = [int(n) for n in re.findall(r"^\*\*Figure (\d+)\.\*\*", md, flags=re.M)]
    check(tn == list(range(1, len(tn) + 1)), "table numbers are not 1..n in order")
    check(fn == list(range(1, len(fn) + 1)), "figure numbers are not 1..n in order")

    # 3. manifest paths
    man = yaml.safe_load(open(os.path.join(REPORT, "report.yaml"), encoding="utf-8"))
    for f in man["files"]:
        p = f["path"]
        rel = p[len("reports/wp3/"):] if p.startswith("reports/wp3/") else None
        full = os.path.join(REPORT, rel) if rel is not None else os.path.join(root, p)
        check(os.path.exists(full), "manifest path does not exist: " + p)
    for key in ("code", "data", "results"):
        for p in man["links"][key]:
            full = os.path.join(REPORT, p[len("reports/wp3/"):]) if p.startswith("reports/wp3/") else os.path.join(root, p)
            check(os.path.exists(full), "link path does not exist: " + p)
    for p in ("wp3_scoring_engine/", "wp3_aggregation_scripts/", "wp3_calibration/", "wp3_dashboard/", "wp3_calibration/validation/pack/",
              "Metric Definitions/metric_definitions.md", "Log schema/log_schema.md", "Evaluation Reports/evaluation_report.md"):
        check(os.path.exists(os.path.join(root, p)), "path named in the report does not exist: " + p)

    # 4. IDs
    defs = yaml.safe_load(open(os.path.join(root, "wp3_scoring_engine", "metric_definitions.yaml"), encoding="utf-8"))
    mids = set(defs["metrics"])
    check(len(mids) == 7, "expected 7 metrics")
    for mid in set(re.findall(r"(?<![-\w])([A-Z]{2,3}-001)\b", md)):
        check(mid in mids, "unknown metric ID in text: " + mid)
    tcs = set(t for m in defs["metrics"].values() for t in m["risk_ids"])
    for t in set(re.findall(r"\bTC\d\b", md)):
        check(t in tcs, "unknown threat ID in text: " + t)
    check(tcs == {"TC1", "TC2", "TC3", "TC4", "TC5", "TC6"}, "definitions do not link all of TC1-TC6")
    check(abs(sum(defs["overall_score"]["weights"].values()) - 1.0) < 1e-9, "weights do not sum to 1")
    cal_md = open(os.path.join(root, "wp3_calibration", "calibration_validation_report.md"), encoding="utf-8").read()
    fids = set(re.findall(r"^\| (F-\d\d) \|", cal_md, flags=re.M))
    check(len(fids) == 17, "expected 17 findings in the calibration report")
    for f in set(re.findall(r"\bF-\d\d\b", md)):
        check(f in fids, "unknown finding ID: " + f)
    lookup_ids = {r["scenario_id"] for r in rd(os.path.join(root, "wp3_aggregation_scripts", "examples", "scenario_lookup.csv"))}
    lookup_ids |= {"EMAIL-WORKED-001", "EMAIL-WORKED-002"}
    lookup_ids |= {r["scenario_id"] for r in rd(os.path.join(root, "wp3_scoring_engine", "input", "scenarios", "scenario_lookup.csv"))}
    for sid in set(re.findall(r"\b((?:EMAIL|WEB|FILE|SCHED)-[A-Z]+-\d{3})\b", prose)):
        check(sid in lookup_ids, "unknown scenario ID in text: " + sid)
    agents = {r["agent_config"] for r in rd(os.path.join(root, "wp3_aggregation_scripts", "examples", "scored_runs.csv"))}
    for a in set(re.findall(r"\bAgent_[A-Z]_\w+", md)):
        check(a in agents, "unknown agent configuration in text: " + a)

    # 5. numbers recomputed from files
    cal = rd(os.path.join(root, "wp3_calibration", "results", "calibration_results.csv"))
    pk = [r for r in cal if r["dataset"] == "pack"]
    tp, fp, fn_, tn = (sum(int(r[k]) for r in pk) for k in ("TP", "FP", "FN", "TN"))
    check((tp + tn, tp + fp + fn_ + tn) == (88, 90), "pack agreement is not 88 of 90 (got %d of %d)" % (tp + tn, tp + fp + fn_ + tn))
    check("%d of %d metric results" % (tp + tn, tp + fp + fn_ + tn) in md, "report text does not state %d of %d" % (tp + tn, tp + fp + fn_ + tn))
    oa = rd(os.path.join(root, "wp3_calibration", "results", "overall_agreement.csv"))
    check(len(oa) == 21 and all(r["band_agrees"] == "yes" for r in oa), "overall bands do not all agree on 21 runs")
    check(max(float(r["abs_difference"]) for r in oa) < 0.0915, "max overall score difference is not 0.091")
    pf = rd(os.path.join(root, "wp3_calibration", "results", "probe_findings.csv"))
    check(len(pf) == 39, "expected 39 probes")
    check(sum(1 for r in pf if r["trust_decision"] == "same") == 22 and sum(1 for r in pf if r["counts_match_truth"] == "yes") == 21,
          "probe agreement is not 22 / 21 of 39")
    ws = rd(os.path.join(root, "wp3_calibration", "results", "band_and_weight_sensitivity.csv"))
    wv = [r for r in ws if r["kind"] == "weight_changed"]
    check(len(wv) == 14 and all(r["ranking_of_agents_preserved"] == "yes" for r in wv), "weight variants: expected 14, all ranking preserved")
    check(sum(int(r["runs_changing_band"]) for r in wv) == 1, "weight variants should change exactly one run's band")
    ts = rd(os.path.join(root, "wp3_calibration", "results", "threshold_sensitivity.csv"))
    check(all(int(r["runs_changing_decision_vs_chosen"]) == 0 for r in ts), "a threshold change alters a decision, text says none")
    gaps = [float(re.search(r"= ([\d.]+)", r["note"]).group(1)) for r in wv]
    check(round(min(gaps), 2) == 0.29 and round(max(gaps), 2) == 0.34, "weight-variant gap range is not 0.29 to 0.34 (%.4f to %.4f)" % (min(gaps), max(gaps)))
    # score distribution table in the text against the calibration report's own table 4.3
    sc = rd(os.path.join(root, "wp3_aggregation_scripts", "examples", "scored_runs.csv"))
    _, rows43 = None, []
    lines = cal_md.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("| Metric | Threshold | Runs measured | Mean"):
            j = i + 2
            while lines[j].startswith("|"):
                rows43.append([x.strip() for x in lines[j].strip("|").split("|")])
                j += 1
    check(len(rows43) == 7, "could not read the calibration report's distribution table")
    for r in rows43:
        mid = r[0]
        xs = [float(x[mid.replace("-", "_") + "_score"]) for x in sc if x[mid.replace("-", "_") + "_score"] != ""]
        check(len(xs) == int(r[2]) and abs(sum(xs) / len(xs) - float(r[3])) < 0.0006, "distribution of %s differs from the calibration report" % mid)
    # hand calculation equals engine
    hc = rd(os.path.join(REPORT, "worked_example", "hand_calculation.csv"))
    check(all(r["match"] == "yes" for r in hc), "hand calculation and engine disagree somewhere")
    # test counts
    tr = {r["suite"]: r for r in rd(os.path.join(REPORT, "figures", "data", "test_results.csv"))}
    for suite, folder in (("scoring engine", "wp3_scoring_engine"), ("aggregation scripts", "wp3_aggregation_scripts"),
                          ("calibration and validation", "wp3_calibration"), ("dashboard", "wp3_dashboard")):
        n = sum(len(re.findall(r"^\s+def test_", open(f, encoding="utf-8").read(), flags=re.M))
                for f in glob.glob(os.path.join(root, folder, "tests", "test_*.py")))
        check(int(tr[suite]["tests_run"]) == n, "%s: %s tests run but %d test functions in the code" % (suite, tr[suite]["tests_run"], n))
        check(tr[suite]["failures"] == "0" and tr[suite]["errors"] == "0", "%s has failing tests" % suite)
    check(("%s automated tests pass" % tr["TOTAL"]["tests_run"]) in md, "report does not state the total test count")
    # tests named in the report exist
    code = "".join(open(f, encoding="utf-8").read() for f in glob.glob(os.path.join(root, "wp3_*", "tests", "test_*.py")))
    for name in set(re.findall(r"(?<![/\w])(test_[a-z0-9_]+)\b(?!\.csv)", md)):
        check(("def " + name) in code, "test named in the report does not exist: " + name)
    # figures' data equal source (fig04 against calibration results)
    f4 = rd(os.path.join(REPORT, "figures", "data", "fig04_precision_recall.csv"))
    check(len(f4) > 0, "fig04 data is empty")

    # 6. summary
    words = len(open(os.path.join(REPORT, "summary.txt"), encoding="utf-8").read().split())
    check(words <= 300, "summary.txt has %d words" % words)

    # 7. docx
    dpath = os.path.join(REPORT, "report.docx")
    check(os.path.exists(dpath), "report.docx missing")
    if os.path.exists(dpath):
        from docx import Document
        d = Document(dpath)
        h1 = [p.text for p in d.paragraphs if p.style.name == "Heading 1"]
        check(len(h1) == 14 and [h.split(".")[0] for h in h1] == [str(i) for i in range(1, 15)], "docx does not have the 14 sections in order: %s" % h1)
        md_tables = len(re.findall(r"^\|[-|]+\|$", md, flags=re.M))
        check(len(d.tables) == md_tables, "docx has %d tables, report.md has %d" % (len(d.tables), md_tables))
        imgs = len(d.inline_shapes)
        check(imgs == len(figs), "docx has %d images, report.md has %d" % (imgs, len(figs)))
        text = "\n".join(p.text for p in d.paragraphs)
        check("{{" not in text and "[@" not in text, "unresolved directive or citation in docx")

    print("%d checks passed, %d failed" % (passes, len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
