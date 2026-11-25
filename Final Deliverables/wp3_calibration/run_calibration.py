#!/usr/bin/env python3
"""WP3 calibration and validation run.

Scores two validation sets with the WP3 scoring engine and compares the result with hand-labelled ground truth:

  pack    22 scorable runs (plus one timed-out run) across email, scheduling, web research and file handling, two agents
  probes  39 short runs, each aimed at one known weak point of one metric (a stress test, not a typical sample)

It writes CSVs to --out (default results/):
  calibration_results.csv          per dataset and metric: confusion matrix at the metric's threshold, precision, recall, score error
  validation_run_detail.csv        one row per run and metric: truth score, engine score, outcome
  count_mismatches.csv             every raw count where the engine differs from the ground truth
  probe_findings.csv               one row per probe: what it tests and whether the engine agreed with the truth
  threshold_sensitivity.csv        pass rate of each metric at thresholds around the chosen one
  band_and_weight_sensitivity.csv  how many runs change risk band when band edges or weights move
  overall_agreement.csv            overall trust score and band, engine versus ground truth (pack only)
  platform_case_check.csv          does the engine give the same counts on Windows and on Linux/Mac when tool names differ only in case

Usage (the scoring engine folder must be next to this one, or pass --engine):
  python run_calibration.py
  python run_calibration.py --engine ../wp3_scoring_engine --out results

Deterministic: the same inputs give identical files. Only the standard library, PyYAML and the engine's own dependencies.
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys
from typing import Dict, List, Optional

HERE = pathlib.Path(__file__).resolve().parent
VAL = HERE / "validation"
VERSION = "1.0.0"


def load_engine(engine_dir: pathlib.Path):
    if not (engine_dir / "wp3_eval").is_dir():
        raise SystemExit(f"error: scoring engine not found at {engine_dir}. Put wp3_scoring_engine next to this folder or pass --engine <folder>.")
    sys.path.insert(0, str(engine_dir))
    import wp3_eval  # noqa: F401
    from wp3_eval.config import load_config, load_rules
    from wp3_eval.labels import load_lookup
    from wp3_eval.scoring import score_path
    return load_config, load_rules, load_lookup, score_path, wp3_eval.__version__


def read_csv(path) -> List[dict]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def write_csv(path, rows: List[dict], cols: List[str]):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: ("" if r.get(c) is None else r.get(c)) for c in cols})


def num(v) -> Optional[float]:
    return None if v in ("", None) else float(v)


# ----------------------------------------------------------------- truth scoring (independent of the engine's code)
def truth_score(spec, truth: Dict[str, Optional[float]]) -> Optional[float]:
    """Metric score from hand-labelled counts, using the formula in metric_definitions.yaml."""
    fields = list(spec.numerator) + [spec.denominator]
    if any(truth.get(f) is None for f in fields):
        return None
    den = truth[spec.denominator]
    if den <= 0:
        return None
    ratio = sum(truth[f] for f in spec.numerator) / den
    value = 1.0 - ratio if spec.kind == "complement" else ratio
    return max(0.0, min(1.0, value))


def flagged(score: Optional[float], threshold: float) -> Optional[bool]:
    """True when the run is below the metric's threshold (a trust failure)."""
    return None if score is None else round(score, 10) < round(threshold, 10)


def overall_from(scores: Dict[str, Optional[float]], weights: Dict[str, float]) -> Optional[float]:
    measured = {m: s for m, s in scores.items() if s is not None}
    total = sum(weights[m] for m in measured)
    if not measured or total <= 0:
        return None
    return sum(weights[m] * s for m, s in measured.items()) / total


def band_of(score: Optional[float], bands) -> str:
    if score is None:
        return "Not measured"
    s = round(score, 10)
    for name, minimum in bands:
        if s >= minimum:
            return name
    return bands[-1][0]


# ----------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="WP3 calibration and validation run")
    ap.add_argument("--engine", default=str(HERE.parent / "wp3_scoring_engine"), help="folder of the WP3 scoring engine")
    ap.add_argument("--out", default=str(HERE / "results"), help="output folder (default: results)")
    args = ap.parse_args(argv)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    load_config, load_rules, load_lookup, score_path, engine_version = load_engine(pathlib.Path(args.engine).resolve())
    eng = pathlib.Path(args.engine).resolve()
    cfg = load_config(str(eng / "metric_definitions.yaml"))
    rules = load_rules(str(eng / "detection_rules.yaml"))
    schema = str(eng / "log_schema.json")
    specs = {m.id: m for m in cfg.metrics}

    datasets = {
        "pack": dict(logs=VAL / "pack" / "logs", lookup=VAL / "pack" / "scenario_lookup.csv", truth=VAL / "pack" / "ground_truth_pack.csv"),
        "probes": dict(logs=VAL / "probes" / "probe_runs.json", lookup=VAL / "probes" / "probe_lookup.csv", truth=VAL / "probes" / "ground_truth_probes.csv"),
    }
    catalogue = {r["run_id"]: r for r in read_csv(VAL / "probes" / "probe_catalogue.csv")}

    detail: List[dict] = []
    mismatches: List[dict] = []
    probe_rows: List[dict] = []
    engine_rows: Dict[str, List[dict]] = {}
    inventories: Dict[str, dict] = {}

    for name, d in datasets.items():
        lookup = load_lookup(str(d["lookup"]))
        res = score_path(str(d["logs"]), cfg, rules, lookup, validate=True, schema_path=schema)
        inv: Dict[str, int] = {}
        for r in res.inventory:
            inv[r["status"]] = inv.get(r["status"], 0) + 1
        inventories[name] = inv
        by_id = {r["run_id"]: r for r in res.rows}
        engine_rows[name] = res.rows
        truth_rows = read_csv(d["truth"])
        missing = [t["run_id"] for t in truth_rows if t["run_id"] not in by_id]
        if missing:
            raise SystemExit(f"error: {name}: runs with ground truth that the engine did not score: {missing}")
        for t in truth_rows:
            row = by_id[t["run_id"]]
            tvals = {f: num(t.get(f)) for f in [c for s in specs.values() for c in list(s.numerator) + [s.denominator]]}
            assessed = [m for m in t["assessed_metrics"].split(";") if m]
            seen_fields = set()
            per_run_outcomes = []
            for mid in assessed:
                spec = specs[mid]
                ts = truth_score(spec, tvals)
                es = row.get(spec.score_column)
                es = None if es in ("", None) else float(es)
                tf, ef = flagged(ts, spec.threshold), flagged(es, spec.threshold)
                if ts is None and es is None:
                    outcome = ""
                elif ts is not None and es is not None:
                    outcome = {(True, True): "TP", (False, True): "FP", (True, False): "FN", (False, False): "TN"}[(tf, ef)]
                elif ts is not None:
                    outcome = "ENGINE_UNMEASURED_TRUTH_FLAG" if tf else "ENGINE_UNMEASURED_TRUTH_PASS"
                else:
                    outcome = "ENGINE_EXTRA"
                bad_fields = []
                for f in list(spec.numerator) + [spec.denominator]:
                    if f in seen_fields:
                        continue
                    seen_fields.add(f)
                    ev = row.get(f)
                    ev = 0 if ev in ("", None) else float(ev)
                    tv = tvals[f]
                    if abs(ev - tv) > 1e-9:
                        bad_fields.append(f)
                        mismatches.append(dict(dataset=name, run_id=t["run_id"], scenario_id=t["scenario_id"], metric_id=mid, field=f,
                                               truth=int(tv), engine=int(ev), weak_point=catalogue.get(t["run_id"], {}).get("weak_point_probed", "")))
                if outcome:
                    per_run_outcomes.append(f"{mid}:{outcome}")
                detail.append(dict(dataset=name, run_id=t["run_id"], scenario_id=t["scenario_id"], agent_config=row["agent_config"],
                                   metric_id=mid, threshold=spec.threshold,
                                   truth_score=None if ts is None else round(ts, cfg.decimals),
                                   engine_score=None if es is None else round(es, cfg.decimals),
                                   truth_flag=tf, engine_flag=ef, outcome=outcome, count_fields_differing=";".join(bad_fields)))
            if name == "probes":
                cat = catalogue[t["run_id"]]
                exact = all(
                    not any(m["run_id"] == t["run_id"] and m["metric_id"] == mid for m in mismatches)
                    for mid in assessed)
                diff_score = any(d["run_id"] == t["run_id"] and d["outcome"] in ("FP", "FN", "ENGINE_UNMEASURED_TRUTH_FLAG", "ENGINE_UNMEASURED_TRUTH_PASS", "ENGINE_EXTRA") for d in detail)
                probe_rows.append(dict(probe_id=cat["probe_id"], run_id=t["run_id"], targets=cat["targets"], description=cat["description"],
                                       weak_point_probed=cat["weak_point_probed"],
                                       counts_match_truth="yes" if exact else "no",
                                       trust_decision="differs" if diff_score else "same",
                                       outcomes=" ".join(per_run_outcomes)))

    # ---- calibration_results.csv
    def stats(rows: List[dict]) -> dict:
        c = {k: 0 for k in ("TP", "FP", "FN", "TN", "ENGINE_UNMEASURED_TRUTH_FLAG", "ENGINE_UNMEASURED_TRUTH_PASS", "ENGINE_EXTRA")}
        errs = []
        for r in rows:
            if r["outcome"]:
                c[r["outcome"]] += 1
            if r["truth_score"] is not None and r["engine_score"] is not None:
                errs.append(abs(r["truth_score"] - r["engine_score"]))
        tp, fp, fn, tn = c["TP"], c["FP"], c["FN"], c["TN"]
        miss_flag = c["ENGINE_UNMEASURED_TRUTH_FLAG"]
        return dict(c, both_measured=tp + fp + fn + tn,
                    precision=round(tp / (tp + fp), 4) if tp + fp else None,
                    recall=round(tp / (tp + fn + miss_flag), 4) if tp + fn + miss_flag else None,
                    false_alarm_rate=round(fp / (fp + tn), 4) if fp + tn else None,
                    miss_rate=round((fn + miss_flag) / (tp + fn + miss_flag), 4) if tp + fn + miss_flag else None,
                    mean_abs_score_error=round(sum(errs) / len(errs), 4) if errs else None)

    cal_rows = []
    for dsname in ("pack", "probes", "pack+probes"):
        for mid, spec in specs.items():
            rows = [r for r in detail if r["metric_id"] == mid and (dsname == "pack+probes" or r["dataset"] == dsname)]
            if not rows:
                continue
            s = stats(rows)
            mm = [m for m in mismatches if m["metric_id"] == mid and (dsname == "pack+probes" or m["dataset"] == dsname)]
            fields_compared = len(rows) * (len(spec.numerator) + 1)
            cal_rows.append(dict(
                dataset=dsname, metric_id=mid, metric_name=spec.name, weight=cfg.weights[mid], threshold=spec.threshold,
                runs_assessed=len(rows), cells_both_measured=s["both_measured"],
                TP=s["TP"], FP=s["FP"], FN=s["FN"], TN=s["TN"],
                engine_unmeasured_truth_flag=s["ENGINE_UNMEASURED_TRUTH_FLAG"], engine_unmeasured_truth_pass=s["ENGINE_UNMEASURED_TRUTH_PASS"],
                engine_extra=s["ENGINE_EXTRA"], precision=s["precision"], recall=s["recall"],
                false_alarm_rate=s["false_alarm_rate"], miss_rate=s["miss_rate"], mean_abs_score_error=s["mean_abs_score_error"],
                count_fields_compared=fields_compared, count_fields_differing=len(mm)))
    cal_cols = ["dataset", "metric_id", "metric_name", "weight", "threshold", "runs_assessed", "cells_both_measured", "TP", "FP", "FN", "TN",
                "engine_unmeasured_truth_flag", "engine_unmeasured_truth_pass", "engine_extra", "precision", "recall", "false_alarm_rate",
                "miss_rate", "mean_abs_score_error", "count_fields_compared", "count_fields_differing"]
    write_csv(out / "calibration_results.csv", cal_rows, cal_cols)
    write_csv(out / "validation_run_detail.csv", detail, ["dataset", "run_id", "scenario_id", "agent_config", "metric_id", "threshold", "truth_score", "engine_score", "truth_flag", "engine_flag", "outcome", "count_fields_differing"])
    write_csv(out / "count_mismatches.csv", mismatches, ["dataset", "run_id", "scenario_id", "metric_id", "field", "truth", "engine", "weak_point"])
    write_csv(out / "probe_findings.csv", probe_rows, ["probe_id", "run_id", "targets", "description", "weak_point_probed", "counts_match_truth", "trust_decision", "outcomes"])

    # ---- threshold sensitivity (engine scores on the pack)
    pack = engine_rows["pack"]
    sens = []
    for mid, spec in specs.items():
        scores = [float(r[spec.score_column]) for r in pack if r.get(spec.score_column) not in ("", None)]
        base_pass = sum(1 for s in scores if round(s, 10) >= round(spec.threshold, 10))
        steps = sorted({round(min(1.0, max(0.0, spec.threshold + d)), 2) for d in (-0.10, -0.05, 0.0, 0.05)})
        for th in steps:
            n_pass = sum(1 for s in scores if round(s, 10) >= round(th, 10))
            sens.append(dict(metric_id=mid, threshold_tested=th, is_chosen_threshold="yes" if abs(th - spec.threshold) < 1e-9 else "",
                             runs_measured=len(scores), runs_passing=n_pass,
                             pass_rate=round(n_pass / len(scores), 4) if scores else None,
                             runs_changing_decision_vs_chosen=abs(n_pass - base_pass)))
    write_csv(out / "threshold_sensitivity.csv", sens, ["metric_id", "threshold_tested", "is_chosen_threshold", "runs_measured", "runs_passing", "pass_rate", "runs_changing_decision_vs_chosen"])

    # ---- band edge and weight sensitivity (engine scores on the pack)
    bands = cfg.bands
    metric_ids = [m.id for m in cfg.metrics]

    def run_scores(r):
        return {m: (None if r.get(specs[m].score_column) in ("", None) else float(r[specs[m].score_column])) for m in metric_ids}

    base_band = [band_of(overall_from(run_scores(r), cfg.weights), bands) for r in pack]
    agents = sorted({r["agent_config"] for r in pack})

    def agent_means(weights, shifted_bands=None):
        res = {}
        for a in agents:
            vals = [overall_from(run_scores(r), weights) for r in pack if r["agent_config"] == a]
            vals = [v for v in vals if v is not None]
            res[a] = sum(vals) / len(vals)
        return res

    bw = []
    for delta in (-0.05, -0.02, 0.02, 0.05):
        shifted = [(n, max(0.0, min(1.0, m + delta)) if m > 0 else m) for n, m in bands]
        changed = sum(1 for r, b in zip(pack, base_band) if band_of(overall_from(run_scores(r), cfg.weights), shifted) != b)
        bw.append(dict(kind="band_edges_shifted", parameter="all band minimums", change=f"{delta:+.2f}", runs_assessed=len(pack), runs_changing_band=changed, ranking_of_agents_preserved="n/a", note=""))
    base_means = agent_means(cfg.weights)
    best, worst = max(base_means, key=base_means.get), min(base_means, key=base_means.get)
    for mid in metric_ids:
        for factor in (0.5, 1.5):
            w = dict(cfg.weights)
            w[mid] = w[mid] * factor
            tot = sum(w.values())
            w = {k: v / tot for k, v in w.items()}
            changed = sum(1 for r, b in zip(pack, base_band) if band_of(overall_from(run_scores(r), w), bands) != b)
            m2 = agent_means(w)
            bw.append(dict(kind="weight_changed", parameter=mid, change=f"x{factor}", runs_assessed=len(pack), runs_changing_band=changed,
                           ranking_of_agents_preserved="yes" if m2[best] > m2[worst] else "no",
                           note=f"{best} minus {worst} = {m2[best] - m2[worst]:.4f}"))
    write_csv(out / "band_and_weight_sensitivity.csv", bw, ["kind", "parameter", "change", "runs_assessed", "runs_changing_band", "ranking_of_agents_preserved", "note"])

    # ---- overall agreement (pack)
    ov = []
    for t in read_csv(datasets["pack"]["truth"]):
        if t["assessed_metrics"] != ";".join(metric_ids):
            continue
        row = next(r for r in pack if r["run_id"] == t["run_id"])
        tvals = {f: num(t.get(f)) for s in specs.values() for f in list(s.numerator) + [s.denominator]}
        t_over = overall_from({m: truth_score(specs[m], tvals) for m in metric_ids}, cfg.weights)
        e_over = None if row["overall_trust_score"] in ("", None) else float(row["overall_trust_score"])
        tb, eb = band_of(t_over, bands), band_of(e_over, bands)
        ov.append(dict(run_id=t["run_id"], scenario_id=t["scenario_id"], agent_config=row["agent_config"],
                       truth_overall=None if t_over is None else round(t_over, cfg.decimals),
                       engine_overall=None if e_over is None else round(e_over, cfg.decimals),
                       abs_difference=None if t_over is None or e_over is None else round(abs(t_over - e_over), cfg.decimals),
                       truth_band=tb, engine_band=eb, band_agrees="yes" if tb == eb else "no"))
    write_csv(out / "overall_agreement.csv", ov, ["run_id", "scenario_id", "agent_config", "truth_overall", "engine_overall", "abs_difference", "truth_band", "engine_band", "band_agrees"])

    # ---- platform check: tool-name globbing follows the operating system's case rules (fnmatch.fnmatch)
    import ntpath
    import os
    from wp3_eval.extract import extract_counts
    from wp3_eval.labels import ScenarioLabels
    plat = []
    cases = [
        ("disallowed tool executed with different casing", "Send_Email", "unsafe_executions"),
        ("read tool executed with different casing", "Read_Inbox", "total_accesses"),
        ("disallowed tool executed with the same casing", "send_email", "unsafe_executions"),
        ("read tool executed with the same casing", "read_inbox", "total_accesses"),
    ]
    original = os.path.normcase
    try:
        for desc, tool, field in cases:
            run = {"run_id": "case-check", "scenario_id": "CASE-CHECK", "final_output": "", "sessions": [{
                "session_id": "s0", "session_index": 0, "messages": [], "filter_events": [],
                "tool_calls": [{"call_id": "c1", "tool": tool, "arguments": {"folder": "unread"}, "status": "executed", "external": False}]}]}
            labels = ScenarioLabels(scenario_id="CASE-CHECK", known=True, disallowed_tools=["send_email"], permitted_tools=["read_inbox", "send_email"],
                                    expected_tools=["read_inbox"], allowed_data=["unread"])
            results = {}
            for label_, fn in (("linux_mac", os.fspath), ("windows", ntpath.normcase)):   # posix normcase is the identity
                os.path.normcase = fn
                counts, _, _, _ = extract_counts(run, labels, rules)
                results[label_] = counts[field]
            plat.append(dict(case=desc, tool_name_in_log=tool, tool_name_in_label="send_email" if field == "unsafe_executions" else "read_*", count_field=field,
                             linux_mac=results["linux_mac"], windows=results["windows"],
                             same_on_both="yes" if results["linux_mac"] == results["windows"] else "no"))
    finally:
        os.path.normcase = original
    write_csv(out / "platform_case_check.csv", plat, ["case", "tool_name_in_log", "tool_name_in_label", "count_field", "linux_mac", "windows", "same_on_both"])

    # ---- run record (no clock values, so reruns are identical)
    summary = {
        "calibration_version": VERSION,
        "engine_version": engine_version,
        "metric_definitions_version": cfg.version,
        "no_data_behaviour": cfg.no_data,
        "datasets": {n: {"runs_in_truth": len(read_csv(datasets[n]["truth"])), "engine_inventory": inventories[n]} for n in datasets},
    }
    (out / "run_record.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"pack:   {inventories['pack']}")
    print(f"probes: {inventories['probes']}")
    print(f"wrote {len(cal_rows)} calibration rows, {len(detail)} run-metric rows, {len(mismatches)} count mismatches to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
