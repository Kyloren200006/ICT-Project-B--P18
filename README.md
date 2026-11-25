# ICT Project B - P18

**Benchmarking Trust: Evaluating Privacy and Security Risks in Agentic AI Systems**

## Project Overview

This project was developed as part of ICT30017 - ICT Project A and ICT30018 - ICT Project B at Swinburne University of Technology.

The aim of the project is to develop a framework for evaluating privacy and security risks in agentic AI systems. The framework uses seven trust evaluation metrics to analyse agent behaviour, calculate trust scores and classify potential security risks.

This repository holds the WP3 (Evaluation Framework and Metrics) work: metric definitions, a run-log schema, a Python scoring engine, aggregation scripts, a Streamlit dashboard, the calibration and validation report, the evaluation reports for WP4's agent runs and the WP3 technical report.

## Main Features

- Seven trust evaluation metrics for assessing AI agent behaviour.
- Weighted trust scoring and risk classification.
- Support for structured CSV and JSON log data.
- Streamlit dashboard for displaying evaluation results.
- Charts, log tables and downloadable CSV results.
- Aggregation scripts for summarising evaluation results.
- Metric definitions and supporting documentation.
- Automated tests for the scoring engine, aggregation scripts, calibration and dashboard.

## Project Structure

- `Final Deliverables/` - final WP3 deliverables for the client (start with its `README.md`)
  - `Metric Definitions/` - the seven metrics: formulas, weights, thresholds and linked risk IDs (`metric_definitions.yaml` is the single source of truth)
  - `Log schema/` - run-log JSON Schema, specification and example log for WP4
  - `wp3_scoring_engine/` - Python scoring engine and tests, with WP4's run logs
  - `wp3_aggregation_scripts/` - per-agent, per-workflow, per-risk and per-scenario summaries, with tests
  - `wp3_calibration/` - calibration and validation report, test pack, probes and results
  - `Evaluation Reports/` - scores for all of WP4's agent runs, summaries and the written evaluation report
  - `wp3_dashboard/` - final Streamlit metrics dashboard, with tests and screenshots in `docs/`
  - `reports/wp3/` - WP3 technical report (`report.docx`, `report.md`, `report.yaml`)
- `dashboard/` - early Sprint 5 prototype dashboard (superseded by `Final Deliverables/wp3_dashboard/`)
- `Week 1` to `Week 11 Deliverables/`, `Semester 1 Final Deliverables/` - ICT30017 Project A work (metric definitions, scoring prototypes, validation framework)

## Running the Tools

Requires Python 3.10 or later. Each component has its own `requirements.txt`. The commands below use `py` (Windows); on macOS or Linux use `python3`.

### Scoring engine

```
cd "Final Deliverables/wp3_scoring_engine"
py -m pip install -r requirements.txt
py score_logs.py
```

With no arguments this scores WP4's logs in `input/logs/` against `input/scenarios/scenario_lookup.csv` and writes to `output/`.

### Aggregation

```
cd "Final Deliverables/wp3_aggregation_scripts"
py -m pip install -r requirements.txt
py aggregate_summaries.py ../wp3_scoring_engine/output/scored_runs.csv --scenarios ../wp3_scoring_engine/input/scenarios/scenario_lookup.csv --out output
```

### Dashboard

```
cd "Final Deliverables/wp3_dashboard"
py -m pip install -r requirements.txt
py -m streamlit run streamlit_app.py
```

The dashboard opens at http://localhost:8501. To view WP4's results, use "Upload a scored file" in the sidebar and choose `wp3_scoring_engine/output/scored_runs.csv`. Without Streamlit, `py dashboard.py` runs an offline version in the browser.

### Tests

Run inside each component folder:

```
py -m unittest discover -s tests -t .
```

Each component folder has its own README with full instructions.

## Testing and Development Status

- 152 automated tests pass: scoring engine (42), aggregation scripts (35), calibration (17) and dashboard (58).
- The dashboard reads `metric_definitions.yaml` and the scoring engine's output; it does not score logs itself.
- A metric with no data is reported as "not measured" and excluded from the overall score, so small samples are not shown as safe.
- WP4's 56 agent runs all passed the log schema; the 48 completed runs were scored and all are Trusted (overall 1.000). The 8 failed Gemini runs were excluded.
- WP4's runs cover two adversarial email scenarios only, so they cannot rank agents; see the limitations in `Evaluation Reports/evaluation_report.md`.

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
