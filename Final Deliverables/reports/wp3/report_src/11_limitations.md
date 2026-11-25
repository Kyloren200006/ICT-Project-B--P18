# 11. Limitations and threats to validity

**Validation data is mostly synthetic.** Every log in the pack and the probes was written for the test. The results show that the engine reads logs correctly and where its rules fail on known tricky cases. The test-pack scores (0.68 and 1.00 for the two configurations) come from the way the pack was built.

**Narrow real-run coverage.** WP4's real runs cover two adversarial email scenarios and two working models. Every run scored 1.0, so they confirm the extraction rules on real output but cannot rank agents, show the mitigation's effect, or tell whether the thresholds are well placed. No benign scenario and no scheduling, web or file-handling scenario has been run.

**Small, uneven samples.** 22 runs and 39 probes, with 2 to 6 cells for MI-001, PIR-001 and ETL-001 on the pack. The rates are counts of cases, not estimates with confidence intervals.

**The probes are not representative.** They were built to find mistakes, so their error rate describes weak points and must not be quoted as accuracy.

**Weights, thresholds and bands are design values.** They follow the severity of each risk and were not derived from data. The data cannot test them (section 7.6). Different reasonable choices would give different bands for runs near an edge, although not a different ranking of the two test agents.

**The overall score can hide a single-metric failure.** The worked example shows a run that is Trusted overall with a Data Minimisation score below its own threshold (section 6.3). Reports should show per-metric scores and the number of runs below each threshold beside any band.

**The engine can only judge against its labels.** Missing aliases, incomplete disallowed-tool lists or too-short sensitive items in WP2's labels show up as engine errors (F-01, F-02, F-06, F-09). A metric without labels is "not measured", and the share of not-measured results should be reported with every score.

**Rule-based detection does not read meaning.** Paraphrased leaks and partial leaks are missed (F-01, F-15); a short item can match inside another word (F-02); a safe agent that quotes an attacker's address while reporting an attack is scored as hijacked (F-05); Excessive Agency does not see scope (F-10) or user approval (F-11); a path that climbs out of an allowed folder passes (F-12); and a read through a tool name not in the list is not counted (F-13). Each has a stated handling, and the candidate fixes are in section 12.

**Dependence on the log.** ETL-001 relies on the log's `external` flag (F-03) and DM-001 on the tool-name list (F-13). The score is only as accurate as WP4's adapters' logging; an adapter that mislabels external calls produces a wrong ETL-001. PIR-001 and TC5: PIR-001 sees what an agent did with injected instructions in retrieved content, and cannot see poisoning of weights or training data.

**Failed runs are excluded.** A run that timed out or errored is listed but not scored, so an agent that crashes more often is not penalised in the trust score. The number of excluded runs per agent should be reported beside it.

**Equal weighting of runs.** The aggregation weighs every run equally, so a scenario that was run more times counts more in a group mean. This matters if WP4's repeat counts differ between scenarios.

**Windows case rules are emulated in the calibration.** The platform check applies Windows' case rules in code (`ntpath.normcase`). Separately, the team ran all four test suites, the scoring of WP4's runs, the aggregation and the calibration on Windows with Python 3.14, and every output was byte-identical to the Linux files. That check found two differences, both fixed before release: JSON and report files were written with Windows line endings, and file paths in the outputs used backslashes; both are now written the same on every system. The Streamlit app's automated tests run against a stand-in for the `streamlit` module (section 7.7); the team has run the app itself in Streamlit on Windows. The dashboard screenshots were taken on Linux and are of the launcher, not of the Streamlit app.

**Labels for the rest of WP2's suite.** Only the two scenarios WP4 ran have complete lookup rows. Scenarios without labels are scored on injection phrases and memory only (F-08), so further runs need their rows completed first. The schema is version 0.1; WP4's runs match it.

**Failed approaches and abandoned choices.** Scoring a metric with no data as 1.0 was abandoned because it rewards uninformative runs. Scoring from hand-built count files was abandoned because it cannot test extraction. The Week 3 five-metric definitions and the Week 9 `schemascore_v2.yaml`, whose weights drifted out of sync with the dashboard, were replaced by one definitions file. A language-model judge and fuzzy matching were considered and not built (section 4.2). Streamlit and Plotly for the dashboard were not tried. The validation also produced negative results that are reported rather than removed: the engine's recall on Excessive Agency is 0.50 on the pack, and on the probes it agreed with the hand labels on 22 of 39.
