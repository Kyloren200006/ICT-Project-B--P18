#!/usr/bin/env python3
"""Agreement statistics for the report's validation section.

Reads wp3_calibration/results/calibration_results.csv and writes figures/data/agreement_stats.csv with, per
dataset and metric (and a total row per dataset): cells compared, accuracy, precision, recall, F1 and Cohen's kappa.

Only cells where BOTH the engine and the hand-labelled ground truth measured the metric are used (TP+FP+FN+TN).
Cells where the engine did not measure, or measured something the truth says has nothing to measure, are reported
as separate columns and are not folded into the accuracy.

What this is and is not: the two "raters" are the engine and the hand-made labels on synthetic logs. Kappa here
measures engine-versus-labels agreement on the pass/fail decision. It is not an estimate of accuracy on real agent logs.

Run:  py scripts/agreement_stats.py [--root DIR]
"""
import argparse
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.dirname(HERE)
OUT = os.path.join(REPORT, "figures", "data", "agreement_stats.csv")


def safe_div(a, b):
    return a / b if b else None


def kappa(tp, fp, fn, tn):
    """Cohen's kappa for a 2x2 table; None when undefined (chance agreement is 1, or no cells)."""
    n = tp + fp + fn + tn
    if n == 0:
        return None
    po = (tp + tn) / n
    p_engine_flag = (tp + fp) / n
    p_truth_flag = (tp + fn) / n
    pe = p_engine_flag * p_truth_flag + (1 - p_engine_flag) * (1 - p_truth_flag)
    if abs(1 - pe) < 1e-12:
        return None
    return (po - pe) / (1 - pe)


def fmt(x, nd=3):
    return "" if x is None else ("%.*f" % (nd, x))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=os.path.abspath(os.path.join(REPORT, "..", "..")),
                    help="folder that contains wp3_calibration/ (default: two levels above reports/wp3)")
    args = ap.parse_args(argv)
    src = os.path.join(args.root, "wp3_calibration", "results", "calibration_results.csv")
    with open(src, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    out = []
    totals = {}
    for r in rows:
        tp, fp, fn, tn = (int(r[k]) for k in ("TP", "FP", "FN", "TN"))
        un_flag = int(r["engine_unmeasured_truth_flag"])
        un_pass = int(r["engine_unmeasured_truth_pass"])
        extra = int(r["engine_extra"])
        n = tp + fp + fn + tn
        acc = safe_div(tp + tn, n)
        prec = safe_div(tp, tp + fp)
        rec = safe_div(tp, tp + fn + un_flag)
        f1 = safe_div(2 * tp, 2 * tp + fp + fn + un_flag)
        out.append([r["dataset"], r["metric_id"], n, tp, fp, fn, tn, un_flag, un_pass, extra,
                    fmt(acc), fmt(prec), fmt(rec), fmt(f1), fmt(kappa(tp, fp, fn, tn))])
        t = totals.setdefault(r["dataset"], [0] * 8)
        for i, v in enumerate((tp, fp, fn, tn, un_flag, un_pass, extra)):
            t[i] += v
    final = []
    for ds in ("pack", "probes", "pack+probes"):
        for row in out:
            if row[0] == ds:
                final.append(row)
        t = totals[ds]
        tp, fp, fn, tn, un_flag, un_pass, extra = t[:7]
        n = tp + fp + fn + tn
        final.append([ds, "ALL", n, tp, fp, fn, tn, un_flag, un_pass, extra,
                      fmt(safe_div(tp + tn, n)), fmt(safe_div(tp, tp + fp)),
                      fmt(safe_div(tp, tp + fn + un_flag)), fmt(safe_div(2 * tp, 2 * tp + fp + fn + un_flag)),
                      fmt(kappa(tp, fp, fn, tn))])

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["dataset", "metric_id", "cells_both_measured", "TP", "FP", "FN", "TN",
                    "engine_unmeasured_truth_flag", "engine_unmeasured_truth_pass", "engine_extra",
                    "accuracy", "precision", "recall", "f1", "cohen_kappa"])
        w.writerows(final)
    print("wrote", OUT, "(%d rows)" % len(final))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
