# 12. Future work

The steps below are concrete and ordered by what they unlock.

1. **Score further WP4 runs** (section 10.4) as they arrive, after completing their scenarios' lookup rows from WP2's failure criteria, and add them to the evaluation reports.
2. **Calibrate on real logs** following the five steps of the calibration report: at least 30 hand-labelled runs per workflow including every failing run, then the threshold and band sweeps on real scores. Change a threshold only if runs cluster near it and the ground truth shows runs just below are acceptable or just above are not; record the change and bump the version.
3. **Decide on the v1.1 engine candidates**, in the order of benefit: `fnmatch.fnmatchcase` everywhere (F-16, one line); normalising paths before the folder check (F-12); whole-word matching of short sensitive items (F-02); counting a flagged tool-stage filter event as detected in ETL-001, as the definition says (F-04); a scope-aware rule for EA-001 (F-10); and checking who introduced an item in MI-001 so that a user re-typing an ID is not a leak (F-14). Each is a change to code or to `detection_rules.yaml`, to be validated with the same probes, which already encode the cases.
4. **Complete the labels.** WP2's scenario labels should carry aliases for sensitive items, complete disallowed-tool and forbidden-marker lists, and cross-session items, which removes most of the false negatives that the probes found (F-01, F-06, F-09, F-15).
5. **An optional second-opinion judge.** If real logs show many paraphrased leaks that the rules miss, add a language-model judge as a flag for human review on the cases the rules cannot decide, with the model, version, prompt, settings and parsing documented and validated, never as the source of the headline score.
6. **Retake the section 9 screenshots from the Streamlit app.**
7. **Confidence intervals.** When repeated runs of a scenario give different scores, report the standard deviation across repeats (already computed per group) and add an interval for the group mean.
