# WP3 Trust Metrics Dashboard

A small Python web app that shows the WP3 trust metrics: the metric definitions and thresholds, the score
distribution of each metric, and the calibration results. It reads the files the WP3 pipeline already produces and
**does not rescore anything**.

There are two ways to run the same dashboard. Both read the same files, use the same code for every number and
chart (`wp3_dash/`), and show the same six pages:

| | Streamlit app | No-install launcher |
|---|---|---|
| Start with | `streamlit run streamlit_app.py` | `py dashboard.py` |
| Needs | `streamlit`, `pandas`, `PyYAML` | `PyYAML` only |
| Extras | sidebar file upload, sidebar filters, CSV download of the runs table | hover tooltips on charts, a static copy of every page (`--export`), runs with no internet |

Written for Python 3.9 or later (tested on 3.13). Install what you need with `py -m pip install -r requirements.txt`.

## 1. Run it

From this folder.

**Streamlit app**

```
py -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

Streamlit opens a browser tab (usually http://localhost:8501). The sidebar has the file settings, an upload box for a
scored file, the chart colour choice and the Agent / Workflow / Scenario type filters. With no changes it uses `input/`
when files are there and falls back to the bundled `examples/` (the 22-run WP3 test pack and its calibration results).
When it is showing the bundled examples, a notice at the top says so.

**No-install launcher**

```
py dashboard.py
```

A browser tab opens at http://127.0.0.1:8765. It chooses files the same way as the Streamlit app.

To show your own results with the launcher, either copy the files into `input/` (see `input/README.txt`) or point at them (the Streamlit app has the same three settings in its sidebar):

```
py dashboard.py --scored ..\wp3_scoring_engine\output\scored_runs.csv --calibration ..\wp3_calibration\results
```

| Option | Meaning |
|---|---|
| `--definitions FILE` | `metric_definitions.yaml` (default: the copy in this folder, identical to the engine's) |
| `--scored FILE` | `scored_runs.csv` or `scored_runs.json` from the scoring engine |
| `--calibration DIR` | the `results` folder of the calibration and validation package |
| `--label TEXT` | a line shown on every page saying what the data is |
| `--port N` / `--host H` | default `8765` on `127.0.0.1` (this computer only) |
| `--no-browser` | do not open a browser tab |
| `--export DIR` | write every page as a static HTML file into `DIR` and exit |

The files are read again on every page load, so after re-running the scoring engine you only reload the page.

## 2. What it reads

| Input | Used for |
|---|---|
| `metric_definitions.yaml` | metric names, formulas, weights, thresholds, risk bands, linked WP1 risks, edge cases, references |
| `scored_runs.csv` / `.json` | one row per run: the seven `<METRIC>_score` columns, the count fields, overall score and band, agent, workflow, scenario type |
| calibration `results/*.csv` | `calibration_results`, `threshold_sensitivity`, `band_and_weight_sensitivity`, `probe_findings`, `overall_agreement`, `platform_case_check`, `count_mismatches`, `run_record.json`. Any file that is missing hides its section. |

Runs whose status is not `completed` are left out, as in the scoring engine's output. A blank score means "not
measured" and is never shown as 0 or 1.

## 3. Pages

| Page | What it shows |
|---|---|
| Overview | scored runs, mean overall score and band, runs per risk band, mean score by agent / workflow / scenario type, share of runs meeting each threshold, agent-by-metric table |
| Metric definitions | all seven metrics with weight, threshold, formula and linked risks; weights chart; the overall-score formula, no-data rule and risk bands; which metrics speak to each WP1 threat |
| Score distributions | a histogram per metric (0.05-wide bars plus one bar for exactly 1.00) with the threshold marked, mean/median/pass rate, a table view of the same counts, and per-agent means. Each metric links to a detail page with its inputs, edge cases, per-agent and per-scenario breakdown, and the runs below threshold with the counts behind each score |
| Runs | every scored run, sortable, with a marker on scores below threshold |
| Calibration | agreement with hand-labelled ground truth, precision and recall per metric, confusion counts, threshold and weight sensitivity, probe findings (known false positives and negatives), the operating-system check |
| Data and checks | which files are loaded and whether they agree (section 4) |

The Overview, Score distributions, metric detail and Runs pages have Agent / Workflow / Scenario type filters.

In the Streamlit app the pages are tabs and the filters are in the sidebar. The detail view for a single metric is
the "Show details for" box at the bottom of the Score distributions tab. Charts there are shown as images, so they
have no hover tooltips; the same numbers are in the tables beside them.
Screenshots of every page are in `docs/screenshots/`; `docs/make_screenshots.py` regenerates them.

## 4. The data check

The Data and checks page recomputes every metric score from the count fields in the scored file, using the formulas in
`metric_definitions.yaml`, and recomputes each overall score from the weights. If the scored file and the definitions
disagree (for example the scored file was produced with different weights), a red notice appears on every page.
On the bundled examples 154 metric scores are checked and 0 differ. Two cells are left blank by the engine on purpose
because that run's scenario has no label (`label_source = heuristic`); the check lists them separately instead of
calling them differences.

## 5. Static copy

`py dashboard.py --export site` writes 13 HTML files (no server, no JavaScript apart from the theme button) that can
be opened from a folder, attached to a release or sent on. The static copy has no filters or sorting. The output is
identical on every run for the same inputs.

## 6. Tests

```
py -m unittest discover -s tests -t .
```

58 tests. 43 cover the data layer (loading CSV and JSON, formulas, bands, bins, filters, data checks, calibration
summaries), every launcher page (renders, well-formed HTML, numbers on the page, HTML escaping), the local server (all
routes, 404s, files re-read per request, a missing file gives a readable error), the static export (links resolve,
deterministic) and the command line. 15 cover the Streamlit front end: the tables and charts it shows (definitions
match the yaml, histogram counts equal the measured runs, below-threshold marks, calibration numbers, charts are
valid standalone SVG) and the app script itself, run against a stand-in for the `streamlit` module (see section 7).
The Streamlit tests are skipped if pandas is not installed.

## 7. Limits and honest notes

- **The Streamlit app has not been run in real Streamlit by its author.** It was written and tested in an
  environment where Streamlit could not be installed. Its tables and charts are tested directly, and the script was run
  against a stand-in `streamlit` module that records the calls it makes. That finds mistakes in this project's code;
  it cannot show that every call works in your Streamlit version (Streamlit's functions change between releases). Run
  `streamlit run streamlit_app.py`, click through the six tabs and compare them with the launcher's pages. If a Streamlit
  call fails in your version, the launcher shows the same content.
- **Plotly is not used.** Charts are drawn as SVG by `wp3_dash/charts.py` (shared by both front ends) and shown with
  `st.image`, so the Streamlit app does not depend on Plotly.
- **The Sprint 4-5 dashboard** (the older `dashboard.py` at the top of the repository, which scored raw logs itself)
  is superseded. This dashboard does not score anything: it shows what the scoring engine wrote.
- **Tested on Linux, Python 3.13.** The tests and screenshots were produced on Linux with headless Chromium. The code uses only
  portable calls and UTF-8 files, but it has not been run on Windows by the author of this package. The screenshots in
  `docs/screenshots/` are of the launcher's pages.
- **Local only.** The launcher listens on `127.0.0.1` by default, has no login and serves read-only pages. Do not expose it on a
  network without adding access control.
- **The calibration section describes the WP3 test pack and probes.** Showing it beside real WP4 results does not make
  those results calibrated; the page says "test pack" wherever the numbers come from it.
- **Colours** follow a colour-blind-checked palette; below-threshold results always carry a marker and text as well as
  colour. Dark mode follows the system setting or the Theme button.

## 8. Files

```
streamlit_app.py          Streamlit app (start here for Streamlit)
dashboard.py              no-install launcher (start here without Streamlit)
metric_definitions.yaml   single source of truth (same file as in the scoring engine)
requirements.txt          streamlit, pandas, PyYAML
wp3_dash/                 data.py (loading, checks, statistics), charts.py (SVG), frames.py (tables and charts for Streamlit),
                          render.py (launcher pages), app.py (launcher server, export)
tests/                    test_dashboard.py (43 tests), test_streamlit.py (15 tests)
examples/                 scored_runs.csv (22-run test pack) and calibration/ results
input/                    put your own files here
docs/screenshots/         one image per launcher page
docs/make_screenshots.py  regenerates the screenshots (needs Playwright; optional)
```
