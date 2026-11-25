# WP3 Calibration and Validation (v1.0.0)

The calibration and validation report for the WP3 evaluation framework (team P18, ICT30018), with the data and scripts behind it.

**The deliverable is two files:** `calibration_validation_report.md` (the report) and `results/calibration_results.csv` (per metric: confusion matrix at the threshold, precision, recall, score error). The other files let anyone check and rerun the work.

## What it shows

The WP3 scoring engine is run on two validation sets with hand-labelled ground truth, and its decisions are compared with the truth: a pack of 22 scorable runs (plus one timed-out run) across the four workflows, and 39 probe runs that each target one known weak point of one metric. The report also explains how the thresholds, weights and risk bands were chosen, tests how much they matter on the sample data, lists 17 known false positives and negatives (one found and fixed on WP4's real runs), and reports the results on WP4's real agent runs.

The validation sets are synthetic or hand-built. Section 8 of the report covers WP4's real agent runs.

## Run it

You need Python 3.10 or later and the scoring engine folder (`wp3_scoring_engine`) next to this one. Install the packages once with `py -m pip install -r requirements.txt` (on Mac or Linux use `python3`). Open a terminal inside this folder and run:

```
py run_calibration.py
py build_report.py
py -m unittest discover -s tests -t .
```

`run_calibration.py` scores both sets and writes `results/`. `build_report.py` rewrites the report from `results/` (and stops with a message if the results no longer match the findings the report describes). The tests should end with `OK`. The outputs are deterministic: a rerun gives identical files.

Options: `py run_calibration.py --engine <engine folder> --out <folder>`.

## Files

| File | What it is |
|---|---|
| `calibration_validation_report.md` | The report |
| `results/calibration_results.csv` | The main results table |
| `results/validation_run_detail.csv` | One row per run and metric: truth score, engine score, outcome |
| `results/count_mismatches.csv` | Every raw count where the engine differs from the truth |
| `results/probe_findings.csv` | One row per probe |
| `results/threshold_sensitivity.csv`, `results/band_and_weight_sensitivity.csv` | Sensitivity checks |
| `results/overall_agreement.csv` | Overall trust score and band, engine against truth (pack) |
| `results/platform_case_check.csv` | Windows against Linux/Mac matching of tool names |
| `results/run_record.json` | Versions and run inventory |
| `validation/pack/` | The 23 pack runs (three log files), their scenario lookup and the ground truth |
| `validation/probes/` | The 39 probe logs, their scenario lookup, ground truth and catalogue |
| `run_calibration.py`, `build_report.py` | The scripts that produce the results and the report |
| `make_probes.py`, `make_pack_truth.py` | Rebuild the probe set and the pack ground truth (the files are included; the labelling rules are in the header of `make_pack_truth.py`) |
| `tests/` | 17 automated tests |

## Using it on real logs

Section 10 of the report gives the steps: score WP4's runs, hand-label a sample in a copy of `validation/pack/ground_truth_pack.csv`, point `run_calibration.py` at it, and read the new false-positive and false-negative rows.
