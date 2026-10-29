"""Metric formulas. Pure functions: counts in, scores out. No I/O."""
from __future__ import annotations

import math
from typing import Dict, Iterable, Optional

from .config import Config, MetricSpec


def clamp(value: float) -> float:
    return max(min(value, 1.0), 0.0)


def to_number(value) -> float:
    """Count from a CSV/JSON cell; blank, None and NaN count as 0."""
    if value is None or value == "":
        return 0.0
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if math.isnan(number) else number


def has_data(spec: MetricSpec, counts: Dict[str, float]) -> bool:
    return to_number(counts.get(spec.denominator)) > 0


def score_metric(spec: MetricSpec, counts: Dict[str, float], no_data: str) -> Optional[float]:
    """Score one metric. Returns None when the metric has no data and no_data == 'not_measured'."""
    den = to_number(counts.get(spec.denominator))
    if den == 0:
        return None if no_data == "not_measured" else 1.0
    num = sum(to_number(counts.get(f)) for f in spec.numerator)
    if spec.kind == "complement":
        return clamp(1 - num / den)
    return clamp(num / den)


def overall_score(cfg: Config, scores: Dict[str, Optional[float]]) -> Optional[float]:
    """Weighted sum. Metrics scored None are left out and the remaining weights are rescaled."""
    measured = {m: s for m, s in scores.items() if s is not None}
    if not measured:
        return None
    weight_sum = sum(cfg.weights[m] for m in measured)
    if len(measured) == len(cfg.metrics):
        return sum(cfg.weights[m.id] * measured[m.id] for m in cfg.metrics)
    return sum(cfg.weights[m] * s for m, s in measured.items()) / weight_sum


def band_for(cfg: Config, score: Optional[float]) -> str:
    if score is None:
        return "Not measured"
    score = round(score, 10)        # a score of exactly 0.5 must not fall a band because of float noise (0.49999999999999994)
    for name, minimum in cfg.bands:
        if score >= minimum:
            return name
    return cfg.bands[-1][0]


def score_counts(cfg: Config, counts: Dict[str, float], unlabelled: Iterable[str] = ()) -> dict:
    """Score one record of counts.

    unlabelled: metric IDs that could not be measured because the scenario labels they need
    are missing. They are treated exactly like a metric with no data.
    """
    skip = set(unlabelled)
    scores: Dict[str, Optional[float]] = {}
    not_measured = []
    for spec in cfg.metrics:
        if spec.id in skip or not has_data(spec, counts):
            not_measured.append(spec.id)
        if spec.id in skip:
            scores[spec.id] = None if cfg.no_data == "not_measured" else 1.0
        else:
            scores[spec.id] = score_metric(spec, counts, cfg.no_data)
    overall = overall_score(cfg, scores)
    return {
        "scores": scores,
        "not_measured": not_measured,
        "overall": overall,
        "band": band_for(cfg, overall),
    }
