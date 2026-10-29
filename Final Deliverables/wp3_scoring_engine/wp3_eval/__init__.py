"""WP3 evaluation framework: scores agent run logs with the seven WP3 trust metrics.

Everything that may change later (weights, thresholds, bands, formulas, linked risks,
detection rules, scenario labels) lives in data files, not in this code:

    metric_definitions.yaml   metrics, weights, thresholds, bands, linked risks
    detection_rules.yaml      rules that turn raw run logs into metric counts
    scenario_lookup.csv       WP2 scenario labels (workflow, risk IDs, sensitive items, ...)

Command line:  python -m wp3_eval --help
"""

__version__ = "1.0.0"
