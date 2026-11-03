"""Tables (pandas DataFrames) and chart helpers for the Streamlit front end.

Everything the Streamlit app shows is worked out here, from the same `wp3_dash.data` functions that the
no-install launcher (dashboard.py) uses, so both front ends show the same numbers. Nothing in this module
imports Streamlit and nothing rescores a run: scores are read from the scored file exactly as written.

Blank cells ("-") always mean "not measured"; they are never shown as 0 or 1.
"""
from __future__ import annotations

import os
import re

import pandas as pd

from . import charts, data
from .data import to_float

DASH = "-"


def fmt(v, d=2):
    return DASH if v is None else ("%." + str(d) + "f") % v


def pct(v, d=0):
    return DASH if v is None else ("%." + str(d) + "f%%") % (v * 100)


def num(v):
    """Counts and other numbers kept as written (3 not 3.0)."""
    if v is None or v == "":
        return DASH
    f = to_float(v)
    if f is None:
        return str(v)
    return "%g" % f


# ----------------------------------------------------------------------------------------
# where the data comes from
# ----------------------------------------------------------------------------------------
EXAMPLE_LABEL = ("bundled example data: the 22-run WP3 test pack scored by the engine. These are test runs built "
                 "to exercise the metrics, not results for any real agent.")


def _first_existing(candidates):
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[-1]


def default_paths(root):
    """(definitions, scored, calibration folder, label). Uses input/ when files are there, else examples/."""
    d = os.path.join(root, "metric_definitions.yaml")
    s = _first_existing([os.path.join(root, "input", "scored_runs.csv"),
                         os.path.join(root, "input", "scored_runs.json"),
                         os.path.join(root, "examples", "scored_runs.csv")])
    c = _first_existing([os.path.join(root, "input", "calibration"),
                         os.path.join(root, "examples", "calibration")])
    label = EXAMPLE_LABEL if os.path.abspath(s).startswith(os.path.join(os.path.abspath(root), "examples")) else ""
    return d, s, c, label


# ----------------------------------------------------------------------------------------
# metric definitions
# ----------------------------------------------------------------------------------------
def definitions_frame(ctx):
    return pd.DataFrame([{
        "ID": m.id, "Metric": m.name, "Weight": fmt(m.weight), "Threshold": fmt(m.threshold),
        "Threshold rule": m.threshold_rule, "Formula": m.formula, "Linked WP1 risks": ", ".join(m.risk_ids),
    } for m in ctx.defs.metrics])


def bands_frame(ctx):
    return pd.DataFrame([{"Band": b["name"], "From": fmt(b["min"]), "To": fmt(b["max"])} for b in ctx.defs.bands])


def risk_frame(ctx):
    rows = []
    for rid, name in data.RISK_NAMES.items():
        linked = [m.id for m in ctx.defs.metrics if rid in m.risk_ids]
        rows.append({"ID": rid, "Threat": name, "Metrics": ", ".join(linked) or "none"})
    return pd.DataFrame(rows)


def weights_svg(ctx):
    defs = ctx.defs
    rows = [{"label": "%s %s" % (m.id, m.name.split()[0]), "value": m.weight, "text": fmt(m.weight),
             "title": "%s weight %s" % (m.id, fmt(m.weight))} for m in defs.metrics]
    return charts.hbar(rows, "Metric weights in the overall score",
                       vmax=max(0.3, max(m.weight for m in defs.metrics)), label_w=190)


def metric_detail(ctx, metric_id):
    """Text fields for one metric as (label, value) pairs, empty values left out."""
    m = ctx.defs.metric(metric_id)
    pairs = [("Description", m.description), ("Formula", m.formula), ("Weight", fmt(m.weight)),
             ("Threshold", "%s (%s)" % (fmt(m.threshold), m.threshold_rule)),
             ("Scoring", "%s: numerator = %s ; denominator = %s" % (m.kind, " + ".join(m.numerator), m.denominator)),
             ("Linked WP1 risks", ", ".join("%s %s" % (i, data.RISK_NAMES.get(i, "")) for i in m.risk_ids)),
             ("Risk mapping note", m.risk_mapping_note)]
    return [(k, v) for k, v in pairs if v not in ("", None)], m


# ----------------------------------------------------------------------------------------
# overview
# ----------------------------------------------------------------------------------------
def overview_numbers(ctx, runs):
    defs = ctx.defs
    overall = [r.overall for r in runs]
    m_overall = data.mean(overall)
    scored = [r for r in runs if r.overall is not None]
    low = min(scored, key=lambda r: r.overall) if scored else None
    cells = fails = 0
    for m in defs.metrics:
        for r in runs:
            s = r.scores.get(m.id)
            if s is not None:
                cells += 1
                if not data.passes(m, s):
                    fails += 1
    return {
        "runs": len(runs), "agents": len({r.agent for r in runs}),
        "mean_overall": m_overall, "mean_band": defs.band_for(m_overall),
        "lowest": low.overall if low else None, "lowest_run": ("%s / %s" % (low.run_id, low.scenario_id)) if low else "",
        "below": fails, "cells": cells,
    }


_BAND_CLS = ["good", "warn", "serious", "critical"]
_BAND_TXT = ["on-fill", "on-warn", "on-warn", "on-fill"]


def band_class(ctx, level):
    names = ctx.defs.band_names
    i = names.index(level) if level in names else len(_BAND_CLS) - 1
    i = min(i, len(_BAND_CLS) - 1)
    return _BAND_CLS[i], _BAND_TXT[i]


def bands_svg(ctx, runs):
    segs = []
    for name, n in data.level_counts(runs, ctx.defs):
        cls, txt = band_class(ctx, name)
        segs.append({"label": name, "count": n, "cls": "st-" + cls, "text_cls": txt})
    return charts.stacked_bar(segs, "Runs by risk band")


def band_counts_frame(ctx, runs):
    return pd.DataFrame([{"Band": n, "Runs": c} for n, c in data.level_counts(runs, ctx.defs)])


def means_svg(groups, title):
    rows = [{"label": k, "value": m, "text": "%s  (n=%d)" % (fmt(m), n),
             "title": "%s: mean overall %s over %d run%s" % (k, fmt(m, 3), n, "" if n == 1 else "s")}
            for k, m, n in groups]
    return charts.hbar(rows, title)


def pass_rate_svg(ctx, runs):
    rows = []
    for m in ctx.defs.metrics:
        st = data.metric_stats(m, runs)
        if st.pass_rate is None:
            rows.append({"label": m.id, "value": None, "text": "not measured in any run"})
        else:
            rows.append({"label": "%s %s" % (m.id, m.name.split()[0]), "value": st.pass_rate,
                         "text": "%s  (%d of %d)" % (pct(st.pass_rate), st.n_pass, st.n_measured),
                         "title": "%s: %d of %d measured runs meet the threshold (%s)" % (
                             m.id, st.n_pass, st.n_measured, m.threshold_rule)})
    return charts.hbar(rows, "Share of runs meeting each metric's threshold", width=600, label_w=190)


def agent_frame(ctx, runs):
    rows = []
    for a in data.agent_summary(runs, ctx.defs):
        row = {"Agent": a["agent"], "Runs": a["n"], "Mean overall": fmt(a["mean"], 3), "Band": a["level"]}
        for m in ctx.defs.metrics:
            row[m.id] = fmt(a["metric_means"][m.id])
        rows.append(row)
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------------------
# score distributions
# ----------------------------------------------------------------------------------------
def stats_for(ctx, runs):
    return {m.id: data.metric_stats(m, runs) for m in ctx.defs.metrics}


def hist_svg(m, st, width=300, height=150):
    passing = [data.bin_passes(m, i) for i in range(len(st.bins))]
    labels = [data.bin_label(i) for i in range(len(st.bins))]
    return charts.histogram(st.bins, m.threshold, passing,
                            "Score distribution of %s %s" % (m.id, m.name), width, height, labels)


def stats_frame(ctx, stats):
    rows = []
    for m in ctx.defs.metrics:
        st = stats[m.id]
        rows.append({"Metric": "%s %s" % (m.id, m.name), "Threshold": fmt(m.threshold), "Measured": st.n_measured,
                     "Not measured": st.n_not_measured, "Mean": fmt(st.mean), "Median": fmt(st.median),
                     "Min": fmt(st.minimum), "Meet threshold": pct(st.pass_rate)})
    return pd.DataFrame(rows)


def hist_table(ctx, stats):
    rows = []
    for i in range(data.N_BINS + 1):
        row = {"Score range": data.bin_label(i)}
        for m in ctx.defs.metrics:
            row[m.id] = stats[m.id].bins[i]
        rows.append(row)
    return pd.DataFrame(rows)


def by_agent_frame(m, runs):
    rows = []
    for agent in sorted({r.agent for r in runs}):
        s = data.metric_stats(m, [r for r in runs if r.agent == agent])
        rows.append({"Agent": agent, "Measured": s.n_measured, "Not measured": s.n_not_measured,
                     "Mean score": fmt(s.mean), "Meet threshold": pct(s.pass_rate)})
    return pd.DataFrame(rows)


def by_scenario_frame(m, runs):
    return pd.DataFrame([{
        "Scenario": r["scenario"], "Workflow": r["workflow"], "Type": r["type"], "Runs": r["runs"],
        "Measured": r["measured"], "Mean score": fmt(r["mean"]),
        "Counts (%s / %s)" % (" + ".join(m.numerator), m.denominator): "%g / %g" % (r["numerator"], r["denominator"]),
    } for r in data.scenario_rows(m, runs)])


def below_frame(m, runs):
    below = [r for r in runs if r.scores.get(m.id) is not None and not data.passes(m, r.scores[m.id])]
    rows = []
    for r in sorted(below, key=lambda r: r.scores[m.id]):
        row = {"Run": r.run_id, "Scenario": r.scenario_id, "Agent": r.agent, "Score": fmt(r.scores[m.id], 3)}
        for f in m.count_fields:
            row[f] = num(r.counts.get(f))
        rows.append(row)
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------------------
# runs
# ----------------------------------------------------------------------------------------
def runs_frame(ctx, runs):
    """One row per run. Scores below threshold carry an x so they are not marked by colour alone."""
    rows = []
    for r in runs:
        row = {"Run": r.run_id, "Scenario": r.scenario_id, "Agent": r.agent, "Workflow": r.workflow,
               "Type": r.scenario_type}
        for m in ctx.defs.metrics:
            s = r.scores.get(m.id)
            row[m.id] = DASH if s is None else (fmt(s) if data.passes(m, s) else fmt(s) + " x")
        row["Overall"] = fmt(r.overall, 3)
        row["Band"] = r.level
        rows.append(row)
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------------------
# calibration
# ----------------------------------------------------------------------------------------
def cal_tiles(cal):
    """[(label, value, note)] for the headline calibration numbers; empty when no files."""
    summ = data.cal_summary(cal)
    out = []
    if "pack" in summ:
        p = summ["pack"]
        out.append(("Test pack: results agreeing with hand labels", "%d of %d" % (p["agree"], p["cells"]),
                    "%d false alarms, %d misses" % (p["FP"], p["FN"])))
    if "probes" in summ:
        p = summ["probes"]
        out.append(("Probes: results agreeing with hand labels", "%d of %d" % (p["agree"], p["cells"]),
                    "%d false alarms, %d misses" % (p["FP"], p["FN"])))
    if "agreement" in summ:
        a = summ["agreement"]
        out.append(("Overall band agrees with hand-computed band", "%d of %d" % (a["band_agree"], a["runs"]),
                    "largest score difference %s" % fmt(a["max_abs_diff"], 3)))
    if "probes_table" in summ:
        p = summ["probes_table"]
        out.append(("Probe runs with the same trust decision", "%d of %d" % (p["decision_same"], p["n"]),
                    "%d of %d had exactly the same counts as the hand labels" % (p["counts_match"], p["n"])))
    return out


def cal_confusion_frame(cal):
    rows = []
    for r in cal.get("results") or []:
        rows.append({
            "Data": r["dataset"], "Metric": r["metric_id"], "Both measured": r["cells_both_measured"],
            "TP": r["TP"], "FP": r["FP"], "FN": r["FN"], "TN": r["TN"],
            "Engine not measured (flag / pass)": "%s / %s" % (r["engine_unmeasured_truth_flag"],
                                                            r["engine_unmeasured_truth_pass"]),
            "Engine extra": r["engine_extra"], "Precision": fmt(to_float(r["precision"])),
            "Recall": fmt(to_float(r["recall"])), "Mean abs score error": fmt(to_float(r["mean_abs_score_error"]), 3),
            "Counts differing": "%s of %s" % (r["count_fields_differing"], r["count_fields_compared"])})
    return pd.DataFrame(rows)


def cal_pr_svg(ctx, cal, field):
    by = {}
    for r in cal.get("results") or []:
        by.setdefault(r["dataset"], {})[r["metric_id"]] = r
    groups = []
    for m in ctx.defs.metrics:
        bars = []
        for ds in ("pack", "probes"):
            r = by.get(ds, {}).get(m.id)
            v = to_float(r.get(field)) if r else None
            if r is None:
                txt = "n/a"
            elif v is None:
                txt = "undefined (no flags)" if field == "precision" else "undefined"
            else:
                txt = fmt(v)
            bars.append({"value": v, "text": txt, "title": "%s on %s: %s %s" % (m.id, ds, field, txt)})
        groups.append({"label": m.id, "bars": bars})
    title = "%s per metric" % field.capitalize()
    return charts.grouped_hbar(groups, ["pack", "probes"], title, width=520, label_w=70)


def cal_threshold_frame(ctx, cal):
    by_metric = {}
    for r in cal.get("thresholds") or []:
        by_metric.setdefault(r["metric_id"], []).append(r)
    rows = []
    for m in ctx.defs.metrics:
        if m.id not in by_metric:
            continue
        parts = []
        for r in sorted(by_metric[m.id], key=lambda r: float(r["threshold_tested"])):
            chosen = r.get("is_chosen_threshold") == "yes"
            parts.append("%.2f%s: %s pass" % (float(r["threshold_tested"]), " (chosen)" if chosen else "",
                                              pct(to_float(r["pass_rate"]))))
        rows.append({"Metric": m.id, "Threshold: share passing": "; ".join(parts),
                     "Runs measured": by_metric[m.id][0]["runs_measured"],
                     "Most decisions changed": max(int(r["runs_changing_decision_vs_chosen"])
                                                   for r in by_metric[m.id])})
    return pd.DataFrame(rows)


def cal_bands_frame(cal):
    return pd.DataFrame([{
        "Change type": r["kind"].replace("_", " "), "Parameter": r["parameter"], "Change": r["change"],
        "Runs": r["runs_assessed"], "Runs changing band": r["runs_changing_band"],
        "Agent ranking kept": r["ranking_of_agents_preserved"], "Note": r["note"]}
        for r in cal.get("bands") or []])


def cal_probes_frame(cal):
    rows = []
    for r in cal.get("probes") or []:
        differs = r.get("trust_decision") == "differs"
        rows.append({"Probe": r["probe_id"], "Metric": r["targets"], "What was probed": r["description"],
                     "Weak point": r.get("weak_point_probed") or "", "Counts match": r["counts_match_truth"],
                     "Trust decision": "x differs" if differs else "same", "Outcome": r["outcomes"]})
    return pd.DataFrame(rows)


def cal_platform_frame(cal):
    return pd.DataFrame([{
        "Case": r["case"], "Tool in log": r["tool_name_in_log"], "Tool in label": r["tool_name_in_label"],
        "Count": r["count_field"], "Linux / macOS": r["linux_mac"], "Windows": r["windows"],
        "Same": r["same_on_both"]} for r in cal.get("platform") or []])


def cal_mismatch_frame(cal):
    return pd.DataFrame([{
        "Data": r["dataset"], "Run": r["run_id"], "Scenario": r["scenario_id"], "Metric": r["metric_id"],
        "Count field": r["field"], "Hand label": r["truth"], "Engine": r["engine"], "Weak point": r["weak_point"]}
        for r in cal.get("mismatches") or []])


def cal_agreement_frame(cal):
    return pd.DataFrame([{
        "Run": r["run_id"], "Scenario": r["scenario_id"], "Agent": r["agent_config"],
        "Hand label overall": r["truth_overall"], "Engine overall": r["engine_overall"],
        "Difference": r["abs_difference"], "Hand band": r["truth_band"], "Engine band": r["engine_band"],
        "Agrees": r["band_agrees"]} for r in cal.get("agreement") or []])


# ----------------------------------------------------------------------------------------
# data and checks
# ----------------------------------------------------------------------------------------
def inputs_frame(ctx):
    ck = ctx.checks
    rr = ctx.calibration.get("run_record") or {}
    rows = [
        {"Input": "Metric definitions file", "Location": ctx.defs.path,
         "Detail": "version %s, %s; %d metrics, weights sum %s" % (
             ctx.defs.version, ctx.defs.status, len(ctx.defs.metrics), fmt(sum(m.weight for m in ctx.defs.metrics)))},
        {"Input": "Scored runs file", "Location": ctx.scored_path,
         "Detail": "%d row%s, %d scored (completed), %d excluded (status not completed)" % (
             ck["total_rows"], "" if ck["total_rows"] == 1 else "s", len(ctx.runs), ck["excluded"])},
        {"Input": "Calibration folder", "Location": str(ctx.calibration.get("dir") or ""),
         "Detail": "%d of %d files found" % (len(ctx.calibration["found"]), len(data.CAL_FILES))},
    ]
    if rr:
        rows.append({"Input": "Calibration run record", "Location": "run_record.json",
                     "Detail": "calibration v%s, engine v%s, definitions v%s" % (
                         rr.get("calibration_version", "?"), rr.get("engine_version", "?"),
                         rr.get("metric_definitions_version", "?"))})
    return pd.DataFrame(rows)


def checks_frame(ctx):
    ck = ctx.checks
    rr = ctx.calibration.get("run_record") or {}
    mism = ctx.defs.version != str(rr.get("metric_definitions_version", ctx.defs.version))
    return pd.DataFrame([
        {"Check": "Score cells recomputed from counts", "Result": "%d checked" % ck["score_cells_checked"],
         "Note": "%d differ" % ck["score_cells_mismatch"]},
        {"Check": "Cells left blank because the scenario has no label (label_source = heuristic)",
         "Result": "%d" % ck["score_cells_unlabelled"], "Note": "designed engine rule, not counted as a difference"},
        {"Check": "Overall scores recomputed (weighted mean, weights rescaled over measured metrics)",
         "Result": "%d checked" % ck["overall_checked"], "Note": "%d differ" % ck["overall_mismatch"]},
        {"Check": "Definitions version matches the calibration run record", "Result": "no" if mism else "yes",
         "Note": ("calibration was run against definitions v%s" % rr.get("metric_definitions_version")) if mism else ""},
    ])


def checks_ok(ctx):
    ck = ctx.checks
    return not (ck.get("score_cells_mismatch") or ck.get("overall_mismatch")) and not ctx.warnings


# ----------------------------------------------------------------------------------------
# charts as something Streamlit can show
# ----------------------------------------------------------------------------------------
def svg_for_streamlit(svg, theme="light"):
    """A chart as a self-contained SVG string that starts with <svg> (what st.image accepts).
    The chart carries its own colours and a background, so it reads the same in Streamlit's light and dark themes."""
    doc = charts.standalone(svg, theme)
    return re.sub(r"^<\?xml[^>]*\?>\s*", "", doc).strip()
