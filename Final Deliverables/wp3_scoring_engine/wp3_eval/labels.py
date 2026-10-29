"""Scenario labels (WP2's side): the lookup file and the helper that builds it from WP2 scenario files.

One row per scenario, matched to run logs by scenario_id. Columns (header names are matched
loosely, and any header can be remapped with --map):

  scenario_id        required. Exact WP2 scenario ID.
  workflow           scheduling / email / web research / file handling
  type               benign or adversarial
  attack_technique   e.g. prompt_injection
  risk_ids           linked WP1 risks, separated by ';' (WP1 threat IDs TC1-TC6)
  injection_planted  true / false. Blank: inferred from type and attack_technique.
  injection_count    number of planted injections (default 1)
  sensitive_items    items that must not leak, separated by '|'. Use '~' for alternative spellings
  forbidden_markers  text that must not appear in an executed tool call or the agent's output
  disallowed_tools   tools the agent must not execute
  permitted_tools    tools the task allows
  expected_tools     tools the task is expected to use
  allowed_data       files/folders/IDs the task may read ('|' separated, '*' wildcards allowed)
  cross_session_items items that must not carry from one session to the next
"""
from __future__ import annotations

import csv
import json
import pathlib
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

import yaml

ALIASES = {
    "scenario_id": ["scenario_id", "scenario", "task_id", "id", "scenario_ids"],
    "workflow": ["workflow", "domain", "workflow_type"],
    "type": ["type", "scenario_type", "benign_adversarial", "behaviour", "behavior"],
    "attack_technique": ["attack_technique", "attack", "adversarial_category", "technique"],
    "risk_ids": ["risk_ids", "linked_risk_ids", "linked_risks", "risks", "risk"],
    "injection_planted": ["injection_planted", "injection", "has_injection"],
    "injection_count": ["injection_count", "injections"],
    "sensitive_items": ["sensitive_items", "sensitive", "confidential_items"],
    "forbidden_markers": ["forbidden_markers", "forbidden", "must_not_appear"],
    "disallowed_tools": ["disallowed_tools", "forbidden_tools", "blocked_tools"],
    "permitted_tools": ["permitted_tools", "allowed_tools", "tools_available", "tools"],
    "expected_tools": ["expected_tools", "expected_tool_calls"],
    "allowed_data": ["allowed_data", "read_scope", "data_scope"],
    "cross_session_items": ["cross_session_items", "memory_items"],
}


def _norm_header(h: str) -> str:
    return str(h).strip().lower().replace(" ", "_").replace("-", "_")


def _split(value, sep: str) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [p.strip() for p in str(value).split(sep) if p.strip()]


def _alias_groups(value, alias_sep: str = "~") -> List[List[str]]:
    """'a~b|c' -> [['a','b'],['c']]  (one item can have several spellings)."""
    groups: List[List[str]] = []
    for item in _split(value, "|"):
        spellings = [s.strip() for s in item.split(alias_sep) if s.strip()]
        if spellings:
            groups.append(spellings)
    return groups


def _tri_bool(value) -> Optional[bool]:
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in ("true", "yes", "y", "1"):
        return True
    if s in ("false", "no", "n", "0"):
        return False
    return None


@dataclass
class ScenarioLabels:
    scenario_id: str = ""
    known: bool = False                      # False = the scenario is not in the lookup file
    workflow: str = ""
    type: str = ""
    attack_technique: str = ""
    risk_ids: List[str] = field(default_factory=list)
    injection_planted: Optional[bool] = None
    injection_count: int = 1
    sensitive_items: List[List[str]] = field(default_factory=list)
    forbidden_markers: List[List[str]] = field(default_factory=list)
    disallowed_tools: List[str] = field(default_factory=list)
    permitted_tools: List[str] = field(default_factory=list)
    expected_tools: List[str] = field(default_factory=list)
    allowed_data: List[str] = field(default_factory=list)
    cross_session_items: List[List[str]] = field(default_factory=list)

    @classmethod
    def unknown(cls, scenario_id: str = "") -> "ScenarioLabels":
        return cls(scenario_id=scenario_id, known=False)

    def injection_expected(self) -> Optional[bool]:
        """True/False when the labels say so, None when unknown (the engine then uses the phrase rules)."""
        if self.injection_planted is not None:
            return self.injection_planted
        if "inject" in self.attack_technique.lower():
            return True
        if self.type.lower().startswith("benign"):
            return False
        return None


def _resolve_columns(headers: Iterable[str], column_map: Optional[Dict[str, str]]) -> Dict[str, str]:
    """canonical name -> actual header in the file."""
    norm = {_norm_header(h): h for h in headers}
    resolved: Dict[str, str] = {}
    for canonical, names in ALIASES.items():
        if column_map and canonical in column_map:
            wanted = column_map[canonical]
            if wanted in headers:
                resolved[canonical] = wanted
            elif _norm_header(wanted) in norm:
                resolved[canonical] = norm[_norm_header(wanted)]
            else:
                raise ValueError(f"--map {canonical}={wanted}: no such column in the lookup file")
            continue
        for n in names:
            if n in norm:
                resolved[canonical] = norm[n]
                break
    if "scenario_id" not in resolved:
        raise ValueError("lookup file needs a scenario ID column (scenario_id, task_id or id); use --map scenario_id=<header>")
    return resolved


def _row_to_labels(row: Dict[str, str], cols: Dict[str, str], alias_sep: str) -> ScenarioLabels:
    def get(name: str) -> str:
        return (row.get(cols[name]) or "").strip() if name in cols else ""

    try:
        count = int(float(get("injection_count"))) if get("injection_count") else 1
    except ValueError:
        count = 1
    return ScenarioLabels(
        scenario_id=get("scenario_id"),
        known=True,
        workflow=get("workflow"),
        type=get("type"),
        attack_technique=get("attack_technique"),
        risk_ids=_split(get("risk_ids"), ";"),
        injection_planted=_tri_bool(get("injection_planted")),
        injection_count=max(count, 0),
        sensitive_items=_alias_groups(get("sensitive_items"), alias_sep),
        forbidden_markers=_alias_groups(get("forbidden_markers"), alias_sep),
        disallowed_tools=_split(get("disallowed_tools"), "|"),
        permitted_tools=_split(get("permitted_tools"), "|"),
        expected_tools=_split(get("expected_tools"), "|"),
        allowed_data=_split(get("allowed_data"), "|"),
        cross_session_items=_alias_groups(get("cross_session_items"), alias_sep),
    )


def _lookup_from_rows(rows: List[dict], headers: List[str], column_map: Optional[Dict[str, str]],
                      alias_sep: str) -> Dict[str, ScenarioLabels]:
    cols = _resolve_columns(headers, column_map)
    out: Dict[str, ScenarioLabels] = {}
    for row in rows:
        labels = _row_to_labels(row, cols, alias_sep)
        if labels.scenario_id:
            out[labels.scenario_id] = labels
    return out


def load_lookup_bytes(raw: bytes, column_map: Optional[Dict[str, str]] = None, alias_sep: str = "~") -> Dict[str, ScenarioLabels]:
    """Same as load_lookup, for an uploaded CSV held in memory (used by the dashboard)."""
    import io
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    return _lookup_from_rows(list(reader), list(reader.fieldnames or []), column_map, alias_sep)


def load_lookup(path, column_map: Optional[Dict[str, str]] = None, alias_sep: str = "~") -> Dict[str, ScenarioLabels]:
    """Read the scenario lookup (.csv, or a .json/.yaml list of rows) into {scenario_id: labels}."""
    path = pathlib.Path(path)
    if path.suffix.lower() == ".csv":
        return load_lookup_bytes(path.read_bytes(), column_map, alias_sep)
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or []
    rows = []
    for r in data:
        row = {}
        for k, v in r.items():
            if isinstance(v, list):
                row[k] = (";" if _norm_header(k) in ALIASES["risk_ids"] else "|").join(str(x) for x in v)
            else:
                row[k] = v
        rows.append(row)
    return _lookup_from_rows(rows, list(rows[0].keys()) if rows else [], column_map, alias_sep)


# ---------------------------------------------------------------------------
# WP2 scenario files -> lookup rows
# ---------------------------------------------------------------------------
LOOKUP_COLUMNS = [
    "scenario_id", "workflow", "type", "attack_technique", "risk_ids", "injection_planted",
    "injection_count", "sensitive_items", "forbidden_markers", "disallowed_tools",
    "permitted_tools", "expected_tools", "allowed_data", "cross_session_items",
]


def _load_scenario_file(path: pathlib.Path) -> Optional[dict]:
    try:
        with open(path, encoding="utf-8") as fh:
            doc = yaml.safe_load(fh)   # JSON is valid YAML
    except Exception:
        return None
    if isinstance(doc, dict) and (doc.get("task_id") or doc.get("scenario_id")) and (
        "user_instruction" in doc or "agent_config" in doc or "expected_behaviour" in doc
    ):
        return doc
    return None


def scenario_to_row(doc: dict, category_to_risk: Dict[str, str]) -> dict:
    """Map one WP2 scenario (task schema) to a lookup row. Prose-only facts are left blank."""
    cfg = doc.get("agent_config") or {}
    perms = cfg.get("permissions") or {}
    exp = doc.get("expected_behaviour") or {}
    env = doc.get("environment") or {}
    category = str(doc.get("adversarial_category") or "")
    stype = str(doc.get("type") or "")

    read_scope = perms.get("read_scope") or []
    if isinstance(read_scope, str):
        read_scope = [read_scope]
    disallowed = [k for k, v in perms.items() if v is False and k.endswith(("email", "file", "calendar", "tool", "payment"))]
    risk = category_to_risk.get(category.lower().replace(" ", "_").replace("-", "_"), "")

    planted = ""
    if "injected_content" in env or "inject" in category.lower():
        planted = "true"
    elif stype.lower().startswith("benign"):
        planted = "false"

    return {
        "scenario_id": doc.get("task_id") or doc.get("scenario_id"),
        "workflow": doc.get("domain", ""),
        "type": stype,
        "attack_technique": category,
        "risk_ids": risk,
        "injection_planted": planted,
        "injection_count": "1" if planted == "true" else "",
        "sensitive_items": "",          # WP2 keeps these as prose: fill in by hand
        "forbidden_markers": "",        # WP2 keeps these as prose: fill in by hand
        "disallowed_tools": "|".join(disallowed),
        "permitted_tools": "|".join(cfg.get("tools_available") or []),
        "expected_tools": "|".join(exp.get("expected_tool_calls") or []),
        "allowed_data": "|".join(str(s) for s in read_scope),
        "cross_session_items": "",
    }


def build_lookup_from_wp2(paths: Iterable, category_to_risk: Dict[str, str]) -> List[dict]:
    files: List[pathlib.Path] = []
    for p in paths:
        p = pathlib.Path(p)
        if p.is_dir():
            files += sorted(f for f in p.rglob("*") if f.suffix.lower() in (".json", ".yml", ".yaml"))
        else:
            files.append(p)
    rows = {}
    for f in files:
        doc = _load_scenario_file(f)
        if doc:
            row = scenario_to_row(doc, category_to_risk)
            rows[row["scenario_id"]] = row
    return [rows[k] for k in sorted(rows)]


def write_lookup_csv(rows: List[dict], path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=LOOKUP_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
