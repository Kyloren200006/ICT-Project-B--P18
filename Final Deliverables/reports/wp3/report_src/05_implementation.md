# 5. Implementation

## 5.1 Architecture

{{fig:arch|fig01_architecture|Architecture of the WP3 framework, from raw run log to score to aggregate. Source data: figures/data/fig01_architecture.csv and fig01_architecture_edges.csv; script: scripts/make_figures.py.}}

A run log from WP4 enters `loader.py`, which reads one file or a whole folder (`.json` or `.jsonl`) and validates every record against `log_schema.json`. Records that fail are listed in the inventory with the reason and do not stop the batch. `extract.py` looks up the scenario by `scenario_id` in WP2's labels (read by `labels.py`) and applies `detection_rules.yaml` to produce fourteen integer counts per run. `metrics.py` applies the formula of each metric, read from `metric_definitions.yaml`, to those counts; it is a few lines of code because the formulas are data. `scoring.py` combines the scores into the overall score and band and writes the output files. Two further packages read the engine's output and never re-score: `aggregate_summaries.py` (per agent, workflow, risk and scenario) and the dashboard. The engine uses no randomness, no clock and no network, and processes runs and files in a fixed order, so the same inputs and settings give byte-identical outputs; a test checks this and another checks that shuffling the input order changes nothing.

{{tcap:modules|Modules of the scoring engine (wp3_scoring_engine/wp3_eval/). Source: the files themselves; line counts computed by scripts/build_report.py.}}

{{table:modules}}

Repository paths used throughout this report are relative to the root of the WP3 delivery. The four packages are `wp3_scoring_engine/`, `wp3_aggregation_scripts/`, `wp3_calibration/` and `wp3_dashboard/`, and this report is in `reports/wp3/`. If the project repository places them under a parent folder, prefix that folder; the manifest `report.yaml` lists every path once, and the check script `scripts/check_report.py` fails if a listed file does not exist.

## 5.2 Run-log schema

The log format is the contract with WP4. It is a JSON Schema (draft 2020-12), `wp3_scoring_engine/log_schema.json`, schema version 0.1, with a human-readable description in `log_schema.md`. A log file holds one record per run, or many records in a JSON array or a `.jsonl` file. {{ref:schema_run}} to {{ref:schema_events}} list every field. Fields marked "required" must be present; a record missing one is rejected as `invalid_schema`.

{{tcap:schema_run|Run record: top-level fields and the agent block. Source: wp3_scoring_engine/log_schema.json; meaning text from wp3_evaluation_framework/log_schema.md.}}

{{table:schema_run}}

{{tcap:schema_session|Session, message and tool-call fields. A run has one or more sessions; the second and later sessions are what Memory Isolation checks. Source: wp3_scoring_engine/log_schema.json.}}

{{table:schema_session}}

{{tcap:schema_events|Filter events and memory events. Source: wp3_scoring_engine/log_schema.json.}}

{{table:schema_events}}

{{ref:annotated}} shows one run from the worked example, cut down to the records that matter, with comments added to say what each record contributes to the scores. The full log is `reports/wp3/worked_example/worked_example_runs.json` and is listed in Appendix C.

{{tcap:annotated|Annotated excerpt of run worked-001 (comments after // are added for this report and are not part of the format). Source: worked_example/worked_example_runs.json; script: scripts/make_worked_example.py.}}

{{annotated_log}}

## 5.3 Scenario labels

A log only records what the agent did. Whether an action was a leak or an unsafe action depends on the scenario, which WP2 designed. WP2's labels reach the engine as a CSV lookup file with one row per scenario, matched to the logs by `scenario_id`. The format is in {{ref:lookup}}. If WP2's file uses different headers, `--map` maps them without editing the file, and `python -m wp3_eval wp2-lookup` starts a lookup from WP2's scenario files; some labels (sensitive items, forbidden text) are held as prose in WP2's files and must be filled in by hand.

{{tcap:lookup|Scenario lookup columns. Source: wp3_scoring_engine/README.md section 5 and wp3_eval/labels.py.}}

{{table:lookup}}

A metric is "not measured" for a scenario when its labels are missing: DM-001 needs `allowed_data`; UAE-001 needs `disallowed_tools` or `forbidden_markers`; EA-001 needs `permitted_tools` or `expected_tools`; SIL-001 and ETL-001 need `sensitive_items`; MI-001 needs `cross_session_items` (or, if none are listed, the memory writes in the log); PIR-001 needs the injection labels. When a scenario is missing from the lookup altogether, the engine falls back to a list of injection phrases and memory writes, marks the run `heuristic` and records a note; the other metrics are not measured for that run.

## 5.4 Engine output files

One command scores a log or a folder: `py score_logs.py <logs> --scenarios <lookup> --out <folder>`. It writes four files. `scored_runs.csv` and `scored_runs.json` hold one row per scored run; `run_inventory.csv` lists every input run and what happened to it; `summary.json` gives the batch result. {{ref:scored_cols}} lists the columns of `scored_runs.csv`, taken from the file the engine produced for the test pack, and {{ref:inventory}} the inventory statuses.

{{tcap:scored_cols|Columns of scored_runs.csv. Source: the column list is read from wp3_aggregation_scripts/examples/scored_runs.csv; the meaning text is from wp3_scoring_engine/README.md section 4 and wp3_eval/scoring.py.}}

{{table:scored_cols}}

{{tcap:inventory|Run inventory statuses. Source: wp3_scoring_engine/README.md section 4 and wp3_eval/scoring.py.}}

{{table:inventory}}

## 5.5 Aggregation method

`wp3_aggregation_scripts/aggregate_summaries.py` reads `scored_runs.csv` (or `.json`) and writes four summaries as CSV plus one combined JSON file: per agent configuration (agent plus model plus mitigation), per agent and workflow, per agent and WP1 threat ID, and per agent and scenario. The rules are these.

The group score is the plain mean of the runs' overall scores, with the sample standard deviation and the lowest score alongside; the standard deviation is blank for a group of fewer than two runs. A run's overall score already has its weights rescaled over the metrics measured in that run, so groups are comparable. The per-metric mean for a group uses only the runs where that metric was measured, and a count of runs with no data is reported beside it, so a missing measurement is never averaged in as zero or one.

The per-risk score works from WP1's threat IDs. For each run tagged with a threat, take the mean of the scores of the metrics linked to that threat (only those measured in the run); the risk score is the mean of those per-run values. A scenario tagged with several threats counts toward each of them. A group's band is the band of its mean overall score.

Only runs with status `completed` are in `scored_runs.csv`, so failed and timed-out runs are not in any mean; the script reports how many the engine excluded. All runs weigh equally: a scenario run more times than another counts more, which is a property to watch when WP4's repeat counts differ between scenarios. The script rounds to six decimals, writes rows in a fixed order with Unix line endings and no timestamps, and gives byte-identical files on every computer. It never re-scores a run. Weights, bands and the metric-to-threat links come from the same `metric_definitions.yaml` the engine reads.

{{tcap:agg_files|Aggregation output files and their columns. Source: wp3_aggregation_scripts/README.md section 4 and examples/expected_output/.}}

{{table:agg_files}}

## 5.6 Dashboard

The dashboard (`wp3_dashboard/`) is a Python web application that reads three things and re-scores nothing: the metric definitions file, a `scored_runs.csv` or `.json`, and the calibration results folder. It has two front ends over the same code. `streamlit_app.py` is the Streamlit app (`streamlit run streamlit_app.py`; it needs `streamlit`, `pandas` and PyYAML) and is the main one, continuing the Streamlit dashboard of the earlier sprints. `dashboard.py` is a launcher built on the Python standard library plus PyYAML, which needs no further installation and can also write a static copy of every page with `--export`. Every number, table and chart comes from the shared package `wp3_dash/` (`data.py` for loading, checks and statistics; `charts.py` for the SVG charts; `frames.py` for the Streamlit tables), so the two front ends show the same figures. The earlier dashboard scored raw logs itself and treated a metric with no data as 1.0; the current one does neither and shows what the scoring engine wrote. Plotly is not used: the charts are drawn as SVG and shown in Streamlit with `st.image`, so they have no hover tooltips there (the launcher keeps them) and each is accompanied by a table of the same numbers. Both front ends re-read the files on every run so that a re-run of the engine shows on reload. Section 9 walks through the pages. As a check on the data, the dashboard recomputes every score cell from its counts using the formulas in the definitions file and reports any difference on its Data and checks page.

The Streamlit app's tables and charts are tested directly, and its script is also tested against a stand-in for the `streamlit` module that records the calls it makes, so the automated tests run without Streamlit installed. The team runs the app in Streamlit on Windows, including for the CapEx26 demonstration and on WP4's scored runs.
