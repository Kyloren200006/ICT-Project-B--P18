#!/usr/bin/env python3
"""WP3 aggregation and summary script (v1.0.0).

Reads the per-run scores written by the WP3 scoring engine (scored_runs.csv or scored_runs.json) and writes
summaries per agent, per workflow, per risk and per scenario, as CSV and JSON:

    summary_by_agent.csv      one row per agent configuration (agent_config + model + mitigation)
    summary_by_workflow.csv   one row per agent and workflow (email, web research, file handling, scheduling)
    summary_by_risk.csv       one row per agent and WP1 threat ID (TC1 to TC6)
    summary_by_scenario.csv   one row per agent and scenario
    summary_all.json          everything above in one file, plus metadata

Usage:

    python aggregate_summaries.py scored_runs.csv --scenarios scenario_lookup.csv --out results

With no arguments it reads input/scored_runs.csv (and input/scenario_lookup.csv if present) and writes to output/.

Weights, thresholds, risk bands and the linked WP1 threat IDs come from metric_definitions.yaml, the same file
the scoring engine reads. The script only reads scores that already exist; it never re-scores a run.
The output is deterministic: the same input gives byte-identical files (no timestamps, fixed ordering).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import pathlib
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("error: PyYAML is not installed. Run:  py -m pip install -r requirements.txt\n")
    raise SystemExit(1)

__version__ = "1.0.0"

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_METRICS = HERE / "metric_definitions.yaml"
DEFAULT_SCORED = HERE / "input" / "scored_runs.csv"
DEFAULT_LOOKUP = HERE / "input" / "scenario_lookup.csv"
DEFAULT_OUT = HERE / "output"

UNLABELLED = "(unlabelled)"
NOT_MEASURED = "Not measured"

# Header names accepted in the scenario lookup (matched case-insensitively, spaces and '-' read as '_').
LOOKUP_ALIASES = {
    "scenario_id": ["scenario_id", "scenario", "task_id", "id", "scenario_ids"],
    "workflow": ["workflow", "domain", "workflow_type"],
    "type": ["type", "scenario_type", "benign_adversarial", "behaviour", "behavior"],
    "risk_ids": ["risk_ids", "linked_risk_ids", "linked_risks", "risks", "risk"],
}


class AggregateError(ValueError):
    """A problem with an input file that the user can fix; shown as 'error: ...'."""


# ---------------------------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class MetricInfo:
    id: str                      # "PIR-001"
    name: str
    column: str                  # "PIR_001"  -> score column "PIR_001_score"
    risk_ids: Tuple[str, ...]    # WP1 threat IDs linked to this metric

    @property
    def score_column(self) -> str:
        return f"{self.column}_score"


@dataclass
class Definitions:
    metrics: List[MetricInfo]
    bands: List[Tuple[str, float]]       # (name, minimum score), highest first
    decimals: int
    version: str
    source: str

    def risks(self) -> List[str]:
        out: List[str] = []
        for m in self.metrics:
            for r in m.risk_ids:
                if r not in out:
                    out.append(r)
        return out


def load_definitions(path) -> Definitions:
    path = pathlib.Path(path)
    try:
        with open(path, encoding="utf-8") as fh:
            doc = yaml.safe_load(fh) or {}
    except FileNotFoundError:
        raise AggregateError(f"metric definitions not found: {path}")
    except yaml.YAMLError as exc:
        raise AggregateError(f"cannot read {path}: {exc}")
    metrics_doc = doc.get("metrics") or {}
    if not metrics_doc:
        raise AggregateError(f"{path} has no 'metrics' section")
    metrics = [
        MetricInfo(
            id=str(mid),
            name=str(m.get("name", mid)),
            column=str(m.get("column") or str(mid).replace("-", "_")),
            risk_ids=tuple(str(r) for r in (m.get("risk_ids") or ())),
        )
        for mid, m in metrics_doc.items()
    ]
    bands = sorted(
        ((str(b["name"]), float(b["min"])) for b in (doc.get("risk_bands") or [])),
        key=lambda b: -b[1],
    )
    if not bands:
        raise AggregateError(f"{path} has no 'risk_bands'")
    settings = doc.get("settings") or {}
    return Definitions(
        metrics=metrics,
        bands=bands,
        decimals=int(settings.get("decimals", 6)),
        version=str((doc.get("schema_info") or {}).get("version", "")),
        source=path.name,
    )


def band_for(defs: Definitions, score: Optional[float]) -> str:
    if score is None:
        return NOT_MEASURED
    score = round(score, 10)   # exactly 0.5 must not drop a band through float noise (0.49999999999999994)
    for name, minimum in defs.bands:
        if score >= minimum:
            return name
    return defs.bands[-1][0]


# ---------------------------------------------------------------------------------------------
# Reading scored runs
# ---------------------------------------------------------------------------------------------
def _number(value, where: str) -> Optional[float]:
    """A score cell: blank or null means 'not measured'."""
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise AggregateError(f"{where}: {value!r} is not a number")
    if math.isnan(number):
        return None
    return number


def read_scored(path, defs: Definitions) -> Tuple[List[dict], int]:
    """Read scored_runs.csv / scored_runs.json. Returns (rows, number of rows skipped as not completed)."""
    path = pathlib.Path(path)
    if path.is_dir():
        for name in ("scored_runs.csv", "scored_runs.json"):
            if (path / name).is_file():
                path = path / name
                break
        else:
            raise AggregateError(f"no scored_runs.csv or scored_runs.json in {path}")
    if not path.is_file():
        raise AggregateError(f"scored runs file not found: {path}")

    try:
        if path.suffix.lower() == ".json":
            with open(path, encoding="utf-8-sig") as fh:
                doc = json.load(fh)
            raw = doc.get("runs") if isinstance(doc, dict) else doc
            if not isinstance(raw, list) or not all(isinstance(r, dict) for r in raw):
                raise AggregateError(f"{path.name}: expected a list of run objects (or {{\"runs\": [...]}})")
        else:
            with open(path, newline="", encoding="utf-8-sig") as fh:
                raw = list(csv.DictReader(fh))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AggregateError(f"cannot read {path}: {exc}")

    if not raw:
        raise AggregateError(f"{path.name} contains no runs")
    present = set(raw[0].keys())
    missing = [c for c in ("scenario_id", "agent_config", "overall_trust_score") if c not in present]
    if missing:
        raise AggregateError(
            f"{path.name} does not look like scoring-engine output; missing column(s): {', '.join(missing)}"
        )

    score_cols = [m.score_column for m in defs.metrics]
    rows: List[dict] = []
    skipped = 0
    for i, r in enumerate(raw, start=1):
        status = str(r.get("status") or "completed").strip().lower()
        if status != "completed":
            skipped += 1
            continue
        label = r.get("run_id") or f"row {i}"
        row = dict(r)
        row["overall_trust_score"] = _number(r.get("overall_trust_score"), f"{label}, overall_trust_score")
        for col in score_cols:
            row[col] = _number(r.get(col), f"{label}, {col}")
        rows.append(row)
    if not rows:
        raise AggregateError(f"{path.name}: every run has a status other than 'completed'; nothing to summarise")
    return rows, skipped


# ---------------------------------------------------------------------------------------------
# Scenario lookup (optional)
# ---------------------------------------------------------------------------------------------
def _norm(h: str) -> str:
    return str(h).strip().lower().replace(" ", "_").replace("-", "_")


def split_risks(value) -> List[str]:
    if value is None:
        return []
    parts = str(value).replace("|", ";").replace(",", ";").split(";")
    out: List[str] = []
    for p in parts:
        p = p.strip()
        if p and p not in out:
            out.append(p)
    return out


def load_lookup(path, column_map: Optional[Dict[str, str]] = None) -> Dict[str, dict]:
    path = pathlib.Path(path)
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            headers = list(reader.fieldnames or [])
            rows = list(reader)
    except (OSError, UnicodeDecodeError) as exc:
        raise AggregateError(f"cannot read scenario lookup {path}: {exc}")

    normed = {_norm(h): h for h in headers}
    cols: Dict[str, str] = {}
    for canonical, names in LOOKUP_ALIASES.items():
        if column_map and canonical in column_map:
            want = column_map[canonical]
            if want in headers:
                cols[canonical] = want
            elif _norm(want) in normed:
                cols[canonical] = normed[_norm(want)]
            else:
                raise AggregateError(f"--map {canonical}={want}: no such column in {path.name}")
            continue
        for n in names:
            if n in normed:
                cols[canonical] = normed[n]
                break
    if "scenario_id" not in cols:
        raise AggregateError(
            f"{path.name} needs a scenario ID column (scenario_id, task_id or id); use --map scenario_id=<header>"
        )

    lookup: Dict[str, dict] = {}
    for r in rows:
        sid = (r.get(cols["scenario_id"]) or "").strip()
        if not sid:
            continue
        if sid in lookup:
            raise AggregateError(f"{path.name}: scenario_id {sid!r} appears more than once")
        lookup[sid] = {
            "workflow": (r.get(cols["workflow"]) or "").strip() if "workflow" in cols else "",
            "type": (r.get(cols["type"]) or "").strip() if "type" in cols else "",
            "risks": split_risks(r.get(cols["risk_ids"])) if "risk_ids" in cols else [],
        }
    return lookup


def enrich(rows: List[dict], lookup: Optional[Dict[str, dict]]) -> Tuple[List[dict], List[str]]:
    """Give every row its workflow, scenario type and risk list.

    The lookup wins where it has a value; otherwise the columns already on the scored row are used.
    Returns (rows, scenario IDs that were not found in the lookup).
    """
    out: List[dict] = []
    not_found: List[str] = []
    for r in rows:
        r = dict(r)
        sid = str(r.get("scenario_id") or "").strip()
        lab = lookup.get(sid) if lookup is not None else None
        if lookup is not None and lab is None and sid and sid not in not_found:
            not_found.append(sid)
        workflow = (lab or {}).get("workflow") or str(r.get("workflow") or "").strip()
        stype = (lab or {}).get("type") or str(r.get("scenario_type") or "").strip()
        risks = (lab or {}).get("risks") or split_risks(r.get("risk_ids"))
        r["workflow"] = workflow or UNLABELLED
        r["scenario_type"] = stype
        r["_risks"] = list(risks)
        out.append(r)
    return out, sorted(not_found)


# ---------------------------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------------------------
def _mean(vals: Sequence[float]) -> Optional[float]:
    return sum(vals) / len(vals) if vals else None


def _std(vals: Sequence[float]) -> Optional[float]:
    """Sample standard deviation (n - 1). Blank for fewer than two values."""
    if len(vals) < 2:
        return None
    m = sum(vals) / len(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))


def _r(value: Optional[float], decimals: int) -> Optional[float]:
    return None if value is None else round(value, decimals)


def _stats(defs: Definitions, rows: List[dict], keys: dict) -> dict:
    overall = [r["overall_trust_score"] for r in rows if r["overall_trust_score"] is not None]
    mean = _mean(overall)
    rec = dict(keys)
    rec.update({
        "n_runs": len(rows),
        "n_runs_with_score": len(overall),
        "mean_overall": _r(mean, defs.decimals),
        "std_overall": _r(_std(overall), defs.decimals),
        "min_overall": _r(min(overall), defs.decimals) if overall else None,
        "trust_level": band_for(defs, mean),
    })
    for m in defs.metrics:
        vals = [r[m.score_column] for r in rows if r.get(m.score_column) is not None]
        rec[m.score_column + "_mean"] = _r(_mean(vals), defs.decimals)
        rec[m.column + "_n_no_data"] = len(rows) - len(vals)
    return rec


def _group(rows: List[dict], key_fn) -> Dict[tuple, List[dict]]:
    groups: Dict[tuple, List[dict]] = {}
    for r in rows:
        groups.setdefault(key_fn(r), []).append(r)
    return dict(sorted(groups.items(), key=lambda kv: tuple(str(x) for x in kv[0])))


def _agent(r: dict) -> str:
    return str(r.get("agent_config") or "unknown")


def aggregate(defs: Definitions, rows: List[dict], skipped_not_completed: int = 0,
              scenarios_not_in_lookup: Optional[List[str]] = None, lookup_used: bool = False,
              source_name: str = "") -> dict:
    """rows must already be enriched (see enrich)."""
    d = defs.decimals

    by_agent = [
        _stats(defs, rs, {"agent_config": k[0], "model": k[1], "mitigation": k[2]})
        for k, rs in _group(rows, lambda r: (_agent(r), str(r.get("model") or ""), str(r.get("mitigation") or ""))).items()
    ]
    by_workflow = [
        _stats(defs, rs, {"agent_config": k[0], "workflow": k[1]})
        for k, rs in _group(rows, lambda r: (_agent(r), r["workflow"])).items()
    ]
    by_scenario = [
        _stats(defs, rs, {"agent_config": k[0], "scenario_id": k[1], "workflow": rs[0]["workflow"],
                          "scenario_type": rs[0]["scenario_type"], "risk_ids": ";".join(rs[0]["_risks"])})
        for k, rs in _group(rows, lambda r: (_agent(r), str(r.get("scenario_id") or ""))).items()
    ]

    # Per risk: a run counts toward a risk when its scenario is tagged with that risk. If no scenario carries
    # any risk tag, every run counts toward every risk, and the 'basis' column says so.
    tagged = any(r["_risks"] for r in rows)
    risk_rows: Dict[Tuple[str, str], List[dict]] = {}
    untagged = 0
    for r in rows:
        if tagged:
            if not r["_risks"]:
                untagged += 1
            risks = r["_risks"]
        else:
            risks = defs.risks()
        for risk in risks:
            risk_rows.setdefault((_agent(r), risk), []).append(r)

    by_risk = []
    for (agent, risk), rs in sorted(risk_rows.items()):
        linked = [m for m in defs.metrics if risk.casefold() in [x.casefold() for x in m.risk_ids]]
        per_run = []
        for r in rs:
            vals = [r[m.score_column] for m in linked if r.get(m.score_column) is not None]
            if vals:
                per_run.append(sum(vals) / len(vals))
        mean = _mean(per_run)
        by_risk.append({
            "agent_config": agent,
            "risk": risk,
            "linked_metrics": ";".join(m.id for m in linked) or "(none)",
            "basis": "scenario_tags" if tagged else "all_runs",
            "n_runs": len(rs),
            "n_runs_measured": len(per_run),
            "mean_risk_score": _r(mean, d),
            "std_risk_score": _r(_std(per_run), d),
            "trust_level": band_for(defs, mean),
        })

    all_overall = [r["overall_trust_score"] for r in rows if r["overall_trust_score"] is not None]
    overall_mean = _mean(all_overall)
    return {
        "metadata": {
            "tool": "aggregate_summaries.py",
            "version": __version__,
            "metric_definitions": defs.source,
            "metric_definitions_version": defs.version,
            "scored_runs_file": source_name,
            "runs_summarised": len(rows),
            "runs_skipped_not_completed": skipped_not_completed,
            "agents": sorted({_agent(r) for r in rows}),
            "mean_overall_all_runs": _r(overall_mean, d),
            "trust_level_all_runs": band_for(defs, overall_mean),
            "scenario_lookup_used": lookup_used,
            "scenarios_not_in_lookup": scenarios_not_in_lookup or [],
            "per_risk_basis": "scenario_tags" if tagged else "all_runs (no scenario carries risk IDs)",
            "runs_without_risk_tag": untagged,
            "risk_bands": [{"name": n, "min": m} for n, m in defs.bands],
        },
        "by_agent": by_agent,
        "by_workflow": by_workflow,
        "by_risk": by_risk,
        "by_scenario": by_scenario,
    }


# ---------------------------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------------------------
def write_outputs(out_dir, agg: dict) -> Dict[str, str]:
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, str] = {}
    for name in ("by_agent", "by_workflow", "by_risk", "by_scenario"):
        rows = agg[name]
        cols: List[str] = []
        for r in rows:
            for k in r:
                if k not in cols:
                    cols.append(k)
        p = out / f"summary_{name}.csv"
        with open(p, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
            w.writeheader()
            for r in rows:
                w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in cols})
        paths[name] = str(p)
    p = out / "summary_all.json"
    with open(p, "w", newline="\n", encoding="utf-8") as fh:
        fh.write(json.dumps(agg, indent=2, ensure_ascii=False) + "\n")
    paths["all"] = str(p)
    return paths


def count_excluded(scored_path) -> Optional[int]:
    """Runs the engine left out of scored_runs (failed, timed out, unreadable), from run_inventory.csv beside it."""
    p = pathlib.Path(scored_path)
    if p.is_dir():
        inv = p / "run_inventory.csv"
    else:
        inv = p.parent / "run_inventory.csv"
    if not inv.is_file():
        return None
    try:
        with open(inv, newline="", encoding="utf-8-sig") as fh:
            return sum(1 for r in csv.DictReader(fh) if (r.get("status") or "").strip().lower() != "scored")
    except (OSError, UnicodeDecodeError):
        return None


def _parse_map(pairs: Optional[List[str]]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for p in pairs or []:
        if "=" not in p:
            raise AggregateError(f"--map expects name=Header, got {p!r}")
        k, v = p.split("=", 1)
        k = k.strip()
        if k not in LOOKUP_ALIASES:
            raise AggregateError(f"--map: unknown name {k!r} (use one of: {', '.join(LOOKUP_ALIASES)})")
        out[k] = v.strip()
    return out


def run(scored, scenarios, metrics, out, column_map=None) -> dict:
    defs = load_definitions(metrics)
    rows, skipped = read_scored(scored, defs)
    lookup = load_lookup(scenarios, column_map) if scenarios else None
    rows, not_found = enrich(rows, lookup)
    agg = aggregate(defs, rows, skipped, not_found, lookup is not None,
                    source_name=pathlib.Path(scored).name if not pathlib.Path(scored).is_dir() else "scored_runs")
    excluded = count_excluded(scored)
    if excluded is not None:
        agg["metadata"]["runs_excluded_by_engine"] = excluded
    paths = write_outputs(out, agg)
    return {"agg": agg, "paths": paths}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="WP3 aggregation and summary script: per-agent, per-workflow, per-risk and per-scenario summaries as CSV and JSON.")
    ap.add_argument("scored", nargs="?", default=None,
                    help="scored_runs.csv or scored_runs.json from the scoring engine, or the folder holding it "
                         "(default: input/scored_runs.csv next to this script)")
    ap.add_argument("--scenarios", help="scenario lookup CSV with workflow, type and risk IDs "
                                        "(default: input/scenario_lookup.csv, if that file exists)")
    ap.add_argument("--no-scenarios", action="store_true",
                    help="ignore the scenario lookup and use only the columns already in the scored file")
    ap.add_argument("--map", action="append", metavar="NAME=HEADER",
                    help="map a lookup column to its header, e.g. --map workflow=Domain (repeatable; names: "
                         + ", ".join(LOOKUP_ALIASES) + ")")
    ap.add_argument("--metrics", default=str(DEFAULT_METRICS),
                    help="metric definitions YAML (default: metric_definitions.yaml next to this script)")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="output folder (default: output/ next to this script)")
    ap.add_argument("--version", action="version", version=f"aggregate_summaries {__version__}")
    args = ap.parse_args(argv)

    try:
        scored = args.scored or str(DEFAULT_SCORED)
        if not args.scored and not DEFAULT_SCORED.is_file():
            raise AggregateError(
                "no scored runs file given and input/scored_runs.csv does not exist. Put the scoring engine's "
                "scored_runs.csv in the input folder, or pass its path: py aggregate_summaries.py <path to scored_runs.csv>")
        scenarios = None
        if not args.no_scenarios:
            if args.scenarios:
                scenarios = args.scenarios
            elif DEFAULT_LOOKUP.is_file():
                scenarios = str(DEFAULT_LOOKUP)
        result = run(scored, scenarios, args.metrics, args.out, _parse_map(args.map))
    except AggregateError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1

    meta = result["agg"]["metadata"]
    print(f"Summarised {meta['runs_summarised']} run(s) for {len(meta['agents'])} agent configuration(s).")
    if meta["runs_skipped_not_completed"]:
        print(f"  Skipped {meta['runs_skipped_not_completed']} row(s) whose status was not 'completed'.")
    if meta["scenarios_not_in_lookup"]:
        print(f"  Not in the scenario lookup (workflow and risk taken from the scored file): "
              f"{', '.join(meta['scenarios_not_in_lookup'])}")
    if meta["runs_without_risk_tag"]:
        print(f"  {meta['runs_without_risk_tag']} run(s) have no risk tag and are left out of the per-risk summary.")
    print(f"Mean overall trust score (all runs): "
          f"{'n/a' if meta['mean_overall_all_runs'] is None else format(meta['mean_overall_all_runs'], '.3f')} "
          f"({meta['trust_level_all_runs']})")
    print("Wrote:")
    for p in result["paths"].values():
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
