# WP3 Final Deliverables: Evaluation Framework and Metrics (v1.0.0)

Project P18, Benchmarking Trust: Evaluating Privacy and Security Risks in Agentic AI Systems (ICT30018, Swinburne University of Technology).

WP3 turns what an AI agent did into trust scores. WP4 runs the agents on WP2's scenarios and records each run as a log; the WP3 scoring engine reads those logs, checks them against the scenario labels and scores every run on seven trust metrics, an overall trust score and a risk band.

## What is in this folder

| Folder | Deliverable | Start with |
|---|---|---|
| `Metric Definitions/` | The seven metrics: formula, inputs, range, direction, threshold, weight and linked WP1 threat IDs | `metric_definitions.md` |
| `Log schema/` | The run-log format agents must produce, with an example log | `log_schema.md` |
| `wp3_scoring_engine/` | Scoring engine: scores run logs. Holds WP4's November 2026 logs and their scenario lookup | `README.md` |
| `wp3_aggregation_scripts/` | Summaries per agent, workflow, risk and scenario | `README.md` |
| `wp3_calibration/` | Calibration and validation report, with its data and scripts | `calibration_validation_report.md` |
| `Evaluation Reports/` | Scores for all of WP4's runs, the summaries and the written evaluation report | `evaluation_report.md` |
| `wp3_dashboard/` | Metrics dashboard (Streamlit, or a no-install version) | `README.md` |
| `reports/wp3/` | WP3 technical report | `report.docx` |

## Requirements

Python 3.10 or later. The commands below use `py` (Windows); on Mac or Linux use `python3`. Open a terminal in this folder (in VS Code: File > Open Folder, then Terminal > New Terminal).

Install the packages once:

```
cd wp3_scoring_engine;      py -m pip install -r requirements.txt; cd ..
cd wp3_aggregation_scripts; py -m pip install -r requirements.txt; cd ..
cd wp3_calibration;         py -m pip install -r requirements.txt; cd ..
cd wp3_dashboard;           py -m pip install -r requirements.txt; cd ..
```

## Run everything

**1. Check it works (optional).** Each should end with `OK` (152 tests in total):

```
cd wp3_scoring_engine;      py -m unittest discover -s tests -t . ; cd ..
cd wp3_aggregation_scripts; py -m unittest discover -s tests -t . ; cd ..
cd wp3_calibration;         py -m unittest discover -s tests -t . ; cd ..
cd wp3_dashboard;           py -m unittest discover -s tests -t . ; cd ..
```

**2. Score the run logs.** Reads `input/logs/` and `input/scenarios/scenario_lookup.csv`, writes `output/`:

```
cd wp3_scoring_engine
py score_logs.py
cd ..
```

On the delivered files this prints 48 runs scored and 8 excluded (failed runs), mean 1.000 (Trusted).

**3. Make the summaries:**

```
cd wp3_aggregation_scripts
py aggregate_summaries.py ..\wp3_scoring_engine\output\scored_runs.csv --scenarios ..\wp3_scoring_engine\input\scenarios\scenario_lookup.csv --out output
cd ..
```

**4. Open the dashboard:**

```
cd wp3_dashboard
py -m streamlit run streamlit_app.py
```

In the browser, use "Upload a scored file" in the sidebar and choose `wp3_scoring_engine\output\scored_runs.csv`. Without Streamlit, `py dashboard.py --scored ..\wp3_scoring_engine\output\scored_runs.csv` shows the same pages. Stop either with Ctrl + C in the terminal.

**5. Re-run the calibration (optional):**

```
cd wp3_calibration
py run_calibration.py
py build_report.py
cd ..
```

All outputs are deterministic: the same inputs always give identical files, on Windows, Mac and Linux.

## Scoring new runs

1. Put the new run logs (`.json` or `.jsonl`, in the format in `Log schema/`) in `wp3_scoring_engine/input/logs/`.
2. Make sure every scenario they use has a row in `wp3_scoring_engine/input/scenarios/scenario_lookup.csv`, with its sensitive items and forbidden markers filled in from WP2's failure criteria (column guide in `wp3_scoring_engine/README.md`, section 5).
3. Run steps 2 to 4 above.

## Where to read more

- How each part works and every option: the `README.md` in each folder.
- Method, implementation, validation and limitations: `reports/wp3/report.docx`.
- Results on WP4's runs: `Evaluation Reports/evaluation_report.md`.
