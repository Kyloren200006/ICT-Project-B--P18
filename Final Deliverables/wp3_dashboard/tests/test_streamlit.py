"""Tests for the Streamlit front end.

Two layers:
  * wp3_dash/frames.py (tables and charts) is plain pandas and is tested directly.
  * streamlit_app.py is run against a small STAND-IN for the `streamlit` module (defined below). The stand-in
    records which calls the app makes and returns plausible values, so these tests catch typos, wrong
    names and crashes in this project's code on the bundled data. They do NOT prove that the app works with a
    particular Streamlit version: that has to be checked by running `streamlit run streamlit_app.py`.

Run:  py -m unittest discover -s tests -t .
"""
import os
import runpy
import sys
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

try:
    import pandas  # noqa: F401
    HAVE_PANDAS = True
except ImportError:  # pandas comes with Streamlit; the rest of the dashboard does not need it
    HAVE_PANDAS = False

if HAVE_PANDAS:
    from wp3_dash import data, frames

DEFS = os.path.join(ROOT, "metric_definitions.yaml")
SCORED = os.path.join(ROOT, "examples", "scored_runs.csv")
CAL = os.path.join(ROOT, "examples", "calibration")


class _Ctx:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeStreamlit(types.ModuleType):
    """Records calls; widgets return their default; layout calls return context managers."""

    def __init__(self, selections=None, text_values=None):
        super().__init__("streamlit")
        self.calls = []
        self.selections = selections or {}
        self.text_values = text_values or {}
        self.sidebar = _Ctx()

    def _rec(self, name, *a, **k):
        self.calls.append((name, a, k))

    def set_page_config(self, *a, **k):
        self._rec("set_page_config", *a, **k)

    def stop(self):
        raise SystemExit("st.stop() called")

    def tabs(self, labels):
        self._rec("tabs", labels)
        return [_Ctx() for _ in labels]

    def columns(self, spec, **k):
        n = spec if isinstance(spec, int) else len(spec)
        self._rec("columns", n)
        return [_Ctx() for _ in range(n)]

    def expander(self, *a, **k):
        self._rec("expander", *a)
        return _Ctx()

    def file_uploader(self, *a, **k):
        self._rec("file_uploader", *a)
        return None

    def text_input(self, label, value="", **k):
        self._rec("text_input", label)
        return self.text_values.get(label, value)

    def selectbox(self, label, options, **k):
        self._rec("selectbox", label, options)
        return self.selections.get(label, options[0])

    def radio(self, label, options, **k):
        self._rec("radio", label, options)
        return options[0]

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def call(*a, **k):
            self._rec(name, *a, **k)
        return call

    def names(self, name):
        return [c for c in self.calls if c[0] == name]


def run_app(fake):
    saved = sys.modules.get("streamlit")
    sys.modules["streamlit"] = fake
    try:
        runpy.run_path(os.path.join(ROOT, "streamlit_app.py"), run_name="__main__")
    finally:
        if saved is None:
            sys.modules.pop("streamlit", None)
        else:
            sys.modules["streamlit"] = saved


@unittest.skipUnless(HAVE_PANDAS, "pandas not installed")
class FramesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = data.build_context(DEFS, SCORED, CAL)
        cls.runs = cls.ctx.runs

    def test_definitions_table_matches_yaml(self):
        df = frames.definitions_frame(self.ctx)
        self.assertEqual(list(df["ID"]), self.ctx.defs.ids)
        self.assertEqual(len(df), 7)
        row = df[df["ID"] == "MI-001"].iloc[0]
        self.assertEqual(row["Weight"], "0.25")
        self.assertEqual(row["Threshold"], "1.00")

    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(m.weight for m in self.ctx.defs.metrics), 1.0, places=9)

    def test_distribution_counts_match_measured_runs(self):
        stats = frames.stats_for(self.ctx, self.runs)
        table = frames.hist_table(self.ctx, stats)
        for m in self.ctx.defs.metrics:
            measured = sum(1 for r in self.runs if r.scores.get(m.id) is not None)
            self.assertEqual(int(table[m.id].sum()), measured, m.id)
            self.assertEqual(stats[m.id].n_measured, measured)

    def test_runs_table_marks_below_threshold_and_not_measured(self):
        df = frames.runs_frame(self.ctx, self.runs)
        self.assertEqual(len(df), len(self.runs))
        for r, (_, row) in zip(self.runs, df.iterrows()):
            for m in self.ctx.defs.metrics:
                s = r.scores.get(m.id)
                cell = row[m.id]
                if s is None:
                    self.assertEqual(cell, frames.DASH)
                elif s < m.threshold - 1e-9:
                    self.assertTrue(cell.endswith(" x"), (r.run_id, m.id, cell))
                else:
                    self.assertFalse(cell.endswith(" x"))

    def test_scores_are_read_not_recomputed(self):
        r = self.runs[0]
        df = frames.runs_frame(self.ctx, [r])
        self.assertEqual(df.iloc[0]["Overall"], "%.3f" % r.overall)

    def test_calibration_frames(self):
        cal = self.ctx.calibration
        conf = frames.cal_confusion_frame(cal)
        self.assertGreater(len(conf), 0)
        self.assertEqual(int(conf[conf["Data"] == "pack"]["TP"].astype(int).sum()), 21)
        tiles = frames.cal_tiles(cal)
        self.assertEqual(len(tiles), 4)
        self.assertEqual(tiles[0][1], "88 of 90")
        for fn in (frames.cal_bands_frame, frames.cal_probes_frame, frames.cal_platform_frame,
                   frames.cal_mismatch_frame, frames.cal_agreement_frame):
            self.assertGreater(len(fn(cal)), 0, fn.__name__)
        self.assertGreater(len(frames.cal_threshold_frame(self.ctx, cal)), 0)

    def test_checks_pass_on_bundled_data(self):
        self.assertTrue(frames.checks_ok(self.ctx))
        df = frames.checks_frame(self.ctx)
        self.assertEqual(len(df), 4)

    def test_svg_for_streamlit_starts_with_svg_and_is_self_contained(self):
        stats = frames.stats_for(self.ctx, self.runs)
        m = self.ctx.defs.metrics[0]
        for theme in ("light", "dark"):
            svg = frames.svg_for_streamlit(frames.hist_svg(m, stats[m.id]), theme)
            self.assertTrue(svg.startswith("<svg"))
            self.assertIn("<style>", svg)
            self.assertIn("xmlns=", svg)
            self.assertNotIn("<?xml", svg)

    def test_default_paths_fall_back_to_examples_and_say_so(self):
        d, s, c, label = frames.default_paths(ROOT)
        if not os.path.exists(os.path.join(ROOT, "input", "scored_runs.csv")):
            self.assertTrue(s.endswith(os.path.join("examples", "scored_runs.csv")))
            self.assertIn("test pack", label)
        self.assertTrue(os.path.isfile(d))

    def test_empty_calibration_gives_empty_frames(self):
        ctx = data.build_context(DEFS, SCORED, os.path.join(ROOT, "does-not-exist"))
        self.assertEqual(frames.cal_tiles(ctx.calibration), [])
        self.assertEqual(len(frames.cal_confusion_frame(ctx.calibration)), 0)


@unittest.skipUnless(HAVE_PANDAS, "pandas not installed")
class AppWithStandInTests(unittest.TestCase):
    def test_app_runs_on_bundled_data(self):
        fake = FakeStreamlit()
        run_app(fake)
        tabs = fake.names("tabs")
        self.assertEqual(len(tabs), 1)
        self.assertEqual(tabs[0][1][0], ["Overview", "Metric definitions", "Score distributions", "Runs",
                                         "Calibration", "Data and checks"])
        # charts: overview 5, definitions 1, distributions 7 + 1 detail panel, calibration 2
        self.assertEqual(len(fake.names("image")), 16)
        self.assertGreater(len(fake.names("dataframe")), 15)   # tables
        self.assertEqual(fake.names("error"), [])
        self.assertTrue(fake.names("info"))                    # "bundled example data" notice
        for _, a, _ in fake.names("image"):
            self.assertTrue(a[0].startswith("<svg"))

    def test_app_with_filter_selected(self):
        fake = FakeStreamlit(selections={"Agent": "Agent_A_Baseline"})
        run_app(fake)
        self.assertEqual(fake.names("error"), [])
        n_rows = [len(a[0]) for n, a, _ in fake.calls if n == "dataframe" and "Run" in a[0].columns
                  and "Overall" in a[0].columns]
        self.assertTrue(n_rows)
        self.assertLess(n_rows[0], 22)

    def test_app_with_missing_calibration_folder(self):
        fake = FakeStreamlit(text_values={"Calibration results folder": os.path.join(ROOT, "nowhere")})
        run_app(fake)
        self.assertEqual(fake.names("error"), [])
        self.assertTrue(any("No calibration files" in str(a[0]) for _, a, _ in fake.names("warning")))

    def test_missing_scored_file_stops_with_message(self):
        fake = FakeStreamlit(text_values={"Scored runs file": os.path.join(ROOT, "missing.csv")})
        with self.assertRaises(SystemExit):
            run_app(fake)
        self.assertTrue(any("Cannot find" in str(a[0]) for _, a, _ in fake.names("error")))

    def test_md_escape(self):
        fake = FakeStreamlit()
        saved = sys.modules.get("streamlit")
        sys.modules["streamlit"] = fake
        try:
            ns = runpy.run_path(os.path.join(ROOT, "streamlit_app.py"), run_name="not_main")
        finally:
            if saved is None:
                sys.modules.pop("streamlit", None)
            else:
                sys.modules["streamlit"] = saved
        self.assertEqual(ns["md"]("a*b_c $x$ [l]"), "a\\*b\\_c \\$x\\$ \\[l\\]")


if __name__ == "__main__":
    unittest.main()
