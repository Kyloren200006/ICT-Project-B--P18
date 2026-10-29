"""Tests for aggregate_summaries.py. Run from the package folder:

    py -m unittest discover -s tests -t .

Every expected number below was worked out by hand from the inputs in the test itself.
"""
import contextlib
import csv
import io
import json
import pathlib
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import aggregate_summaries as ag  # noqa: E402

DEFS = ag.load_definitions(ROOT / "metric_definitions.yaml")
SCORE_COLS = [m.score_column for m in DEFS.metrics]
BASE_COLS = ["run_id", "scenario_id", "agent_config", "model", "mitigation", "status",
             "workflow", "scenario_type", "risk_ids"]
ALL_COLS = BASE_COLS + SCORE_COLS + ["metrics_not_measured", "overall_trust_score", "trust_level"]


def make_row(n, agent, scenario, overall, workflow="", risks="", status="completed", **scores):
    """scores: DM_001=1.0 etc. (omitted = blank = not measured)."""
    row = {"run_id": f"run-{n:03d}", "scenario_id": scenario, "agent_config": agent, "model": "m1",
           "mitigation": "", "status": status, "workflow": workflow, "scenario_type": "",
           "risk_ids": risks, "metrics_not_measured": "", "trust_level": "",
           "overall_trust_score": "" if overall is None else overall}
    for col in SCORE_COLS:
        key = col[:-len("_score")]
        row[col] = scores.get(key, "")
    return row


def write_csv(path, rows, cols=ALL_COLS):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def run_agg(self, rows, lookup=None, name="scored_runs.csv", **kw):
        scored = self.tmp / name
        write_csv(scored, rows)
        out = self.tmp / "out"
        res = ag.run(str(scored), lookup, str(ROOT / "metric_definitions.yaml"), str(out), **kw)
        return res["agg"], out

    def cli(self, *args):
        err, outp = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(outp):
            code = ag.main(list(args))
        return code, outp.getvalue(), err.getvalue()


class TestAgentSummary(Base):
    def test_mean_std_min_band(self):
        rows = [make_row(1, "A", "S1", 1.0), make_row(2, "A", "S1", 0.5), make_row(3, "A", "S1", 0.0)]
        agg, _ = self.run_agg(rows)
        a = agg["by_agent"][0]
        self.assertEqual(a["n_runs"], 3)
        self.assertEqual(a["mean_overall"], 0.5)          # (1 + .5 + 0) / 3 = .5
        self.assertEqual(a["std_overall"], 0.5)           # sample std of 1, .5, 0 = sqrt(.5 / 2) = .5
        self.assertEqual(a["min_overall"], 0.0)
        self.assertEqual(a["trust_level"], "Moderate Risk")   # 0.5 is the Moderate floor

    def test_two_agents_kept_apart_and_sorted(self):
        rows = [make_row(1, "B", "S1", 1.0), make_row(2, "A", "S1", 0.2), make_row(3, "A", "S1", 0.4)]
        agg, _ = self.run_agg(rows)
        self.assertEqual([r["agent_config"] for r in agg["by_agent"]], ["A", "B"])
        a, b = agg["by_agent"]
        self.assertEqual(a["mean_overall"], 0.3)
        self.assertEqual(a["trust_level"], "High Risk")
        self.assertEqual(b["mean_overall"], 1.0)
        self.assertEqual(b["trust_level"], "Trusted")
        self.assertIsNone(b["std_overall"])               # one run: no standard deviation

    def test_same_agent_different_model_or_mitigation_is_a_separate_row(self):
        r1, r2 = make_row(1, "A", "S1", 1.0), make_row(2, "A", "S1", 0.0)
        r2["mitigation"] = "filter_on"
        agg, _ = self.run_agg([r1, r2])
        self.assertEqual(len(agg["by_agent"]), 2)

    def test_metric_means_ignore_blank_and_count_no_data(self):
        rows = [make_row(1, "A", "S1", 1.0, DM_001=1.0, PIR_001=0.0),
                make_row(2, "A", "S1", 0.5, DM_001=0.5),
                make_row(3, "A", "S1", 0.0)]
        agg, _ = self.run_agg(rows)
        a = agg["by_agent"][0]
        self.assertEqual(a["DM_001_score_mean"], 0.75)    # (1 + .5) / 2: the blank run is not a zero
        self.assertEqual(a["DM_001_n_no_data"], 1)
        self.assertEqual(a["PIR_001_score_mean"], 0.0)
        self.assertEqual(a["PIR_001_n_no_data"], 2)
        self.assertIsNone(a["MI_001_score_mean"])         # nothing measured at all
        self.assertEqual(a["MI_001_n_no_data"], 3)

    def test_run_without_overall_score_counts_as_a_run_but_not_in_the_mean(self):
        rows = [make_row(1, "A", "S1", 1.0), make_row(2, "A", "S1", None)]
        agg, _ = self.run_agg(rows)
        a = agg["by_agent"][0]
        self.assertEqual((a["n_runs"], a["n_runs_with_score"], a["mean_overall"]), (2, 1, 1.0))


class TestBands(unittest.TestCase):
    def test_boundaries(self):
        cases = [(1.0, "Trusted"), (0.95, "Trusted"), (0.949999, "Low Risk"), (0.80, "Low Risk"),
                 (0.799999, "Moderate Risk"), (0.50, "Moderate Risk"), (0.49999999999999994, "Moderate Risk"),
                 (0.499999, "High Risk"), (0.0, "High Risk"), (None, "Not measured")]
        for score, band in cases:
            self.assertEqual(ag.band_for(DEFS, score), band, score)

    def test_bands_come_from_the_definitions_file(self):
        import yaml
        doc = yaml.safe_load((ROOT / "metric_definitions.yaml").read_text(encoding="utf-8"))
        for b in doc["risk_bands"]:
            if b["name"] == "Moderate Risk":
                b["min"] = 0.60
        alt = pathlib.Path(tempfile.mkdtemp()) / "alt.yaml"
        self.addCleanup(shutil.rmtree, alt.parent, ignore_errors=True)
        alt.write_text(yaml.safe_dump(doc), encoding="utf-8")
        d2 = ag.load_definitions(alt)
        self.assertEqual(ag.band_for(DEFS, 0.55), "Moderate Risk")
        self.assertEqual(ag.band_for(d2, 0.55), "High Risk")


class TestWorkflow(Base):
    def test_split_by_workflow_with_unlabelled_bucket(self):
        rows = [make_row(1, "A", "E1", 1.0, workflow="email"), make_row(2, "A", "E2", 0.0, workflow="email"),
                make_row(3, "A", "W1", 0.6, workflow="web research"), make_row(4, "A", "X1", 0.2)]
        agg, _ = self.run_agg(rows)
        got = {r["workflow"]: (r["n_runs"], r["mean_overall"]) for r in agg["by_workflow"]}
        self.assertEqual(got, {"email": (2, 0.5), "web research": (1, 0.6), ag.UNLABELLED: (1, 0.2)})


class TestRisk(Base):
    def rows(self):
        return [
            # TC6 links DM-001, UAE-001, EA-001. Run 1: (1.0 + 0.5 + 0.0) / 3 = 0.5
            make_row(1, "A", "S1", 0.5, risks="TC6", DM_001=1.0, UAE_001=0.5, EA_001=0.0),
            # Run 2: UAE blank, so (1.0 + 1.0) / 2 = 1.0
            make_row(2, "A", "S2", 1.0, risks="TC6", DM_001=1.0, EA_001=1.0),
            make_row(3, "A", "S3", 0.0, risks="TC1", PIR_001=0.0),
        ]

    def test_risk_score_is_mean_over_runs_of_mean_of_linked_metrics(self):
        agg, _ = self.run_agg(self.rows())
        got = {r["risk"]: r for r in agg["by_risk"]}
        tc6 = got["TC6"]
        self.assertEqual(tc6["linked_metrics"], "DM-001;UAE-001;EA-001")
        self.assertEqual((tc6["n_runs"], tc6["n_runs_measured"]), (2, 2))
        self.assertEqual(tc6["mean_risk_score"], 0.75)            # (0.5 + 1.0) / 2
        self.assertEqual(tc6["std_risk_score"], 0.353553)         # sample std of 0.5 and 1.0
        self.assertEqual(tc6["trust_level"], "Moderate Risk")
        self.assertEqual(got["TC1"]["mean_risk_score"], 0.0)
        self.assertEqual(got["TC1"]["trust_level"], "High Risk")
        self.assertEqual(set(got), {"TC1", "TC6"})                # only tagged risks appear
        self.assertTrue(all(r["basis"] == "scenario_tags" for r in agg["by_risk"]))

    def test_one_scenario_counts_toward_each_of_its_risks(self):
        # TC2 links SIL-001 and ETL-001; TC3 links UAE-001 and ETL-001.
        rows = [make_row(1, "A", "S1", 0.5, risks="TC2;TC3", SIL_001=0.0, ETL_001=1.0, UAE_001=0.5)]
        agg, _ = self.run_agg(rows)
        got = {r["risk"]: r["mean_risk_score"] for r in agg["by_risk"]}
        self.assertEqual(got, {"TC2": 0.5, "TC3": 0.75})          # (0+1)/2 and (0.5+1)/2

    def test_risk_with_nothing_measured(self):
        rows = [make_row(1, "A", "S1", None, risks="TC4")]         # TC4 links MI-001, which is blank
        agg, _ = self.run_agg(rows)
        r = agg["by_risk"][0]
        self.assertEqual((r["n_runs"], r["n_runs_measured"]), (1, 0))
        self.assertIsNone(r["mean_risk_score"])
        self.assertEqual(r["trust_level"], "Not measured")

    def test_tag_not_linked_to_any_metric(self):
        agg, _ = self.run_agg([make_row(1, "A", "S1", 1.0, risks="TC9", DM_001=1.0)])
        r = agg["by_risk"][0]
        self.assertEqual((r["linked_metrics"], r["mean_risk_score"]), ("(none)", None))

    def test_no_tags_anywhere_falls_back_to_every_run_for_every_risk(self):
        rows = [make_row(1, "A", "S1", 1.0, DM_001=1.0, PIR_001=1.0),
                make_row(2, "A", "S2", 0.0, DM_001=0.0, PIR_001=0.0)]
        agg, _ = self.run_agg(rows)
        self.assertEqual({r["risk"] for r in agg["by_risk"]}, set(DEFS.risks()))
        self.assertTrue(all(r["basis"] == "all_runs" for r in agg["by_risk"]))
        tc1 = [r for r in agg["by_risk"] if r["risk"] == "TC1"][0]
        self.assertEqual((tc1["n_runs"], tc1["mean_risk_score"]), (2, 0.5))
        self.assertIn("all_runs", agg["metadata"]["per_risk_basis"])

    def test_untagged_run_is_left_out_and_reported(self):
        rows = self.rows() + [make_row(4, "A", "S4", 0.9)]
        agg, _ = self.run_agg(rows)
        self.assertEqual(agg["metadata"]["runs_without_risk_tag"], 1)
        self.assertEqual(sum(r["n_runs"] for r in agg["by_risk"]), 3)


class TestLookup(Base):
    def write_lookup(self, text, name="lookup.csv"):
        p = self.tmp / name
        p.write_text(text, encoding="utf-8")
        return str(p)

    def test_lookup_supplies_workflow_and_risks(self):
        lk = self.write_lookup('scenario_id,workflow,type,risk_ids\nS1,email,adversarial,"TC1;TC2"\n')
        agg, _ = self.run_agg([make_row(1, "A", "S1", 0.5, PIR_001=0.5, SIL_001=0.5, ETL_001=0.5)], lookup=lk)
        self.assertEqual(agg["by_workflow"][0]["workflow"], "email")
        self.assertEqual({r["risk"] for r in agg["by_risk"]}, {"TC1", "TC2"})
        self.assertEqual(agg["by_scenario"][0]["scenario_type"], "adversarial")
        self.assertEqual(agg["by_scenario"][0]["risk_ids"], "TC1;TC2")
        self.assertEqual(agg["metadata"]["scenarios_not_in_lookup"], [])

    def test_lookup_overrides_the_scored_file_and_unknown_ids_fall_back_to_it(self):
        lk = self.write_lookup("scenario_id,workflow,risk_ids\nS1,web research,TC1\n")
        rows = [make_row(1, "A", "S1", 1.0, workflow="email", risks="TC6", PIR_001=1.0),
                make_row(2, "A", "S2", 1.0, workflow="email", risks="TC6", DM_001=1.0)]
        agg, _ = self.run_agg(rows, lookup=lk)
        wf = {r["workflow"]: r["n_runs"] for r in agg["by_workflow"]}
        self.assertEqual(wf, {"web research": 1, "email": 1})
        self.assertEqual({r["risk"] for r in agg["by_risk"]}, {"TC1", "TC6"})
        self.assertEqual(agg["metadata"]["scenarios_not_in_lookup"], ["S2"])

    def test_blank_lookup_value_does_not_erase_the_scored_files_value(self):
        lk = self.write_lookup("scenario_id,workflow,risk_ids\nS1,,\n")
        agg, _ = self.run_agg([make_row(1, "A", "S1", 1.0, workflow="email", risks="TC6", DM_001=1.0)], lookup=lk)
        self.assertEqual(agg["by_workflow"][0]["workflow"], "email")
        self.assertEqual(agg["by_risk"][0]["risk"], "TC6")

    def test_header_aliases_and_map(self):
        lk = self.write_lookup("Scenario,Domain,Linked Risks\nS1,scheduling,TC3\n")
        agg, _ = self.run_agg([make_row(1, "A", "S1", 1.0, UAE_001=1.0)], lookup=lk)
        self.assertEqual(agg["by_workflow"][0]["workflow"], "scheduling")
        lk2 = self.write_lookup("ID_in_index,Area,Threats\nS1,file handling,TC4\n", "lookup2.csv")
        agg2, _ = self.run_agg([make_row(1, "A", "S1", 1.0, MI_001=1.0)], lookup=lk2,
                               column_map={"scenario_id": "ID_in_index", "workflow": "Area", "risk_ids": "Threats"})
        self.assertEqual(agg2["by_workflow"][0]["workflow"], "file handling")
        self.assertEqual(agg2["by_risk"][0]["risk"], "TC4")

    def test_risk_separators(self):
        self.assertEqual(ag.split_risks("TC1;TC2"), ["TC1", "TC2"])
        self.assertEqual(ag.split_risks("TC1, TC2 | TC3"), ["TC1", "TC2", "TC3"])
        self.assertEqual(ag.split_risks("TC1;TC1"), ["TC1"])
        self.assertEqual(ag.split_risks(None), [])

    def test_bad_lookups_are_reported(self):
        with self.assertRaises(ag.AggregateError):
            ag.load_lookup(self.write_lookup("scenario_id,workflow\nS1,email\nS1,web\n"))       # duplicate
        with self.assertRaises(ag.AggregateError):
            ag.load_lookup(self.write_lookup("name,workflow\nS1,email\n"))                      # no ID column
        with self.assertRaises(ag.AggregateError):
            ag.load_lookup(self.write_lookup("scenario_id,workflow\nS1,email\n"), {"workflow": "Nope"})
        with self.assertRaises(ag.AggregateError):
            ag.load_lookup(self.tmp / "missing.csv")


class TestInput(Base):
    def test_json_gives_the_same_output_as_csv(self):
        rows = [make_row(1, "A", "S1", 1.0, "email", "TC1", PIR_001=1.0),
                make_row(2, "A", "S1", 0.25, "email", "TC1", PIR_001=0.25)]
        _, out_csv = self.run_agg(rows)
        csv_files = {p.name: p.read_bytes() for p in out_csv.iterdir()}
        shutil.rmtree(out_csv)
        jrows = []
        for r in rows:
            j = dict(r)
            for k in SCORE_COLS + ["overall_trust_score"]:
                j[k] = None if j[k] == "" else float(j[k])
            jrows.append(j)
        jp = self.tmp / "scored_runs.json"
        jp.write_text(json.dumps(jrows), encoding="utf-8")
        ag.run(str(jp), None, str(ROOT / "metric_definitions.yaml"), str(out_csv))
        json_files = {p.name: p.read_bytes() for p in out_csv.iterdir()}
        # the JSON metadata names its own source file; everything else is identical
        for name in csv_files:
            if name != "summary_all.json":
                self.assertEqual(csv_files[name], json_files[name], name)
        a, b = json.loads(csv_files["summary_all.json"]), json.loads(json_files["summary_all.json"])
        a["metadata"].pop("scored_runs_file"); b["metadata"].pop("scored_runs_file")
        self.assertEqual(a, b)

    def test_json_with_runs_key(self):
        jp = self.tmp / "scored_runs.json"
        r = make_row(1, "A", "S1", 0.7)
        jp.write_text(json.dumps({"runs": [r]}), encoding="utf-8")
        res = ag.run(str(jp), None, str(ROOT / "metric_definitions.yaml"), str(self.tmp / "o"))
        self.assertEqual(res["agg"]["by_agent"][0]["mean_overall"], 0.7)

    def test_folder_input_finds_scored_runs(self):
        write_csv(self.tmp / "scored_runs.csv", [make_row(1, "A", "S1", 0.7)])
        res = ag.run(str(self.tmp), None, str(ROOT / "metric_definitions.yaml"), str(self.tmp / "o"))
        self.assertEqual(res["agg"]["metadata"]["runs_summarised"], 1)

    def test_rows_not_completed_are_skipped_and_reported(self):
        rows = [make_row(1, "A", "S1", 1.0), make_row(2, "A", "S1", 0.0, status="timeout")]
        agg, _ = self.run_agg(rows)
        self.assertEqual(agg["metadata"]["runs_skipped_not_completed"], 1)
        self.assertEqual(agg["by_agent"][0]["n_runs"], 1)

    def test_engine_inventory_is_reported_when_present(self):
        write_csv(self.tmp / "scored_runs.csv", [make_row(1, "A", "S1", 1.0)])
        (self.tmp / "run_inventory.csv").write_text(
            "source,run_id,scenario_id,status,detail\nx.json,run-001,S1,scored,\nx.json,run-002,S1,excluded_failed_run,timeout\n",
            encoding="utf-8")
        res = ag.run(str(self.tmp / "scored_runs.csv"), None, str(ROOT / "metric_definitions.yaml"), str(self.tmp / "o"))
        self.assertEqual(res["agg"]["metadata"]["runs_excluded_by_engine"], 1)

    def test_bad_inputs_raise_clear_errors(self):
        defs = DEFS
        with self.assertRaises(ag.AggregateError):
            ag.read_scored(self.tmp / "nope.csv", defs)
        empty = self.tmp / "empty.csv"
        write_csv(empty, [])
        with self.assertRaises(ag.AggregateError):
            ag.read_scored(empty, defs)
        notscored = self.tmp / "other.csv"
        notscored.write_text("a,b\n1,2\n", encoding="utf-8")
        with self.assertRaisesRegex(ag.AggregateError, "missing column"):
            ag.read_scored(notscored, defs)
        bad = self.tmp / "bad.csv"
        write_csv(bad, [make_row(1, "A", "S1", "high")])
        with self.assertRaisesRegex(ag.AggregateError, "not a number"):
            ag.read_scored(bad, defs)
        allfail = self.tmp / "allfail.csv"
        write_csv(allfail, [make_row(1, "A", "S1", 0.0, status="timeout")])
        with self.assertRaises(ag.AggregateError):
            ag.read_scored(allfail, defs)
        badjson = self.tmp / "bad.json"
        badjson.write_text("{not json", encoding="utf-8")
        with self.assertRaises(ag.AggregateError):
            ag.read_scored(badjson, defs)

    def test_utf8_bom_file_is_read(self):
        p = self.tmp / "bom.csv"
        write_csv(p, [make_row(1, "A", "S1", 0.7)])
        p.write_bytes(b"\xef\xbb\xbf" + p.read_bytes())
        rows, _ = ag.read_scored(p, DEFS)
        self.assertEqual(rows[0]["overall_trust_score"], 0.7)


class TestDeterminism(Base):
    def rows(self):
        return [make_row(i, a, s, o, w, r, DM_001=d)
                for i, (a, s, o, w, r, d) in enumerate([
                    ("B", "S2", 0.9, "web research", "TC1", 0.9), ("A", "S1", 0.4, "email", "TC6", 0.4),
                    ("A", "S2", 0.8, "web research", "TC1", 0.8), ("B", "S1", 1.0, "email", "TC6", 1.0),
                    ("A", "S1", 0.1, "email", "TC6", 0.1)], start=1)]

    def snapshot(self, out):
        return {p.name: p.read_bytes() for p in sorted(out.iterdir())}

    def test_same_input_same_bytes_and_no_carriage_returns(self):
        _, out1 = self.run_agg(self.rows())
        s1 = self.snapshot(out1)
        shutil.rmtree(out1)
        _, out2 = self.run_agg(self.rows())
        s2 = self.snapshot(out2)
        self.assertEqual(s1, s2)
        self.assertEqual(len(s1), 5)
        for name, data in s1.items():
            self.assertNotIn(b"\r", data, name)

    def test_row_order_in_the_input_does_not_matter(self):
        _, out1 = self.run_agg(self.rows())
        s1 = self.snapshot(out1)
        shutil.rmtree(out1)
        _, out2 = self.run_agg(list(reversed(self.rows())))
        self.assertEqual(s1, self.snapshot(out2))

    def test_json_output_is_valid_and_has_every_section(self):
        _, out = self.run_agg(self.rows())
        doc = json.loads((out / "summary_all.json").read_text(encoding="utf-8"))
        self.assertEqual(list(doc), ["metadata", "by_agent", "by_workflow", "by_risk", "by_scenario"])
        self.assertEqual(doc["metadata"]["runs_summarised"], 5)
        self.assertEqual(doc["metadata"]["agents"], ["A", "B"])
        # CSV and JSON agree
        csv_rows = read_csv(out / "summary_by_agent.csv")
        for c, j in zip(csv_rows, doc["by_agent"]):
            self.assertEqual(float(c["mean_overall"]), j["mean_overall"])
            self.assertEqual(int(c["n_runs"]), j["n_runs"])


class TestExamplesAndCli(Base):
    def test_example_files_reproduce_the_expected_output(self):
        ex = ROOT / "examples"
        out = self.tmp / "ex_out"
        code, _, err = self.cli(str(ex / "scored_runs.csv"), "--scenarios", str(ex / "scenario_lookup.csv"),
                                "--out", str(out))
        self.assertEqual((code, err), (0, ""))
        for exp in sorted((ex / "expected_output").iterdir()):
            self.assertEqual((out / exp.name).read_bytes(), exp.read_bytes(), exp.name)

    def test_example_numbers(self):
        rows = {r["agent_config"]: r for r in read_csv(ROOT / "examples" / "expected_output" / "summary_by_agent.csv")}
        self.assertEqual(rows["Agent_A_Baseline"]["n_runs"], "12")
        self.assertEqual(rows["Agent_A_Baseline"]["mean_overall"], "0.680808")
        self.assertEqual(rows["Agent_A_Baseline"]["trust_level"], "Moderate Risk")
        self.assertEqual(rows["Agent_B_Filtered"]["mean_overall"], "1.0")
        self.assertEqual(rows["Agent_B_Filtered"]["trust_level"], "Trusted")

    def test_cli_error_exit_code_and_message(self):
        code, out, err = self.cli(str(self.tmp / "missing.csv"), "--out", str(self.tmp / "o"))
        self.assertEqual(code, 1)
        self.assertTrue(err.startswith("error: "))
        self.assertFalse((self.tmp / "o").exists())

    def test_cli_prints_a_summary(self):
        write_csv(self.tmp / "s.csv", [make_row(1, "A", "S1", 1.0), make_row(2, "A", "S1", 0.5)])
        code, out, _ = self.cli(str(self.tmp / "s.csv"), "--no-scenarios", "--out", str(self.tmp / "o"))
        self.assertEqual(code, 0)
        self.assertIn("Summarised 2 run(s) for 1 agent configuration(s).", out)
        self.assertIn("Mean overall trust score (all runs): 0.750 (Moderate Risk)", out)

    def test_bad_map_option(self):
        write_csv(self.tmp / "s.csv", [make_row(1, "A", "S1", 1.0)])
        code, _, err = self.cli(str(self.tmp / "s.csv"), "--map", "colour=Red", "--out", str(self.tmp / "o"))
        self.assertEqual(code, 1)
        self.assertIn("unknown name", err)


if __name__ == "__main__":
    unittest.main()
