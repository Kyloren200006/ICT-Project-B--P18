"""Load the metric definitions (single source of truth) and the detection rules."""
from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import yaml

PACKAGE_DIR = pathlib.Path(__file__).resolve().parent
ROOT_DIR = PACKAGE_DIR.parent
DEFAULT_METRICS_PATH = ROOT_DIR / "metric_definitions.yaml"
DEFAULT_RULES_PATH = ROOT_DIR / "detection_rules.yaml"
DEFAULT_SCHEMA_PATH = ROOT_DIR / "log_schema.json"

NO_DATA_MODES = ("score_one", "not_measured")
SCORING_KINDS = ("complement", "ratio")


class ConfigError(ValueError):
    """The metric definitions file is missing something the engine needs."""


@dataclass(frozen=True)
class MetricSpec:
    id: str                      # e.g. "PIR-001"
    name: str                    # e.g. "Prompt Injection Resistance"
    column: str                  # e.g. "PIR_001" -> output column "PIR_001_score"
    kind: str                    # "complement" or "ratio"
    numerator: Tuple[str, ...]   # raw count fields summed in the numerator
    denominator: str             # raw count field in the denominator
    threshold: float
    direction: str
    risk_ids: Tuple[str, ...]    # linked WP1 risks (WP1 threat IDs TC1-TC6)

    @property
    def score_column(self) -> str:
        return f"{self.column}_score"


@dataclass
class Config:
    metrics: List[MetricSpec]
    weights: Dict[str, float]
    bands: List[Tuple[str, float]]      # (name, min score), highest first
    no_data: str
    decimals: int
    version: str
    source: str

    def metric(self, metric_id: str) -> MetricSpec:
        for m in self.metrics:
            if m.id == metric_id:
                return m
        raise KeyError(metric_id)

    @property
    def raw_fields(self) -> List[str]:
        """Every raw count field the metrics read, in a stable order."""
        seen: List[str] = []
        for m in self.metrics:
            for f in list(m.numerator) + [m.denominator]:
                if f not in seen:
                    seen.append(f)
        return seen

    def risks(self) -> List[str]:
        """All linked risks, in first-seen order."""
        out: List[str] = []
        for m in self.metrics:
            for r in m.risk_ids:
                if r not in out:
                    out.append(r)
        return out


def load_config(path: Optional[str] = None, no_data: Optional[str] = None) -> Config:
    path = pathlib.Path(path) if path else DEFAULT_METRICS_PATH
    try:
        with open(path, encoding="utf-8") as fh:
            doc = yaml.safe_load(fh)
    except FileNotFoundError as exc:
        raise ConfigError(f"metric definitions not found: {path}") from exc

    metrics_doc = (doc or {}).get("metrics") or {}
    weights = ((doc.get("overall_score") or {}).get("weights")) or {}
    if not metrics_doc:
        raise ConfigError("metric_definitions.yaml has no 'metrics' section")

    specs: List[MetricSpec] = []
    for mid, m in metrics_doc.items():
        sc = m.get("scoring") or {}
        kind = sc.get("kind")
        if kind not in SCORING_KINDS:
            raise ConfigError(f"{mid}: scoring.kind must be one of {SCORING_KINDS}")
        num = tuple(sc.get("numerator") or ())
        den = sc.get("denominator")
        if not num or not den:
            raise ConfigError(f"{mid}: scoring needs numerator and denominator")
        if mid not in weights:
            raise ConfigError(f"{mid}: no weight in overall_score.weights")
        specs.append(MetricSpec(
            id=mid,
            name=m.get("name", mid),
            column=m.get("column") or mid.replace("-", "_"),
            kind=kind,
            numerator=num,
            denominator=den,
            threshold=float(m.get("threshold", 0.0)),
            direction=m.get("direction", "higher_is_safer"),
            risk_ids=tuple(m.get("risk_ids") or ()),
        ))

    total = sum(float(weights[s.id]) for s in specs)
    if abs(total - 1.0) > 1e-6:
        raise ConfigError(f"weights must sum to 1.0 (got {total})")

    bands = sorted(
        ((b["name"], float(b["min"])) for b in (doc.get("risk_bands") or [])),
        key=lambda b: -b[1],
    )
    if not bands:
        raise ConfigError("risk_bands is empty")

    settings = doc.get("settings") or {}
    mode = no_data or settings.get("no_data_behaviour", "score_one")
    if mode not in NO_DATA_MODES:
        raise ConfigError(f"no_data_behaviour must be one of {NO_DATA_MODES}")

    return Config(
        metrics=specs,
        weights={s.id: float(weights[s.id]) for s in specs},
        bands=bands,
        no_data=mode,
        decimals=int(settings.get("decimals", 6)),
        version=str((doc.get("schema_info") or {}).get("version", "")),
        source=str(path),
    )


def load_rules(path: Optional[str] = None) -> dict:
    path = pathlib.Path(path) if path else DEFAULT_RULES_PATH
    try:
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except FileNotFoundError as exc:
        raise ConfigError(f"detection rules not found: {path}") from exc
