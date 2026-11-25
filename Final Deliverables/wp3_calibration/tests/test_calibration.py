"""Tests for the calibration and validation scripts. Run from this folder:

    py -m unittest discover -s tests -t .

The tests that score logs need the WP3 scoring engine next to this folder (or set WP3_ENGINE to its path).
"""
import csv
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
ENGINE = pathlib.Path(os.environ.get("WP3_ENGINE", ROOT.parent / "wp3_scoring_engine"))
HAVE_ENGINE = (ENGINE / "wp3_eval").is_dir()
FIELDS = ["total_accesses", "unnecessary_accesses", "total_injection_attempts", "detected_injections", "total_actions",
          "unsafe_executions", "total_sensitive_tokens", "leaked_sensitive_tokens", "total_session_transitions",
          "leaked_sessions", "unauthorized_actions", "unnecessary_actions", "total_leakage_events", "detected_leakage_events"]
METRICS = {"DM-001", "PIR-001", "UAE-001", "SIL-001", "MI-001", "EA-001", "ETL-001"}


def rd(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def digest(folder):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(pathlib.Path(folder).iterdir()) if p.is_file()}


def run(*args, cwd=ROOT):
    return subprocess.run([sys.executable, *args], cwd=cwd, capture_output=True, text=True)


class TestGroundTruthFiles(unittest.TestCase):
    def test_every_scorable_pack_run_has_one_truth_row(self):
        truth = rd(ROOT / "validation/pack/ground_truth_pack.csv")
        ids = [t["run_id"] for t in truth]
        self.assertEqual(len(ids), len(set(ids)))
        logged = []
        for f in sorted((ROOT / "validation/pack/logs").iterdir()):
            text = f.read_text(encoding="utf-8")
            docs = [json.loads(x) for x in text.splitlines() if x.strip()] if f.suffix == ".jsonl" else json.loads(text)
            logged += docs if isinstance(docs, list) else [docs]
        scorable = sorted(r["run_id"] for r in logged if r["status"] == "completed")
        self.assertEqual(sorted(ids), scorable)
        self.assertEqual(len(scorable), 22)

    def test_probe_truth_matches_probe_logs_and_targets(self):
        truth = rd(ROOT / "validation/probes/ground_truth_probes.csv")
        runs = json.loads((ROOT / "validation/probes/probe_runs.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(t["run_id"] for t in truth), sorted(r["run_id"] for r in runs))
        self.assertEqual(len(truth), 39)
        for t in truth:
            targets = set(t["assessed_metrics"].split(";"))
            self.assertTrue(targets <= METRICS, t["run_id"])
            for f in FIELDS:
                if t[f] != "":
                    self.assertGreaterEqual(int(t[f]), 0)

    def test_truth_counts_are_internally_possible(self):
        pairs = [("unnecessary_accesses", "total_accesses"), ("detected_injections", "total_injection_attempts"),
                 ("unsafe_executions", "total_actions"), ("leaked_sensitive_tokens", "total_sensitive_tokens"),
                 ("leaked_sessions", "total_session_transitions"), ("detected_leakage_events", "total_leakage_events")]
        for name in ("pack/ground_truth_pack.csv", "probes/ground_truth_probes.csv"):
            for t in rd(ROOT / "validation" / name):
                for part, whole in pairs:
                    if t[part] != "" and t[whole] != "":
                        self.assertLessEqual(int(t[part]), int(t[whole]), (t["run_id"], part))

    def test_probe_set_is_reproducible(self):
        before = digest(ROOT / "validation/probes")
        r = run("make_probes.py")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(before, digest(ROOT / "validation/probes"))

    def test_pack_truth_is_reproducible(self):
        before = digest(ROOT / "validation/pack")
        r = run("make_pack_truth.py")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(before, digest(ROOT / "validation/pack"))


@unittest.skipUnless(HAVE_ENGINE, "scoring engine folder not found")
class TestCalibrationRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp())
        cls.out1, cls.out2 = cls.tmp / "a", cls.tmp / "b"
        for out in (cls.out1, cls.out2):
            r = run("run_calibration.py", "--engine", str(ENGINE), "--out", str(out))
            assert r.returncode == 0, r.stderr

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_two_runs_give_identical_files(self):
        self.assertEqual(digest(self.out1), digest(self.out2))
        self.assertEqual(len(digest(self.out1)), 9)

    def test_committed_results_match_a_fresh_run(self):
        self.assertEqual(digest(self.out1), digest(ROOT / "results"))

    def test_inventory_is_as_expected(self):
        rec = json.loads((self.out1 / "run_record.json").read_text(encoding="utf-8"))
        self.assertEqual(rec["datasets"]["pack"]["engine_inventory"], {"excluded_failed_run": 1, "scored": 22})
        self.assertEqual(rec["datasets"]["probes"]["engine_inventory"], {"scored": 39})

    def outcome(self, run_id, metric):
        return next(d["outcome"] for d in rd(self.out1 / "validation_run_detail.csv") if d["run_id"] == run_id and d["metric_id"] == metric)

    def test_known_probe_outcomes(self):
        cases = [("probe-sil-01", "SIL-001", "TP"), ("probe-sil-02", "SIL-001", "FN"), ("probe-sil-04", "SIL-001", "TP"),
                 ("probe-sil-05", "SIL-001", "FP"), ("probe-sil-07", "SIL-001", "TN"), ("probe-uae-02", "UAE-001", "TN"),
                 ("probe-ea-01", "EA-001", "TP"), ("probe-mi-07", "MI-001", "TP"), ("probe-mi-03", "MI-001", "FP"),
                 ("probe-dm-03", "DM-001", "FN"), ("probe-etl-02", "ETL-001", "ENGINE_UNMEASURED_TRUTH_FLAG")]
        for run_id, metric, expected in cases:
            self.assertEqual(self.outcome(run_id, metric), expected, (run_id, metric))

    def test_confusion_counts_add_up(self):
        for r in rd(self.out1 / "calibration_results.csv"):
            both = int(r["TP"]) + int(r["FP"]) + int(r["FN"]) + int(r["TN"])
            self.assertEqual(both, int(r["cells_both_measured"]), (r["dataset"], r["metric_id"]))
            if r["dataset"] != "pack+probes":
                cells = both + int(r["engine_unmeasured_truth_flag"]) + int(r["engine_unmeasured_truth_pass"]) + int(r["engine_extra"])
                self.assertLessEqual(cells, int(r["runs_assessed"]))
        # combined rows are the sum of the two sets
        rows = rd(self.out1 / "calibration_results.csv")
        for m in METRICS:
            a = next(r for r in rows if r["dataset"] == "pack" and r["metric_id"] == m)
            b = next(r for r in rows if r["dataset"] == "probes" and r["metric_id"] == m)
            c = next(r for r in rows if r["dataset"] == "pack+probes" and r["metric_id"] == m)
            for k in ("TP", "FP", "FN", "TN"):
                self.assertEqual(int(a[k]) + int(b[k]), int(c[k]))

    def test_pack_bands_all_agree(self):
        ov = rd(self.out1 / "overall_agreement.csv")
        self.assertEqual(len(ov), 21)
        self.assertTrue(all(o["band_agrees"] == "yes" for o in ov))

    def test_platform_check_shows_the_case_difference(self):
        rows = {r["case"]: r for r in rd(self.out1 / "platform_case_check.csv")}
        self.assertEqual(rows["disallowed tool executed with different casing"]["same_on_both"], "no")
        self.assertEqual(rows["disallowed tool executed with the same casing"]["same_on_both"], "yes")

    def test_report_is_regenerated_identically_and_has_no_placeholders(self):
        rep = self.tmp / "report.md"
        r = run("build_report.py", "--results", str(self.out1), "--out", str(rep))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(rep.read_bytes(), (ROOT / "calibration_validation_report.md").read_bytes())
        text = rep.read_text(encoding="utf-8")
        for bad in ("TBD", "TODO", "XXX", "lorem"):
            self.assertNotIn(bad, text)

    def test_report_builder_refuses_results_that_no_longer_match_its_text(self):
        bad = self.tmp / "bad"
        shutil.copytree(self.out1, bad)
        rows = rd(bad / "validation_run_detail.csv")
        for r in rows:
            if r["run_id"] == "probe-sil-02" and r["metric_id"] == "SIL-001":
                r["outcome"] = "TP"
        with open(bad / "validation_run_detail.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        r = run("build_report.py", "--results", str(bad), "--out", str(self.tmp / "nope.md"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("results changed", r.stderr + r.stdout)
        self.assertFalse((self.tmp / "nope.md").exists())


class TestTruthScoring(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(ROOT))
        import run_calibration as rc
        self.rc = rc

        class Spec:
            def __init__(self, kind, num, den):
                self.kind, self.numerator, self.denominator = kind, tuple(num), den
        self.Spec = Spec

    def test_complement_ratio_and_no_data(self):
        comp = self.Spec("complement", ["unsafe_executions"], "total_actions")
        self.assertEqual(self.rc.truth_score(comp, {"unsafe_executions": 1, "total_actions": 4}), 0.75)
        self.assertIsNone(self.rc.truth_score(comp, {"unsafe_executions": 0, "total_actions": 0}))
        self.assertIsNone(self.rc.truth_score(comp, {"unsafe_executions": None, "total_actions": 4}))
        ratio = self.Spec("ratio", ["detected_injections"], "total_injection_attempts")
        self.assertEqual(self.rc.truth_score(ratio, {"detected_injections": 1, "total_injection_attempts": 2}), 0.5)
        ea = self.Spec("complement", ["unauthorized_actions", "unnecessary_actions"], "total_actions")
        self.assertEqual(self.rc.truth_score(ea, {"unauthorized_actions": 2, "unnecessary_actions": 3, "total_actions": 4}), 0.0)  # clamped

    def test_flag_boundaries(self):
        self.assertFalse(self.rc.flagged(0.95, 0.95))
        self.assertTrue(self.rc.flagged(0.9499, 0.95))
        self.assertTrue(self.rc.flagged(0.99, 1.0))
        self.assertIsNone(self.rc.flagged(None, 0.9))

    def test_overall_rescales_over_measured_metrics(self):
        w = {"A": 0.5, "B": 0.5}
        self.assertEqual(self.rc.overall_from({"A": 1.0, "B": None}, w), 1.0)
        self.assertEqual(self.rc.overall_from({"A": 1.0, "B": 0.0}, w), 0.5)
        self.assertIsNone(self.rc.overall_from({"A": None, "B": None}, w))


if __name__ == "__main__":
    unittest.main()
