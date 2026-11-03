#!/usr/bin/env python3
"""WP3 Trust Metrics Dashboard (Streamlit).

Run from this folder:

    streamlit run streamlit_app.py

It reads three things and rescores nothing:
  * metric_definitions.yaml   metric definitions, weights, thresholds, risk bands, formulas, linked risks
  * scored_runs.csv / .json   the scoring engine's output, one row per run
  * the calibration results   the results folder written by the calibration and validation package

With nothing set it uses ./input/ when files are there and falls back to the bundled ./examples/ (the 22-run
WP3 test pack and its calibration results); every page says so while it is showing the bundled examples.
Use the sidebar to point at other files or to upload a scored file.

All tables and charts are built in wp3_dash/frames.py from the same code as the no-install launcher
(dashboard.py), so both show the same numbers. See README.md.
"""
import os
import re
import sys
import tempfile

import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from wp3_dash import data, frames  # noqa: E402

TITLE = "WP3 Trust Metrics Dashboard"
ALL = "All"


# ----------------------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------------------
def md(text):
    """Escape characters Streamlit's markdown would act on (emphasis, links, code, LaTeX) in text from the data files."""
    return re.sub(r"([\\`*_{}\[\]<>~$|])", r"\\\1", str(text))


def show_table(df, empty="Nothing to show."):
    if df is None or len(df) == 0:
        st.caption(empty)
    else:
        st.dataframe(df, hide_index=True)


def show_chart(svg, theme):
    st.image(frames.svg_for_streamlit(svg, theme))


def save_upload(uploaded):
    """Write an uploaded file to a fixed temp location and return its path (overwritten on every rerun)."""
    folder = os.path.join(tempfile.gettempdir(), "wp3_dashboard_uploads")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, os.path.basename(uploaded.name))
    with open(path, "wb") as fh:
        fh.write(uploaded.getvalue())
    return path


# ----------------------------------------------------------------------------------------
# sidebar: where the data comes from
# ----------------------------------------------------------------------------------------
def sidebar_inputs():
    d0, s0, c0, label0 = frames.default_paths(HERE)
    with st.sidebar:
        st.header("Data")
        st.caption("Files are read again on every run, so after re-running the scoring engine just reload the page.")
        up_scored = st.file_uploader("Upload a scored file (scored_runs.csv or .json)", type=["csv", "json"])
        up_defs = st.file_uploader("Upload metric_definitions.yaml (optional)", type=["yaml", "yml"])
        defs_path = st.text_input("Metric definitions file", value=d0)
        scored_path = st.text_input("Scored runs file", value=s0)
        cal_dir = st.text_input("Calibration results folder", value=c0)
        theme = st.radio("Chart colours", ["light", "dark"], horizontal=True)
    label = label0
    if up_scored is not None:
        scored_path = save_upload(up_scored)
        label = "uploaded file: %s" % up_scored.name
    elif scored_path != s0:
        label = ""
    if up_defs is not None:
        defs_path = save_upload(up_defs)
    return defs_path, scored_path, cal_dir, label, theme


def load_context(defs_path, scored_path, cal_dir, label):
    for what, path in (("metric definitions", defs_path), ("scored runs", scored_path)):
        if not os.path.isfile(path):
            st.error("Cannot find the %s file: %s" % (what, path))
            st.stop()
    try:
        return data.build_context(defs_path, scored_path, cal_dir, label)
    except Exception as exc:  # a bad file should give a message, not a stack trace
        st.error("Could not read the input files: %s: %s" % (type(exc).__name__, exc))
        st.stop()


def sidebar_filters(ctx):
    opts = data.filter_options(ctx.runs)
    with st.sidebar:
        st.header("Filters")
        agent = st.selectbox("Agent", [ALL] + opts["agent"])
        workflow = st.selectbox("Workflow", [ALL] + opts["workflow"])
        stype = st.selectbox("Scenario type", [ALL] + opts["type"])
    f = data.Filters(agent="" if agent == ALL else agent, workflow="" if workflow == ALL else workflow,
                     scenario_type="" if stype == ALL else stype)
    return f, data.apply_filters(ctx.runs, f)


def notices(ctx):
    if ctx.label:
        st.info("Data shown: " + ctx.label)
    for w in ctx.warnings:
        st.error(w)
    ck = ctx.checks
    if ck.get("score_cells_mismatch") or ck.get("overall_mismatch"):
        st.error("Data check failed: %d score cell(s) and %d overall score(s) in the scored file differ from a "
                 "recomputation using the definitions file. See the Data and checks tab."
                 % (ck["score_cells_mismatch"], ck["overall_mismatch"]))


# ----------------------------------------------------------------------------------------
# tabs
# ----------------------------------------------------------------------------------------
def tab_overview(ctx, runs, theme):
    if not runs:
        st.warning("No runs match these filters.")
        return
    n = frames.overview_numbers(ctx, runs)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Scored runs", n["runs"])
        st.caption("%d agent configuration%s" % (n["agents"], "" if n["agents"] == 1 else "s"))
    with c2:
        st.metric("Mean overall trust score", frames.fmt(n["mean_overall"], 3))
        st.caption("Band: " + n["mean_band"])
    with c3:
        st.metric("Lowest run", frames.fmt(n["lowest"], 3))
        st.caption(n["lowest_run"])
    with c4:
        st.metric("Metric results below threshold", "%d of %d" % (n["below"], n["cells"]))
        st.caption("measured results only; not-measured results are left out")

    left, right = st.columns(2)
    with left:
        st.subheader("Runs by risk band")
        show_chart(frames.bands_svg(ctx, runs), theme)
        show_table(frames.band_counts_frame(ctx, runs))
    with right:
        st.subheader("Mean overall trust score by agent")
        show_chart(frames.means_svg(data.group_means(runs, "agent"), "Mean overall trust score by agent"), theme)
    left, right = st.columns(2)
    with left:
        st.subheader("By workflow")
        show_chart(frames.means_svg(data.group_means(runs, "workflow"), "By workflow"), theme)
    with right:
        st.subheader("By scenario type")
        show_chart(frames.means_svg(data.group_means(runs, "scenario_type"), "By scenario type"), theme)
    st.subheader("Share of runs meeting each metric's threshold")
    st.caption("Only runs where the metric was measured.")
    show_chart(frames.pass_rate_svg(ctx, runs), theme)
    st.subheader("Agent summary")
    st.caption("Mean metric score per agent. A dash means the metric was not measured in any of that agent's runs.")
    show_table(frames.agent_frame(ctx, runs))


def tab_definitions(ctx, theme):
    defs = ctx.defs
    st.caption("Read from %s (version %s, %s). Weights, thresholds, bands, formulas and linked risks all come from "
               "that file; change a value there and this tab and the scoring engine follow."
               % (os.path.basename(defs.path), defs.version, defs.status))
    show_table(frames.definitions_frame(ctx))
    left, right = st.columns(2)
    with left:
        st.subheader("Weights in the overall score")
        st.caption("Weights of the measured metrics are rescaled to sum to 1 for each run.")
        show_chart(frames.weights_svg(ctx), theme)
    with right:
        st.subheader("Overall score")
        st.code(defs.overall_formula or "-", language=None)
        st.markdown("**No-data rule:** " + md(defs.no_data_behaviour or "-"))
        st.subheader("Risk bands")
        show_table(frames.bands_frame(ctx))
        if defs.band_status:
            st.caption(md(defs.band_status))
    st.subheader("Linked WP1 threats")
    st.caption("Which metrics speak to each WP1 threat category.")
    show_table(frames.risk_frame(ctx))
    if defs.change_control:
        st.subheader("Change control")
        for c in defs.change_control:
            st.markdown("- " + md(c))


def metric_panel(ctx, runs, m, theme):
    pairs, m = frames.metric_detail(ctx, m.id)
    left, right = st.columns(2)
    with left:
        st.subheader("%s: %s" % (m.id, m.name))
        for k, v in pairs:
            st.markdown("**%s:** %s" % (k, md(v)))
        if m.inputs:
            st.markdown("**Inputs**")
            for k, v in m.inputs.items():
                st.markdown("- `%s`: %s" % (k, md(v)))
        for title, items in (("Edge cases", m.edge_cases), ("Run-log sources", m.run_log_sources),
                             ("References", m.references)):
            if items:
                st.markdown("**%s**" % title)
                for it in items:
                    st.markdown("- " + md(it))
    with right:
        s = data.metric_stats(m, runs)
        st.subheader("Score distribution")
        if s.n_measured:
            show_chart(frames.hist_svg(m, s, 420, 190), theme)
        else:
            st.caption("Not measured in any of these runs.")
        st.caption("%d measured, %d not measured; mean %s, median %s, min %s; %s meet the threshold." % (
            s.n_measured, s.n_not_measured, frames.fmt(s.mean), frames.fmt(s.median), frames.fmt(s.minimum),
            frames.pct(s.pass_rate)))
    st.subheader("By agent")
    show_table(frames.by_agent_frame(m, runs))
    st.subheader("By scenario")
    show_table(frames.by_scenario_frame(m, runs))
    below = frames.below_frame(m, runs)
    st.subheader("Runs below threshold (%d)" % len(below))
    show_table(below, "No measured run is below the threshold.")


def tab_distributions(ctx, runs, theme):
    if not runs:
        st.warning("No runs match these filters.")
        return
    stats = frames.stats_for(ctx, runs)
    st.caption("Each bar counts runs whose score falls in a 0.05 band; the last bar is runs scoring exactly 1.00. "
               "Blue meets the metric's threshold, red is below it, and the dashed line marks the threshold. "
               "Runs where a metric was not measured are not in the chart.")
    metrics = ctx.defs.metrics
    for row_start in range(0, len(metrics), 3):
        cols = st.columns(3)
        for col, m in zip(cols, metrics[row_start:row_start + 3]):
            with col:
                st.markdown("**%s: %s**" % (m.id, m.name))
                st.caption("weight %s, threshold %s" % (frames.fmt(m.weight), m.threshold_rule or frames.fmt(m.threshold)))
                s = stats[m.id]
                if s.n_measured:
                    show_chart(frames.hist_svg(m, s), theme)
                else:
                    st.caption("Not measured in any of these runs.")
                st.caption("%d measured, %d not measured; mean %s, median %s; %s meet threshold" % (
                    s.n_measured, s.n_not_measured, frames.fmt(s.mean), frames.fmt(s.median), frames.pct(s.pass_rate)))
    st.subheader("Summary per metric")
    show_table(frames.stats_frame(ctx, stats))
    st.subheader("Mean score per agent and metric")
    show_table(frames.agent_frame(ctx, runs))
    with st.expander("Table view of the histograms"):
        show_table(frames.hist_table(ctx, stats))
    st.subheader("Metric details")
    ids = [m.id for m in metrics]
    chosen = st.selectbox("Show details for", ids, key="metric_detail_pick")
    metric_panel(ctx, runs, ctx.defs.metric(chosen), theme)


def tab_runs(ctx, runs):
    st.caption("One row per scored run. An x after a score marks it below that metric's threshold; a dash means not "
               "measured. Click a column heading to sort.")
    df = frames.runs_frame(ctx, runs)
    st.write("%d run%s" % (len(df), "" if len(df) == 1 else "s"))
    show_table(df, "No runs match these filters.")
    if len(df):
        st.download_button("Download this table (CSV)", df.to_csv(index=False).encode("utf-8"),
                           file_name="runs_table.csv", mime="text/csv")


def tab_calibration(ctx, theme):
    cal = ctx.calibration
    if not cal.get("found"):
        st.warning("No calibration files were found in %s. Set the calibration results folder in the sidebar to the "
                   "results folder of the calibration package." % (cal.get("dir") or ""))
        return
    st.caption("How the scoring engine's output compares with hand-labelled ground truth on the test pack and on "
               "targeted probes. A flag means a metric score below its threshold. Read together with the calibration "
               "and validation report.")
    tiles = frames.cal_tiles(cal)
    if tiles:
        cols = st.columns(len(tiles))
        for col, (label, value, note) in zip(cols, tiles):
            with col:
                st.metric(label, value)
                st.caption(note)
    if cal.get("results"):
        left, right = st.columns(2)
        with left:
            st.subheader("Precision per metric")
            st.caption("Of the runs the engine flagged, the share that really should be flagged. Blue: test pack, orange: probes.")
            show_chart(frames.cal_pr_svg(ctx, cal, "precision"), theme)
        with right:
            st.subheader("Recall per metric")
            st.caption("Of the runs that should be flagged, the share the engine flagged. Blue: test pack, orange: probes.")
            show_chart(frames.cal_pr_svg(ctx, cal, "recall"), theme)
        st.subheader("Confusion counts per metric")
        st.caption("TP = both flag, FP = engine flags only, FN = hand label flags only, TN = neither. 'Engine extra' = "
                   "engine measured where the hand label did not.")
        show_table(frames.cal_confusion_frame(cal))
    if cal.get("thresholds"):
        st.subheader("Threshold sensitivity")
        st.caption("Share of measured test-pack runs passing at nearby thresholds. The last column is the most runs "
                   "whose pass/fail decision changes at any tested threshold.")
        show_table(frames.cal_threshold_frame(ctx, cal))
    if cal.get("bands"):
        st.subheader("Band edge and weight sensitivity")
        show_table(frames.cal_bands_frame(cal))
    if cal.get("probes"):
        st.subheader("Probe findings (known false positives and false negatives)")
        st.caption("Each probe is a run built to exercise one weak point of the rule-based extraction. 'x differs' marks "
                   "runs where the engine reaches a different trust decision from the hand label.")
        show_table(frames.cal_probes_frame(cal))
    if cal.get("platform"):
        st.subheader("Operating-system check")
        st.caption("The same run scored under Linux/macOS rules and Windows rules (known finding F-16 in the validation report).")
        show_table(frames.cal_platform_frame(cal))
    if cal.get("mismatches"):
        st.subheader("Count mismatches (engine vs hand label)")
        show_table(frames.cal_mismatch_frame(cal))
    if cal.get("agreement"):
        with st.expander("Overall score agreement, run by run (%d runs)" % len(cal["agreement"])):
            show_table(frames.cal_agreement_frame(cal))
    if cal.get("missing"):
        st.caption("Not found in the calibration folder (sections hidden): " + ", ".join(cal["missing"]))


def tab_data(ctx):
    st.caption("What this dashboard is showing, and whether the files agree with each other.")
    if frames.checks_ok(ctx) and ctx.checks.get("counts_present"):
        st.success("Data checks passed. Every score in the scored file matches a recomputation from its counts using "
                   "the formulas in the definitions file.")
    elif frames.checks_ok(ctx):
        st.info("Count fields not present or checks incomplete. See below.")
    else:
        st.error("Data checks found differences. " + " | ".join(ctx.checks.get("examples", [])))
    show_table(frames.inputs_frame(ctx))
    st.subheader("Checks")
    show_table(frames.checks_frame(ctx))
    st.subheader("How to refresh")
    st.markdown("Re-run the scoring engine, then reload this page: the files are read on every run. Use the sidebar to "
                "point at other files.")


# ----------------------------------------------------------------------------------------
def main():
    st.set_page_config(page_title=TITLE, layout="wide")
    st.title(TITLE)
    defs_path, scored_path, cal_dir, label, theme = sidebar_inputs()
    ctx = load_context(defs_path, scored_path, cal_dir, label)
    st.caption("Metric definitions v%s (%s), %d scored run%s. Scores are read as written by the scoring engine; this "
               "dashboard does not rescore." % (ctx.defs.version, ctx.defs.status, len(ctx.runs),
                                                "" if len(ctx.runs) == 1 else "s"))
    notices(ctx)
    _, runs = sidebar_filters(ctx)
    t_over, t_defs, t_dist, t_runs, t_cal, t_data = st.tabs(
        ["Overview", "Metric definitions", "Score distributions", "Runs", "Calibration", "Data and checks"])
    with t_over:
        tab_overview(ctx, runs, theme)
    with t_defs:
        tab_definitions(ctx, theme)
    with t_dist:
        tab_distributions(ctx, runs, theme)
    with t_runs:
        tab_runs(ctx, runs)
    with t_cal:
        tab_calibration(ctx, theme)
    with t_data:
        tab_data(ctx)


if __name__ == "__main__":
    main()
