#!/usr/bin/env python3
"""Regenerate every figure in the WP3 technical report: figures/figNN_*.svg (editable text), .png, and the data
behind each figure in figures/data/figNN_*.csv.

Reads only files in the repository:
  wp3_scoring_engine/metric_definitions.yaml
  wp3_aggregation_scripts/examples/scored_runs.csv            (engine output on the 22-run test pack)
  wp3_aggregation_scripts/examples/expected_output/summary_by_agent.csv
  wp3_calibration/results/*.csv

Run:  py scripts/make_figures.py [--root DIR]      (needs matplotlib and PyYAML)
"""
import argparse
import csv
import math
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402
import yaml  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.dirname(HERE)
FIG = os.path.join(REPORT, "figures")
DATA = os.path.join(FIG, "data")

# colours: the validated default palette (light mode), status colours kept for status only
INK, INK2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
S = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
CRIT = "#d03b3b"

plt.rcParams.update({
    "svg.fonttype": "none",                   # keep text as text so the SVG stays editable
    "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans", "Arial"],
    "font.size": 9, "axes.edgecolor": AXIS, "axes.linewidth": 0.8, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "text.color": INK, "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE, "axes.spines.top": False, "axes.spines.right": False,
})


def rd(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def wr(name, header, rows):
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, name), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def save(fig, name):
    os.makedirs(FIG, exist_ok=True)
    fig.savefig(os.path.join(FIG, name + ".svg"))
    fig.savefig(os.path.join(FIG, name + ".png"), dpi=200)
    plt.close(fig)


def f(x):
    return None if x in ("", None) else float(x)


# ---------------------------------------------------------------------------------------------------------------
def fig_architecture():
    """Figure 1: the scoring pipeline. The boxes and arrows are listed in fig01_architecture*.csv."""
    fig, ax = plt.subplots(figsize=(11, 5.4))
    ax.set_xlim(0, 104)
    ax.set_ylim(0, 57)
    ax.axis("off")
    W, H = 17.5, 12
    boxes = {  # id: (x, y, title, subtitle, kind)
        "logs": (1, 40, "WP4 run logs", ".json / .jsonl\nschema v0.1", "input"),
        "loader": (22, 40, "loader.py", "read and validate against\nlog_schema.json", "code"),
        "extract": (43, 40, "extract.py", "rule-based counts\n(14 count fields)", "code"),
        "metrics": (64, 40, "metrics.py", "formulas: counts to\nseven metric scores", "code"),
        "scoring": (85, 40, "scoring.py", "overall score and band,\nwrite output files", "code"),
        "lookup": (22, 21, "WP2 scenario labels", "scenario_lookup.csv\n(matched by scenario_id)", "input"),
        "rules": (43, 21, "detection_rules.yaml", "tool-name patterns, phrases,\nmemory settings", "config"),
        "defs": (64, 21, "metric_definitions.yaml", "weights, thresholds, bands,\nformulas, linked risks", "config"),
        "out": (85, 21, "Engine output files", "scored_runs.csv / .json\nrun_inventory.csv\nsummary.json", "output"),
        "agg": (64, 2, "aggregate_summaries.py", "per agent, workflow,\nrisk and scenario", "code"),
        "dash": (85, 2, "streamlit_app.py", "definitions, distributions,\ncalibration results", "code"),
    }
    colour = {"input": "#cde2fb", "code": "#ffffff", "output": "#cde2fb", "config": "#f0efec"}
    for k, (x, y, t, sub, kind) in boxes.items():
        ax.add_patch(FancyBboxPatch((x, y), W, H, boxstyle="round,pad=0.0,rounding_size=1.2", fc=colour[kind],
                                    ec=S[0] if kind in ("input", "output") else AXIS, lw=1.0))
        ax.text(x + W / 2, y + H - 2.6, t, ha="center", va="center", fontsize=8.2, fontweight="bold", color=INK)
        ax.text(x + W / 2, y + H / 2 - 2.0, sub, ha="center", va="center", fontsize=7.8, color=INK2, linespacing=1.25)

    def arrow(p, q, dashed=False):
        ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=9, lw=1.0 if not dashed else 0.9,
                                     color=INK2 if not dashed else MUTED, linestyle=(0, (3, 2)) if dashed else "-",
                                     shrinkA=0, shrinkB=0))
    row = 46
    arrow((18.5, row), (22, row))
    arrow((39.5, row), (43, row))
    arrow((60.5, row), (64, row))
    arrow((81.5, row), (85, row))
    arrow((93.75, 40), (93.75, 33))
    arrow((88, 21), (78, 14))
    arrow((96, 21), (96, 14))
    arrow((81.5, 8), (85, 8))
    arrow((36, 33), (45, 40))                      # WP2 labels -> extract.py
    arrow((51.75, 33), (51.75, 40), dashed=True)   # rules -> extract.py
    arrow((72.75, 33), (72.75, 40), dashed=True)   # definitions -> metrics.py
    arrow((79, 33), (89, 40), dashed=True)         # definitions -> scoring.py
    ax.text(0, 56, "Blue: files other teams supply or the engine writes.  White: WP3 code.  Grey: settings files (data, not code); dashed arrows show which code reads them.",
            fontsize=8, color=INK2, va="top")
    save(fig, "fig01_architecture")
    wr("fig01_architecture.csv", ["node", "label", "kind"], [[k, v[2], v[4]] for k, v in boxes.items()])
    edges = [("logs", "loader", "run records"), ("loader", "extract", "valid runs"), ("extract", "metrics", "counts"),
             ("metrics", "scoring", "scores"), ("scoring", "out", "rows"), ("out", "agg", "scored_runs.csv"),
             ("out", "dash", "scored_runs.csv"), ("agg", "dash", "summaries"), ("lookup", "extract", "labels"),
             ("rules", "extract", "rules"), ("defs", "metrics", "formulas"), ("defs", "scoring", "weights, bands")]
    wr("fig01_architecture_edges.csv", ["from", "to", "label"], [list(e) for e in edges])


def fig_weights(defs):
    ms = [(k, v["name"], defs["overall_score"]["weights"][k], v["threshold"]) for k, v in defs["metrics"].items()]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)
    ys = list(range(len(ms)))[::-1]
    for ax, idx, title, vmax in ((axes[0], 2, "Weight in the overall score", 0.30), (axes[1], 3, "Threshold (acceptable at or above)", 1.0)):
        ax.barh(ys, [m[idx] for m in ms], color=S[0], height=0.55)
        for y, m in zip(ys, ms):
            ax.text(m[idx] + vmax * 0.015, y, "%.2f" % m[idx], va="center", fontsize=8.5, color=INK)
        ax.set_xlim(0, vmax * 1.12)
        ax.set_title(title, fontsize=9.5, loc="left", color=INK)
        ax.grid(axis="x", color=GRID, lw=0.6)
        ax.set_axisbelow(True)
    axes[0].set_yticks(ys)
    axes[0].set_yticklabels(["%s  %s" % (m[0], m[1]) for m in ms], fontsize=8.5)
    fig.tight_layout()
    save(fig, "fig02_weights_thresholds")
    wr("fig02_weights_thresholds.csv", ["metric_id", "name", "weight", "threshold"], [[m[0], m[1], m[2], m[3]] for m in ms])


def fig_distributions(defs, runs):
    ids = list(defs["metrics"])
    nb = 21
    fig, axes = plt.subplots(2, 4, figsize=(11, 5.0))
    rows = []
    for ax, mid in zip(axes.flat, ids):
        spec = defs["metrics"][mid]
        col = spec["column"] + "_score"
        vals = [f(r[col]) for r in runs if f(r[col]) is not None]
        bins = [0] * nb
        for v in vals:
            bins[nb - 1 if v >= 1 - 1e-9 else min(nb - 2, int(v * 20 + 1e-9))] += 1
        thr = spec["threshold"]
        cols = [S[0] if (i / 20.0) >= thr - 1e-9 else CRIT for i in range(nb)]
        ax.bar(range(nb), bins, color=cols, width=0.78)
        ax.axvline(round(thr * 20) - 0.5, color=INK, lw=1.2, ls=(0, (4, 3)))
        ax.set_title("%s  (n=%d)" % (mid, len(vals)), fontsize=9, loc="left", color=INK)
        ax.set_xticks([0, 10, 20])
        ax.set_xticklabels(["0", "0.5", "1.0"], fontsize=8)
        ax.set_xlim(-0.8, nb - 0.2)
        ax.tick_params(axis="y", labelsize=8)
        ax.yaxis.get_major_locator().set_params(integer=True)
        ax.grid(axis="y", color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        ax.text(round(thr * 20) - 0.9, ax.get_ylim()[1] * 0.97, "threshold %.2f" % thr, ha="right" if thr > 0.6 else "left",
                va="top", fontsize=7.5, color=INK)
        for i, c in enumerate(bins):
            rows.append([mid, i, "1.00" if i == 20 else "%.2f-%.2f" % (i / 20, (i + 1) / 20), c, "yes" if (i / 20.0) >= thr - 1e-9 else "no"])
    ax = axes.flat[-1]
    ax.axis("off")
    ax.text(0, 0.8, "Blue bars: score meets the threshold", fontsize=8.5, color=INK, va="top")
    ax.text(0, 0.62, "Red bars: score is below the threshold", fontsize=8.5, color=INK, va="top")
    ax.text(0, 0.44, "Dashed line: the threshold", fontsize=8.5, color=INK, va="top")
    ax.text(0, 0.26, "Bars are 0.05 wide; the last bar is\nexactly 1.00. Runs where the metric was\nnot measured are not counted.", fontsize=8, color=INK2, va="top")
    fig.tight_layout()
    save(fig, "fig03_pack_score_distributions")
    wr("fig03_pack_score_distributions.csv", ["metric_id", "bin_index", "bin_range", "runs", "meets_threshold"], rows)


def fig_precision_recall(cal):
    ids = ["DM-001", "PIR-001", "UAE-001", "SIL-001", "MI-001", "EA-001", "ETL-001"]
    by = {(r["dataset"], r["metric_id"]): r for r in cal}
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.8), sharey=True)
    ys = list(range(len(ids)))[::-1]
    rows = []
    for ax, field, title in ((axes[0], "precision", "Precision"), (axes[1], "recall", "Recall")):
        for k, (ds, col) in enumerate((("pack", S[0]), ("probes", S[1]))):
            for y, mid in zip(ys, ids):
                v = f(by[(ds, mid)][field])
                yy = y + (0.17 if k == 0 else -0.17)
                if v is None:
                    ax.text(0.01, yy, "undefined", va="center", fontsize=7.5, color=MUTED)
                else:
                    ax.barh(yy, v, height=0.3, color=col)
                    ax.text(v + 0.015, yy, "%.2f" % v, va="center", fontsize=7.5, color=INK)
                if field == "precision":
                    rows.append([ds, mid, by[(ds, mid)]["precision"], by[(ds, mid)]["recall"], by[(ds, mid)]["TP"], by[(ds, mid)]["FP"],
                                 by[(ds, mid)]["FN"], by[(ds, mid)]["TN"]])
        ax.set_xlim(0, 1.15)
        ax.set_title(title, fontsize=9.5, loc="left", color=INK)
        ax.grid(axis="x", color=GRID, lw=0.6)
        ax.set_axisbelow(True)
    axes[0].set_yticks(ys)
    axes[0].set_yticklabels(ids, fontsize=8.5)
    h = [plt.Rectangle((0, 0), 1, 1, color=S[0]), plt.Rectangle((0, 0), 1, 1, color=S[1])]
    fig.legend(h, ["test pack (22 runs)", "probes (39 runs)"], loc="lower center", ncol=2, frameon=False, fontsize=8.5)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    save(fig, "fig04_precision_recall")
    wr("fig04_precision_recall.csv", ["dataset", "metric_id", "precision", "recall", "TP", "FP", "FN", "TN"], rows)


def fig_overall_agreement(ag):
    fig, ax = plt.subplots(figsize=(4.8, 4.4))
    xs = [f(r["truth_overall"]) for r in ag]
    ys = [f(r["engine_overall"]) for r in ag]
    ax.plot([0, 1], [0, 1], color=AXIS, lw=1)
    same = [(x, y) for x, y in zip(xs, ys) if abs(x - y) < 5e-7]
    diff = [(x, y, r["run_id"]) for x, y, r in zip(xs, ys, ag) if abs(x - y) >= 5e-7]
    ax.scatter([a for a, _ in same], [b for _, b in same], s=34, color=S[0], zorder=3, label="engine equals hand label (%d runs)" % len(same))
    ax.scatter([a for a, _, _ in diff], [b for _, b, _ in diff], s=34, color=S[1], zorder=3, label="engine differs (%d runs)" % len(diff))
    for x, y, rid in diff:
        ax.annotate(rid, (x, y), textcoords="offset points", xytext=(6, -10), fontsize=8, color=INK)
    ax.set_xlabel("Overall trust score from hand-labelled counts")
    ax.set_ylabel("Overall trust score from the engine")
    ax.set_xlim(-0.03, 1.03)
    ax.set_ylim(-0.03, 1.03)
    ax.set_aspect("equal")
    ax.grid(color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", frameon=False, fontsize=8)
    fig.tight_layout()
    save(fig, "fig05_overall_agreement")
    wr("fig05_overall_agreement.csv", ["run_id", "truth_overall", "engine_overall", "abs_difference", "truth_band", "engine_band"],
       [[r["run_id"], r["truth_overall"], r["engine_overall"], r["abs_difference"], r["truth_band"], r["engine_band"]] for r in ag])


def fig_probe_outcomes(cal):
    ids = ["DM-001", "PIR-001", "UAE-001", "SIL-001", "MI-001", "EA-001", "ETL-001"]
    cats = [("TP", "both flag (TP)"), ("TN", "neither flags (TN)"), ("FP", "engine flags only (FP)"), ("FN", "hand label flags only (FN)"),
            ("engine_unmeasured_truth_flag", "engine not measured, hand label flags"),
            ("engine_unmeasured_truth_pass", "engine not measured, hand label passes")]
    by = {r["metric_id"]: r for r in cal if r["dataset"] == "probes"}
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ys = list(range(len(ids)))[::-1]
    rows = []
    for y, mid in zip(ys, ids):
        left = 0
        for k, (key, _) in enumerate(cats):
            v = int(by[mid][key])
            if v:
                ax.barh(y, v, left=left, color=S[k], edgecolor=SURFACE, linewidth=1.5, height=0.6)
                ax.text(left + v / 2, y, str(v), ha="center", va="center", fontsize=8,
                        color="#0b0b0b" if k == 3 else "#ffffff", fontweight="bold")
            left += v
        rows.append([mid] + [by[mid][c[0]] for c in cats])
    ax.set_yticks(ys)
    ax.set_yticklabels(ids, fontsize=8.5)
    ax.set_xlabel("Probe results")
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    h = [plt.Rectangle((0, 0), 1, 1, color=S[k]) for k in range(len(cats))]
    fig.legend(h, [c[1] for c in cats], loc="lower center", ncol=3, frameon=False, fontsize=8)
    fig.tight_layout(rect=(0, 0.14, 1, 1))
    save(fig, "fig06_probe_outcomes")
    wr("fig06_probe_outcomes.csv", ["metric_id"] + [c[0] for c in cats], rows)


def fig_weight_sensitivity(bw):
    rows = []
    for r in bw:
        if r["kind"] == "weight_changed":
            m = re.search(r"= ([0-9.]+)", r["note"])
            rows.append([r["parameter"], r["change"], float(m.group(1)), r["ranking_of_agents_preserved"], r["runs_changing_band"]])
    ids = ["DM-001", "PIR-001", "UAE-001", "SIL-001", "MI-001", "EA-001", "ETL-001"]
    fig, ax = plt.subplots(figsize=(8, 3.4))
    for k, (chg, col, off) in enumerate((("x0.5", S[0], -0.15), ("x1.5", S[1], 0.15))):
        for r in rows:
            if r[1] == chg:
                y = len(ids) - 1 - ids.index(r[0]) + off
                ax.scatter(r[2], y, s=36, color=col, zorder=3)
                ax.text(r[2] + 0.002, y + 0.0, "%.3f" % r[2], fontsize=7.5, va="center", ha="left", color=INK)
    ax.set_yticks(range(len(ids)))
    ax.set_yticklabels(ids[::-1], fontsize=8.5)
    ax.set_xlim(0.27, 0.36)
    ax.set_xlabel("Mean overall score of the filtered agent minus the unprotected agent")
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    h = [plt.Line2D([], [], marker="o", ls="", color=S[0]), plt.Line2D([], [], marker="o", ls="", color=S[1])]
    ax.legend(h, ["that weight halved", "that weight increased by half"], loc="lower right", frameon=False, fontsize=8)
    fig.tight_layout()
    save(fig, "fig07_weight_sensitivity")
    wr("fig07_weight_sensitivity.csv", ["metric_id", "change", "agent_gap", "ranking_preserved", "runs_changing_band"], rows)


def fig_agents(defs, agents):
    ids = list(defs["metrics"])
    fig, ax = plt.subplots(figsize=(9, 3.6))
    names = [a["agent_config"] for a in agents]
    w = 0.38
    rows = []
    for k, a in enumerate(agents):
        for i, mid in enumerate(ids):
            v = f(a[defs["metrics"][mid]["column"] + "_score_mean"])
            x = i + (k - 0.5) * w
            if v is not None:
                ax.bar(x, v, width=w - 0.04, color=S[k])
                ax.text(x, v + 0.015, "%.2f" % v, ha="center", fontsize=7.5, color=INK)
            rows.append([a["agent_config"], mid, "" if v is None else v])
    ax.set_xticks(range(len(ids)))
    ax.set_xticklabels(ids, fontsize=8.5)
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("Mean metric score")
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.legend([plt.Rectangle((0, 0), 1, 1, color=S[k]) for k in range(len(names))], names, loc="lower right", frameon=False, fontsize=8.5)
    fig.tight_layout()
    save(fig, "fig08_agent_metric_means")
    wr("fig08_agent_metric_means.csv", ["agent_config", "metric_id", "mean_score"], rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(REPORT)))
    a = ap.parse_args()
    R = a.root
    with open(os.path.join(R, "wp3_scoring_engine", "metric_definitions.yaml"), encoding="utf-8") as fh:
        defs = yaml.safe_load(fh)
    runs = rd(os.path.join(R, "wp3_aggregation_scripts", "examples", "scored_runs.csv"))
    cal = rd(os.path.join(R, "wp3_calibration", "results", "calibration_results.csv"))
    ag = rd(os.path.join(R, "wp3_calibration", "results", "overall_agreement.csv"))
    bw = rd(os.path.join(R, "wp3_calibration", "results", "band_and_weight_sensitivity.csv"))
    agents = rd(os.path.join(R, "wp3_aggregation_scripts", "examples", "expected_output", "summary_by_agent.csv"))
    fig_architecture()
    fig_weights(defs)
    fig_distributions(defs, runs)
    fig_precision_recall(cal)
    fig_overall_agreement(ag)
    fig_probe_outcomes(cal)
    fig_weight_sensitivity(bw)
    fig_agents(defs, agents)
    print("Wrote 8 figures (svg + png) and their data to", FIG)


if __name__ == "__main__":
    main()
