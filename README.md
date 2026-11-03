# ICT Project B - P18

**Benchmarking Trust: Evaluating Privacy and Security Risks in Agentic AI Systems**

## Project Overview

This project was developed as part of ICT30017 - ICT Project A and ICT30018 - ICT Project B at Swinburne University of Technology.

The aim of the project is to develop a framework for evaluating privacy and security risks in agentic AI systems. The framework uses seven trust evaluation metrics to analyse agent behaviour, calculate trust scores and classify potential security risks.

This repository holds the WP3 (Evaluation Framework and Metrics) work: metric definitions, a run-log schema, a Python scoring engine, aggregation scripts and a Streamlit dashboard.

## Main Features

- Seven trust evaluation metrics for assessing AI agent behaviour.
- Weighted trust scoring and risk classification.
- Support for structured CSV and JSON log data.
- Streamlit dashboard for displaying evaluation results.
- Charts, log tables and downloadable CSV results.
- Aggregation scripts for summarising evaluation results.
- Metric definitions and supporting documentation.
- Automated tests for the scoring engine, aggregation scripts and dashboard.

## Project Structure

- `Final Deliverables/` - final WP3 deliverables for the client
  - `Metric Definitions/` - the seven metrics: formulas, weights, thresholds and linked risk IDs (`metric_definitions.yaml` is the single source of truth)
  - `Log schema/` - run-log JSON Schema, specification and example log for WP4
  - `wp3_scoring_engine/` - Python scoring engine and tests
  - `wp3_aggregation_scripts/` - per-agent, per-workflow, per-risk and per-scenario summaries, with tests
  - `wp3_dashboard/` - final Streamlit metrics dashboard, with tests and screenshots in `docs/`
- `dashboard/` - early Sprint 5 prototype dashboard (superseded by `Final Deliverables/wp3_dashboard/`)
- `Week 1` to `Week 11 Deliverables/`, `Semester 1 Final Deliverables/` - ICT30017 Project A work (metric definitions, scoring prototypes, validation framework)

## Running the Tools

Requires Python 3.10 or later. Each component has its own `requirements.txt`. The commands below use `py` (Windows); on macOS or Linux use `python3`.

### Dashboard

```
cd "Final Deliverables/wp3_dashboard"
py -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

The dashboard opens at http://localhost:8501. Without Streamlit, `py dashboard.py` runs an offline version in the browser.

### Scoring engine

```
cd "Final Deliverables/wp3_scoring_engine"
py -m pip install -r requirements.txt
py score_logs.py examples/example_runs.json --scenarios examples/scenario_lookup.csv --out results
```

To score a whole folder of logs, pass the folder instead of a single file.

### Aggregation

```
cd "Final Deliverables/wp3_aggregation_scripts"
py -m pip install -r requirements.txt
py aggregate_summaries.py examples/scored_runs.csv --scenarios examples/scenario_lookup.csv --out results
```

### Tests

Run inside each component folder:

```
py -m unittest discover -s tests -t .
```

Each component folder has its own README with full instructions.

## Testing and Development Status

- 131 automated tests pass: scoring engine (38), aggregation scripts (35) and dashboard (58).
- The dashboard reads `metric_definitions.yaml` and the scoring engine's output; it does not score logs itself.
- A metric with no data is reported as "not measured" and excluded from the overall score, so small samples are not shown as safe.
- All current results come from synthetic and sample logs.

Remaining before the v1.0 release: scoring WP4's full agent-run logs, the calibration and validation report, the evaluation reports and the WP3 technical report.

## Technologies Used

- Python
- Streamlit
- Pandas
- YAML and JSON
- GitHub
- Jira

## Project Team

ICT Project B - Group P18

- Sandev Fernando
- Suhash Barani Prem
- Sam O'Connor
- Sebastian Haney
- Sahan Maduranga

## Academic Project

Developed for ICT30017 - ICT Project A and ICT30018 - ICT Project B at Swinburne University of Technology.
