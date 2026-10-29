"""Score run logs. This is the engine's core: logs in, scored rows out."""
from __future__ import annotations

import csv
import json
import pathlib
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from .config import Config, load_rules
from .extract import COUNT_FIELDS, extract_counts
from .labels import ScenarioLabels
from .loader import Item, get_validator, load_path, validation_errors
from .metrics import score_counts, to_number

IDENTITY_COLUMNS = [
    "run_id", "scenario_id", "repeat_index", "agent_config", "provider", "model", "mitigation",
    "status", "workflow", "scenario_type", "risk_ids", "label_source", "source_file", "notes",
    "timestamp", "session_id", "log_id", "behavior_type",
]


@dataclass
class ScoreResult:
    rows: List[dict] = field(default_factory=list)
    inventory: List[dict] = field(default_factory=list)


def _apply_scores(cfg: Config, row: dict, counts: dict, unlabelled: Iterable[str] = ()) -> dict:
    result = score_counts(cfg, counts, unlabelled)
    for spec in cfg.metrics:
        row[spec.score_column] = result["scores"][spec.id]
    row["metrics_not_measured"] = ";".join(result["not_measured"])
    row["overall_trust_score"] = result["overall"]
    row["trust_level"] = result["band"]
    return row


def _run_row(cfg: Config, rules: dict, run: dict, labels: ScenarioLabels, source: str) -> dict:
    counts, unlabelled, label_source, notes = extract_counts(run, labels, rules)
    agent = run.get("agent") or {}
    sessions = run.get("sessions") or []
    stype = labels.type or ("adversarial" if counts["total_injection_attempts"] else "unknown")
    row = {
        "run_id": run.get("run_id", ""),
        "scenario_id": run.get("scenario_id", ""),
        "repeat_index": run.get("repeat_index", 0),
        "agent_config": agent.get("agent_config", ""),
        "provider": agent.get("provider", ""),
        "model": agent.get("model", ""),
        "mitigation": agent.get("mitigation") or "",
        "status": run.get("status", ""),
        "workflow": labels.workflow,
        "scenario_type": labels.type,
        "risk_ids": ";".join(labels.risk_ids),
        "label_source": label_source,
        "source_file": source,
        "notes": "; ".join(notes),
        # columns the dashboard has always shown
        "timestamp": run.get("started_at", ""),
        "session_id": sessions[0].get("session_id", "") if sessions else run.get("run_id", ""),
        "log_id": run.get("run_id", ""),
        "behavior_type": stype,
    }
    row.update(counts)
    return _apply_scores(cfg, row, counts, unlabelled)


def score_items(items: List[Item], cfg: Config, rules: dict, lookup: Optional[Dict[str, ScenarioLabels]] = None,
                validate: bool = True, schema_path: Optional[str] = None,
                problems: Optional[List[dict]] = None) -> ScoreResult:
    lookup = lookup or {}
    result = ScoreResult(inventory=list(problems or []))
    validator = get_validator(schema_path) if validate else None
    for item in items:
        if item.kind == "run":
            run = item.data
            rid, sid = run.get("run_id", ""), run.get("scenario_id", "")
            errs = validation_errors(run, validator) if validator else []
            if errs:
                result.inventory.append({"source": item.source, "run_id": rid, "scenario_id": sid,
                                         "status": "invalid_schema", "detail": " | ".join(errs)})
                continue
            if run.get("status", "completed") != "completed":
                result.inventory.append({"source": item.source, "run_id": rid, "scenario_id": sid,
                                         "status": "excluded_failed_run",
                                         "detail": f"status={run.get('status')}; {run.get('error') or ''}".strip("; ")})
                continue
            labels = lookup.get(sid) or ScenarioLabels.unknown(sid)
            row = _run_row(cfg, rules, run, labels, item.source)
            result.rows.append(row)
            result.inventory.append({"source": item.source, "run_id": rid, "scenario_id": sid,
                                     "status": "scored", "detail": row["notes"]})

    def key(r: dict):
        return (str(r.get("agent_config", "")), str(r.get("scenario_id") or r.get("task_id") or ""),
                int(to_number(r.get("repeat_index"))), str(r.get("run_id") or r.get("log_id") or ""),
                str(r.get("source_file", "")), str(r.get("timestamp", "")))

    result.rows.sort(key=key)
    result.inventory.sort(key=lambda r: (str(r.get("source", "")), str(r.get("run_id", "")), str(r.get("status", ""))))
    return result


def score_path(path, cfg: Config, rules: Optional[dict] = None, lookup: Optional[Dict[str, ScenarioLabels]] = None,
               validate: bool = True, schema_path: Optional[str] = None) -> ScoreResult:
    items, problems = load_path(path)
    return score_items(items, cfg, rules if rules is not None else load_rules(), lookup, validate, schema_path, problems)


# ---------------------------------------------------------------------------
# Summary and output files
# ---------------------------------------------------------------------------
def summarise(cfg: Config, result: ScoreResult) -> dict:
    from .metrics import band_for
    rows = result.rows
    overall = [r["overall_trust_score"] for r in rows if r.get("overall_trust_score") is not None]
    mean_overall = sum(overall) / len(overall) if overall else None
    per_metric = {}
    coverage = {}
    for spec in cfg.metrics:
        vals = [r[spec.score_column] for r in rows if r.get(spec.score_column) is not None]
        per_metric[spec.id] = round(sum(vals) / len(vals), cfg.decimals) if vals else None
        coverage[spec.id] = sum(1 for r in rows if spec.id in str(r.get("metrics_not_measured", "")).split(";"))
    counts = {}
    for r in result.inventory:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {
        "framework_version": cfg.version,
        "metric_definitions": pathlib.Path(cfg.source).name,
        "no_data_behaviour": cfg.no_data,
        "runs_scored": len(rows),
        "inventory": dict(sorted(counts.items())),
        "mean_overall_trust_score": None if mean_overall is None else round(mean_overall, cfg.decimals),
        "trust_level": band_for(cfg, mean_overall),
        "mean_metric_scores": per_metric,
        "runs_with_no_data_per_metric": coverage,
    }


def _rounded(value, decimals: int):
    return round(value, decimals) if isinstance(value, float) else value


def write_outputs(out_dir, cfg: Config, result: ScoreResult) -> Dict[str, str]:
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    # columns: identity first, then any extra columns in first-seen order, counts, scores, overall
    score_cols = [s.score_column for s in cfg.metrics]
    tail = ["metrics_not_measured", "overall_trust_score", "trust_level"]
    fixed = set(IDENTITY_COLUMNS) | set(COUNT_FIELDS) | set(score_cols) | set(tail)
    extras: List[str] = []
    for r in result.rows:
        for k in r:
            if k not in fixed and k not in extras:
                extras.append(k)
    present = lambda cols: [c for c in cols if any(c in r for r in result.rows)]
    columns = present(IDENTITY_COLUMNS) + extras + present(COUNT_FIELDS) + score_cols + tail
    rows = [{k: _rounded(v, cfg.decimals) for k, v in r.items()} for r in result.rows]

    paths = {}
    p = out / "scored_runs.csv"
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in columns})
    paths["scored_runs_csv"] = str(p)

    p = out / "scored_runs.json"
    p.write_text(json.dumps([{k: r.get(k) for k in columns} for r in rows], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    paths["scored_runs_json"] = str(p)

    p = out / "run_inventory.csv"
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["source", "run_id", "scenario_id", "status", "detail"], extrasaction="ignore")
        w.writeheader()
        for r in result.inventory:
            w.writerow({k: r.get(k, "") for k in ["source", "run_id", "scenario_id", "status", "detail"]})
    paths["run_inventory_csv"] = str(p)

    p = out / "summary.json"
    p.write_text(json.dumps(summarise(cfg, result), indent=2) + "\n", encoding="utf-8")
    paths["summary_json"] = str(p)
    return paths
