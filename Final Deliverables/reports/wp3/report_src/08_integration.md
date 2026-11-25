# 8. Integration with other WPs

WP3 sits between WP2 and WP4: it takes WP2's scenario labels and WP4's run logs and returns scores. It takes WP1's threat IDs as its risk vocabulary and hands WP1 and WP2 a coverage view of which metrics measure which threats. {{ref:integration}} lists what was consumed and handed over, with the shared IDs. The statuses are as of 23 November 2026.

{{tcap:integration|What WP3 consumed from and handed to each work package, with the shared identifiers. Source: wp3_scoring_engine/README.md, wp3_scoring_engine/metric_definitions.yaml and wp3_calibration/calibration_validation_report.md section 8.}}

{{table:integration}}

**Shared IDs.** The risk IDs in `metric_definitions.yaml` are WP1's threat IDs TC1 to TC6, taken from WP1's threat taxonomy as communicated to WP3 on 29 October 2026. The scenario IDs in a log must equal the `scenario_id` in WP2's labels exactly; a mismatch makes every label-based metric "not measured" for that run, which the `metrics_not_measured` column and the inventory make visible. The agent configuration names in a log (`agent.agent_config`) are WP4's; the engine and the aggregation scripts carry them through unchanged and group by agent configuration, model and mitigation. The metric IDs (DM-001 and so on) are WP3's and are used identically in the engine, the aggregation scripts, the dashboard and this report.

The client's guide writes risk IDs in the form R-…, and WP1's taxonomy uses TC1 to TC6. If WP1's final published taxonomy uses different identifiers, the change is made in the `risk_ids` fields of `metric_definitions.yaml` and in the scenario lookup, with no code change, and the version of the definitions is bumped ({{ref:risk_matrix}} shows the current mapping). The same file holds the change control note.

**Evaluation reports.** WP4's {{val:wp4_runs}} runs arrived in schema v0.1 and all passed it. WP3 scored every completed run and delivered the evaluation reports in `Evaluation Reports/` (section 7.8). WP4 ran two of WP2's scenarios, so WP3 completed the lookup rows for those two from WP2's failure criteria; the rest of WP2's suite has no runs and most of its labels are still in prose. If WP4 runs further scenarios, the same steps (section 10.4) score them once their lookup rows are filled in.
