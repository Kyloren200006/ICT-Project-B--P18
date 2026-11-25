# 14. Appendices

## Appendix A. Glossary

Terms are defined once here and used with these meanings throughout the report.

{{table:glossary}}

## Appendix B. Configuration and specification files

These are the three files the engine reads, reproduced in full. They are data, not code: weights, thresholds, bands, detection rules and the log format are changed by editing them.

### B.1 Metric definitions: `wp3_scoring_engine/metric_definitions.yaml`

{{inc:wp3_scoring_engine/metric_definitions.yaml|yaml}}

### B.2 Detection rules: `wp3_scoring_engine/detection_rules.yaml`

{{inc:wp3_scoring_engine/detection_rules.yaml|yaml}}

### B.3 Run-log JSON Schema: `wp3_scoring_engine/log_schema.json`

{{inc:wp3_scoring_engine/log_schema.json|json}}

## Appendix C. Worked example files

### C.1 Scenario labels: `worked_example/worked_example_lookup.csv`

{{inc:reports/wp3/worked_example/worked_example_lookup.csv|text}}

### C.2 Run logs: `worked_example/worked_example_runs.json`

{{inc:reports/wp3/worked_example/worked_example_runs.json|json}}

### C.3 Engine output for the worked runs: `worked_example/engine_output/scored_runs.csv`

{{inc:reports/wp3/worked_example/engine_output/scored_runs.csv|text}}

## Appendix D. Complete table of known false positives and false negatives

{{table:findings_full}}

## Appendix E. Probe catalogue and outcomes

Outcome codes: TP, TN, FP, FN as in section 7.2; "engine unmeasured" and "engine extra" are cells where only one side measured the metric. "Agreed" means the engine's counts and decision matched the hand label.

{{table:probes}}

## Appendix F. Test-pack summaries per agent and workflow

Aggregation of the 22 test-pack runs (test data, not results). Source: wp3_aggregation_scripts/examples/expected_output/summary_by_workflow.csv. "(unlabelled)" is the run whose scenario is missing from the lookup.

{{table:workflow_summary}}

## Appendix G. Files delivered with this report

Every file is listed in `report.yaml` with its path. Paths are relative to the root of the WP3 delivery.

{{table:manifest}}
