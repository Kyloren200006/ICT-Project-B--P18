"""Data layer for the WP3 metrics dashboard.

Reads three kinds of files and nothing else:

  * metric_definitions.yaml   - metrics, weights, thresholds, formulas, bands, linked risks
  * scored_runs.csv / .json   - one row per scored run (written by the WP3 scoring engine)
  * calibration results       - the CSV files written by the calibration and validation package

No scoring logic lives here. The only calculation that touches scores is a *check*:
recompute_metric() recomputes a metric score from the count fields using the formula
in the definitions file, so the dashboard can flag a scored file that disagrees with
the definitions it is displayed against.
"""
from __future__ import annotations

import csv
import json
import math
import os
from dataclasses import dataclass, field

import yaml

EPS = 1e-9
# Display names for WP1's threat IDs (the names are the comments beside risk_ids in the definitions file).
RISK_NAMES = {
    "TC1": "Prompt Injection",
    "TC2": "Sensitive Data Leakage",
    "TC3": "Unsafe Tool Execution",
    "TC4": "Cross-session Memory Exposure",
    "TC5": "Model/Data Poisoning",
    "TC6": "Excessive Agency",
}
N_BINS = 20            # histogram bins of width 0.05 over [0, 1), plus one bin for exactly 1.0
CAL_FILES = {
    "results": "calibration_results.csv",
    "thresholds": "threshold_sensitivity.csv",
    "bands": "band_and_weight_sensitivity.csv",
    "probes": "probe_findings.csv",
    "agreement": "overall_agreement.csv",
    "platform": "platform_case_check.csv",
    "mismatches": "count_mismatches.csv",
    "run_record": "run_record.json",
}


# ----------------------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------------------
def to_float(value):
    """'' / None / 'nan' -> None; otherwise float."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        f = float(value)
        return None if math.isnan(f) else f
    s = str(value).strip()
    if s == "" or s.lower() in ("nan", "none", "null", "n/a", "na"):
        return None
    try:
        f = float(s)
    except ValueError:
        return None
    return None if math.isnan(f) else f


def mean(values):
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def median(values):
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    mid = len(vals) // 2
    return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2


def stdev(values):
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return None
    m = sum(vals) / len(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))


def split_ids(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [p.strip() for p in str(value).replace(",", ";").split(";") if p.strip()]


# ----------------------------------------------------------------------------------------
# definitions
# ----------------------------------------------------------------------------------------
@dataclass
class Metric:
    id: str
    name: str
    column: str
    description: str
    formula: str
    weight: float
    threshold: float
    threshold_rule: str
    kind: str
    numerator: list
    denominator: str
    inputs: dict
    edge_cases: list
    risk_ids: list
    risk_mapping_note: str
    run_log_sources: list
    references: list
    wp1_risk_category: str

    @property
    def count_fields(self):
        return list(self.numerator) + [self.denominator]


@dataclass
class Definitions:
    path: str
    version: str
    status: str
    metrics: list
    bands: list                # [{name, min, max}] highest first
    no_data_behaviour: str
    overall_formula: str
    band_status: str
    change_control: list
    decimals: int = 6

    def metric(self, metric_id):
        for m in self.metrics:
            if m.id == metric_id:
                return m
        return None

    @property
    def ids(self):
        return [m.id for m in self.metrics]

    def band_for(self, score):
        """Band name for an overall score (lower bound of each band decides, as the engine does)."""
        if score is None:
            return "Not scored"
        for b in sorted(self.bands, key=lambda b: -b["min"]):
            if score >= b["min"] - EPS:
                return b["name"]
        return self.bands[-1]["name"] if self.bands else "Not scored"

    @property
    def band_names(self):
        return [b["name"] for b in sorted(self.bands, key=lambda b: -b["min"])]


def load_definitions(path):
    with open(path, "r", encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    weights = (doc.get("overall_score") or {}).get("weights") or {}
    metrics = []
    for mid, m in (doc.get("metrics") or {}).items():
        sc = m.get("scoring") or {}
        metrics.append(Metric(
            id=mid,
            name=m.get("name", mid),
            column=m.get("column", mid.replace("-", "_")),
            description=m.get("description", ""),
            formula=m.get("formula", ""),
            weight=float(weights.get(mid, 0.0)),
            threshold=float(m.get("threshold", 0.0)),
            threshold_rule=m.get("threshold_rule", ""),
            kind=sc.get("kind", ""),
            numerator=list(sc.get("numerator") or []),
            denominator=sc.get("denominator", ""),
            inputs=dict(m.get("inputs") or {}),
            edge_cases=list(m.get("edge_cases") or []),
            risk_ids=split_ids(m.get("risk_ids")),
            risk_mapping_note=m.get("risk_mapping_note", ""),
            run_log_sources=list(m.get("run_log_sources") or []),
            references=list(m.get("references") or []),
            wp1_risk_category=m.get("wp1_risk_category", ""),
        ))
    # display order: the order in the file, which is the order the engine and the report use
    info = doc.get("schema_info") or {}
    bands = [{"name": b["name"], "min": float(b["min"]), "max": float(b["max"])}
             for b in (doc.get("risk_bands") or [])]
    return Definitions(
        path=path,
        version=str(info.get("version", "")),
        status=str(info.get("status", "")),
        metrics=metrics,
        bands=bands,
        no_data_behaviour=str((doc.get("settings") or {}).get("no_data_behaviour",
                                                               info.get("no_data_behaviour", ""))),
        overall_formula=str((doc.get("overall_score") or {}).get("formula", "")),
        band_status=str(doc.get("band_status", "")),
        change_control=list(doc.get("change_control") or []),
        decimals=int((doc.get("settings") or {}).get("decimals", 6)),
    )


def recompute_metric(metric, counts):
    """Recompute a metric score from count fields using the definitions file.
    Returns None when the metric is not measured (denominator 0 or a count is missing)."""
    den = counts.get(metric.denominator)
    if den is None or den <= 0:
        return None
    nums = [counts.get(f) for f in metric.numerator]
    if any(n is None for n in nums):
        return None
    total = sum(nums)
    if metric.kind == "complement":
        score = 1.0 - total / den
    elif metric.kind == "ratio":
        score = total / den
    else:
        return None
    return min(1.0, max(0.0, score))


def recompute_overall(defs, scores):
    """Weighted mean over the measured metrics, weights rescaled. None if nothing measured."""
    num = den = 0.0
    for m in defs.metrics:
        s = scores.get(m.id)
        if s is not None:
            num += m.weight * s
            den += m.weight
    return num / den if den > 0 else None


# ----------------------------------------------------------------------------------------
# scored runs
# ----------------------------------------------------------------------------------------
@dataclass
class Run:
    run_id: str
    scenario_id: str
    repeat_index: str
    agent: str
    model: str
    mitigation: str
    status: str
    workflow: str
    scenario_type: str
    risk_ids: list
    scores: dict               # metric id -> float | None
    counts: dict               # count field -> float | None
    overall: object            # float | None
    level: str
    raw: dict = field(default_factory=dict)


def _first(row, *keys, default=""):
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return row[k]
    return default


def _row_to_run(row, defs):
    scores = {}
    for m in defs.metrics:
        scores[m.id] = to_float(_first(row, m.column + "_score", m.column, m.id, default=None))
    count_fields = []
    for m in defs.metrics:
        for f in m.count_fields:
            if f not in count_fields:
                count_fields.append(f)
    counts = {f: to_float(row.get(f)) for f in count_fields}
    overall = to_float(_first(row, "overall_trust_score", "overall_trust", "overall", default=None))
    level = str(_first(row, "trust_level", default="")).strip()
    if not level:
        level = defs.band_for(overall)
    return Run(
        run_id=str(_first(row, "run_id")),
        scenario_id=str(_first(row, "scenario_id")),
        repeat_index=str(_first(row, "repeat_index")),
        agent=str(_first(row, "agent_config", "agent", default="(unknown)")),
        model=str(_first(row, "model")),
        mitigation=str(_first(row, "mitigation")),
        status=str(_first(row, "status", default="completed")),
        workflow=str(_first(row, "workflow", default="(unknown)")),
        scenario_type=str(_first(row, "scenario_type", default="(unknown)")),
        risk_ids=split_ids(row.get("risk_ids")),
        scores=scores,
        counts=counts,
        overall=overall,
        level=level,
        raw=dict(row),
    )


def load_scored(path, defs):
    """Load scored_runs.csv or scored_runs.json. Returns (runs, warnings)."""
    ext = os.path.splitext(path)[1].lower()
    warnings = []
    if ext == ".json":
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
        if isinstance(doc, dict):
            doc = doc.get("runs") or doc.get("scored_runs") or []
        rows = [r for r in doc if isinstance(r, dict)]
    else:
        with open(path, "r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
    if not rows:
        warnings.append("The scored file has no rows.")
    runs = [_row_to_run(r, defs) for r in rows]
    if rows:
        first = rows[0]
        found = [m.id for m in defs.metrics
                 if any(k in first for k in (m.column + "_score", m.column, m.id))]
        missing = [m.id for m in defs.metrics if m.id not in found]
        if missing:
            warnings.append("No score column found for: " + ", ".join(missing)
                            + ". Those metrics are shown as not measured.")
    return runs, warnings


def check_runs(runs, defs, tol=2e-6):
    """Data checks on the scored file. Returns a dict of counts and examples."""
    n_unlabelled = n_score_checked = n_score_bad = n_overall_checked = n_overall_bad = 0
    examples = []
    for r in runs:
        have_counts = any(v is not None for v in r.counts.values())
        for m in defs.metrics:
            if not have_counts:
                continue
            n_score_checked += 1
            exp = recompute_metric(m, r.counts)
            got = r.scores.get(m.id)
            if got is None and exp is not None and r.raw.get("label_source") == "heuristic":
                # The engine leaves metrics that need scenario labels blank when the scenario has
                # no label (label_source = heuristic). That is a designed rule, not a mismatch.
                n_unlabelled += 1
                continue
            ok = (exp is None and got is None) or (
                exp is not None and got is not None and abs(exp - got) <= tol)
            if not ok:
                n_score_bad += 1
                if len(examples) < 5:
                    examples.append("%s %s: file %s, recomputed %s" % (
                        r.run_id, m.id, "blank" if got is None else "%.6f" % got,
                        "blank" if exp is None else "%.6f" % exp))
        exp_o = recompute_overall(defs, r.scores)
        if r.overall is not None or exp_o is not None:
            n_overall_checked += 1
            if (r.overall is None) != (exp_o is None) or (
                    r.overall is not None and abs(r.overall - exp_o) > tol):
                n_overall_bad += 1
                if len(examples) < 5:
                    examples.append("%s overall: file %s, recomputed %s" % (
                        r.run_id, r.overall, exp_o))
    return {
        "score_cells_checked": n_score_checked, "score_cells_mismatch": n_score_bad,
        "score_cells_unlabelled": n_unlabelled,
        "overall_checked": n_overall_checked, "overall_mismatch": n_overall_bad,
        "examples": examples,
        "counts_present": any(any(v is not None for v in r.counts.values()) for r in runs),
    }


# ----------------------------------------------------------------------------------------
# filters and statistics
# ----------------------------------------------------------------------------------------
@dataclass
class Filters:
    agent: str = ""
    workflow: str = ""
    scenario_type: str = ""

    def active(self):
        return {k: v for k, v in (("agent", self.agent), ("workflow", self.workflow),
                                  ("type", self.scenario_type)) if v}


def filter_options(runs):
    return {
        "agent": sorted({r.agent for r in runs}),
        "workflow": sorted({r.workflow for r in runs}),
        "type": sorted({r.scenario_type for r in runs}),
    }


def parse_filters(query, runs):
    """query is a dict of lists (urllib.parse.parse_qs). Unknown values are ignored."""
    opts = filter_options(runs)

    def pick(key, name):
        v = (query.get(key) or [""])[0]
        return v if v in opts[name] else ""
    return Filters(agent=pick("agent", "agent"), workflow=pick("workflow", "workflow"),
                   scenario_type=pick("type", "type"))


def apply_filters(runs, f):
    out = []
    for r in runs:
        if f.agent and r.agent != f.agent:
            continue
        if f.workflow and r.workflow != f.workflow:
            continue
        if f.scenario_type and r.scenario_type != f.scenario_type:
            continue
        out.append(r)
    return out


def passes(metric, score):
    return score is not None and score >= metric.threshold - EPS


def bin_index(score):
    if score >= 1.0 - EPS:
        return N_BINS
    return min(N_BINS - 1, max(0, int(score * N_BINS + EPS)))


def bin_label(i):
    if i == N_BINS:
        return "1.00"
    return "%.2f-%.2f" % (i / N_BINS, (i + 1) / N_BINS)


def histogram(scores):
    bins = [0] * (N_BINS + 1)
    for s in scores:
        if s is not None:
            bins[bin_index(s)] += 1
    return bins


def bin_passes(metric, i):
    return (i / N_BINS) >= metric.threshold - EPS


@dataclass
class MetricStats:
    metric: Metric
    n_runs: int
    n_measured: int
    n_not_measured: int
    mean: object
    median: object
    minimum: object
    maximum: object
    n_pass: int
    pass_rate: object
    bins: list


def metric_stats(metric, runs):
    scores = [r.scores.get(metric.id) for r in runs]
    measured = [s for s in scores if s is not None]
    n_pass = sum(1 for s in measured if passes(metric, s))
    return MetricStats(
        metric=metric, n_runs=len(runs), n_measured=len(measured),
        n_not_measured=len(runs) - len(measured),
        mean=mean(measured), median=median(measured),
        minimum=min(measured) if measured else None,
        maximum=max(measured) if measured else None,
        n_pass=n_pass, pass_rate=(n_pass / len(measured)) if measured else None,
        bins=histogram(measured))


def level_counts(runs, defs):
    names = list(defs.band_names)
    counts = {n: 0 for n in names}
    for r in runs:
        counts[r.level] = counts.get(r.level, 0) + 1
    order = names + [n for n in counts if n not in names]
    return [(n, counts[n]) for n in order if n in names or counts[n] > 0]


def agent_summary(runs, defs):
    out = []
    for agent in sorted({r.agent for r in runs}):
        rs = [r for r in runs if r.agent == agent]
        overall = [r.overall for r in rs]
        m = mean(overall)
        out.append({
            "agent": agent, "n": len(rs),
            "n_scored": sum(1 for o in overall if o is not None),
            "mean": m, "std": stdev(overall),
            "min": min([o for o in overall if o is not None], default=None),
            "level": defs.band_for(m),
            "metric_means": {mm.id: mean([r.scores.get(mm.id) for r in rs]) for mm in defs.metrics},
            "metric_counts": {mm.id: sum(1 for r in rs if r.scores.get(mm.id) is not None)
                              for mm in defs.metrics},
        })
    return out


def group_means(runs, key):
    groups = {}
    for r in runs:
        groups.setdefault(getattr(r, key), []).append(r.overall)
    return [(k, mean(v), sum(1 for x in v if x is not None)) for k, v in sorted(groups.items())]


def scenario_rows(metric, runs):
    """Per-scenario breakdown of one metric, with the summed counts behind the score."""
    groups = {}
    for r in runs:
        groups.setdefault(r.scenario_id, []).append(r)
    rows = []
    for sid, rs in sorted(groups.items()):
        scores = [r.scores.get(metric.id) for r in rs]
        meas = [s for s in scores if s is not None]
        num = [sum((r.counts.get(f) or 0) for r in rs) for f in metric.numerator]
        den = sum((r.counts.get(metric.denominator) or 0) for r in rs)
        rows.append({
            "scenario": sid, "workflow": rs[0].workflow, "type": rs[0].scenario_type,
            "runs": len(rs), "measured": len(meas), "mean": mean(meas),
            "numerator": sum(num), "denominator": den,
            "pass": sum(1 for s in meas if passes(metric, s)),
        })
    return rows


# ----------------------------------------------------------------------------------------
# calibration results
# ----------------------------------------------------------------------------------------
def _read_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def load_calibration(directory):
    """Read whichever calibration files exist in `directory`. Missing files are simply absent."""
    cal = {"dir": directory, "found": [], "missing": []}
    for key, name in CAL_FILES.items():
        p = os.path.join(directory, name)
        if not os.path.isfile(p):
            cal[key] = None
            cal["missing"].append(name)
            continue
        cal["found"].append(name)
        if name.endswith(".json"):
            with open(p, "r", encoding="utf-8") as fh:
                cal[key] = json.load(fh)
        else:
            cal[key] = _read_csv(p)
    return cal


def cal_summary(cal):
    """Headline numbers from the calibration files (None when a file is missing)."""
    out = {}
    res = cal.get("results")
    if res:
        for ds in ("pack", "probes"):
            rows = [r for r in res if r.get("dataset") == ds]
            if not rows:
                continue
            t = {k: sum(int(to_float(r.get(k)) or 0) for r in rows)
                 for k in ("TP", "FP", "FN", "TN", "engine_unmeasured_truth_flag",
                           "engine_unmeasured_truth_pass", "engine_extra")}
            t["cells"] = t["TP"] + t["FP"] + t["FN"] + t["TN"]
            t["agree"] = t["TP"] + t["TN"]
            out[ds] = t
    ag = cal.get("agreement")
    if ag:
        out["agreement"] = {
            "runs": len(ag),
            "band_agree": sum(1 for r in ag if r.get("band_agrees") == "yes"),
            "max_abs_diff": max((to_float(r.get("abs_difference")) or 0.0) for r in ag),
        }
    pr = cal.get("probes")
    if pr:
        out["probes_table"] = {
            "n": len(pr),
            "counts_match": sum(1 for r in pr if r.get("counts_match_truth") == "yes"),
            "decision_same": sum(1 for r in pr if r.get("trust_decision") == "same"),
        }
    return out


# ----------------------------------------------------------------------------------------
# context
# ----------------------------------------------------------------------------------------
@dataclass
class Context:
    defs: Definitions
    runs: list
    scored_path: str
    calibration: dict
    warnings: list
    checks: dict
    label: str = ""

    @property
    def completed(self):
        return [r for r in self.runs if r.status == "completed"]

    @property
    def excluded(self):
        return [r for r in self.runs if r.status != "completed"]


def build_context(defs_path, scored_path, cal_dir, label=""):
    defs = load_definitions(defs_path)
    runs, warnings = load_scored(scored_path, defs)
    cal = load_calibration(cal_dir) if cal_dir and os.path.isdir(cal_dir) else {
        "dir": cal_dir, "found": [], "missing": list(CAL_FILES.values()),
        **{k: None for k in CAL_FILES}}
    ctx = Context(defs=defs, runs=runs, scored_path=scored_path, calibration=cal,
                  warnings=warnings, checks={}, label=label)
    ctx.runs = ctx.completed            # the dashboard shows scored (completed) runs only
    ctx.checks = check_runs(ctx.runs, defs)
    ctx.checks["excluded"] = len(runs) - len(ctx.runs)
    ctx.checks["total_rows"] = len(runs)
    return ctx
