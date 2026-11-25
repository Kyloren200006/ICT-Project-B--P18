# 2. Objectives and scope

## 2.1 Goals as set in the guide

The final deliverables guide asks WP3 for Evaluation Framework v1.0: "metric definitions plus a scoring engine that turns agent run logs into per-scenario scores and aggregate reports, with no manual steps." It lists nine WP3 deliverables, and {{ref:deliverables}} shows where each one stands and where it is in the repository. Three goals follow from that sentence and shaped every design choice: the metrics must be defined precisely enough that two people computing one by hand get the same number; the engine must run from a single command and give identical output on identical input; and every setting a team might want to change (weights, thresholds, bands, detection rules) must live in a data file, so that a change needs no code edit.

## 2.2 In scope

The metric definitions (ID, name, formula, inputs, range, direction, threshold, linked risk IDs); the run-log schema that WP4 must emit; the scoring engine; the aggregation and summary scripts; the calibration and validation report; the metrics dashboard; and this technical report. The advanced metrics the guide names, memory leakage, unsafe actions and external tool leakage, are MI-001, UAE-001 and ETL-001.

## 2.3 Out of scope

WP3 does not choose or write scenarios (WP2), define the risk taxonomy (WP1), or run agents (WP4). It does not judge meaning: the engine checks text, tool names and structure against labels, and where a label is missing it reports "not measured" rather than guessing. It does not score model weights or training data; it scores what is in a run log.

## 2.4 Changes of scope

Three changes were made during the project, each recorded here with its reason.

The metric definitions were consolidated. The Week 3 definitions (`formal_metric_definitions.md`, five metrics) and the Week 9 `schemascore_v2.yaml` (whose weights had drifted out of step with the dashboard demo) are superseded by `metric_definitions.yaml`, now the single source of truth that the engine, the aggregation scripts and the dashboard all read. The final seven metrics include the three advanced ones the guide names: MI-001 (memory leakage), UAE-001 (unsafe actions) and ETL-001 (external tool leakage).

The rule for a metric with nothing to measure changed. The early dashboard demo scored such a metric as 1.0 (fully trusted). That rule was dropped: a run in which nothing could be measured would look perfectly safe. The final rule leaves the metric out and rescales the remaining weights (section 4.5; {{ref:worked_table}} shows it on a worked run).

The engine reads raw run logs, not counts. WP3's earlier work, including a 90-row hand-built file of counts, scored counts that a person had already extracted. Those are counts, not logs, so they cannot test the extraction step, which is where most of the risk is. The engine now reads WP4's logs directly and extracts the counts itself, and the validation in section 7 tests that step.

{{tcap:deliverables|WP3 deliverables against the final deliverables guide, with status and location. Paths are relative to the root of the WP3 delivery. Source: the files named in the Location column; status from this report's sections 6 to 8.}}

{{table:deliverables}}
