# ICT Project B - P18

## Benchmarking Trust: Evaluating Privacy and Security Risks in Agentic AI Systems

### Project Overview

This project was developed as part of ICT30017 - ICT Project A and ICT30018 - ICT Project B at Swinburne University of Technology.

The aim of the project is to develop a framework for evaluating privacy and security risks in agentic AI systems. The framework uses seven trust evaluation metrics to analyse agent behaviour, calculate trust scores and classify potential security risks.

The project includes a Python-based scoring engine, aggregation scripts, metric definitions, a run-log schema and a Streamlit dashboard.

### Main Features

- Seven trust evaluation metrics for assessing AI agent behaviour.
- Weighted trust scoring and risk classification.
- Support for structured CSV and JSON log data.
- Streamlit dashboard for displaying evaluation results.
- Charts, log tables and downloadable CSV results.
- Aggregation scripts for summarising evaluation results.
- Metric definitions and supporting documentation.
- Automated tests for scoring and aggregation components.

### Project Structure

- **dashboard/** - Streamlit dashboard and its components.
- **Final Deliverables/Metric Definitions/** - Metric formulas, weights and thresholds.
- **Final Deliverables/Log schema/** - Run-log schema and example logs.
- **Final Deliverables/wp3_scoring_engine/** - Python scoring engine and automated tests.
- **Final Deliverables/wp3_aggregation_scripts/** - Aggregation scripts and automated tests.
- **Week 1–11 Deliverables/** - Weekly development work and supporting project files.

### Running the Dashboard

Install the required Python packages:

```bash
python -m pip install streamlit pandas plotly pyyaml
```

Open the dashboard folder and run:

```bash
cd dashboard
python -m streamlit run dashboard.py
```

The dashboard will normally open at `http://localhost:8501`.

Additional dependencies may be required depending on the dashboard implementation.

### Testing and Development Status

The project includes automated tests for the standalone scoring engine and aggregation scripts. These components support structured trust evaluation and reporting.

The scoring engine also supports a "not measured" result when insufficient data is available for a metric.

The remaining work includes completing integration between the dashboard and standalone scoring engine, validating the framework using real agent execution logs and finalising calibration and handover documentation.

### Technologies Used

- Python
- Streamlit
- Pandas
- Plotly
- YAML and JSON
- GitHub
- Jira

### Project Team

ICT Project B - Group P18

- Sandev Fernando
- Suhash Barani Prem
- Sam O'Connor
- Sebastian Haney
- Sahan Maduranga

### Academic Project

Developed for ICT30017 - ICT Project A and ICT30018 - ICT Project B at Swinburne University of Technology.
