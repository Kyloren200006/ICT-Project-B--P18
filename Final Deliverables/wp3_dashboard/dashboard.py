#!/usr/bin/env python3
"""WP3 Trust Metrics Dashboard.

Run from this folder:

    py dashboard.py                       # opens http://127.0.0.1:8765 and reads the files below
    py dashboard.py --scored ..\\scored_runs.csv --calibration ..\\wp3_calibration\\results
    py dashboard.py --export site         # write a static copy of every page into the folder "site"

Reads three things and rescored nothing:
  --definitions  metric_definitions.yaml (metrics, weights, thresholds, bands, formulas, linked risks)
  --scored       scored_runs.csv or scored_runs.json from the scoring engine
  --calibration  the results folder written by the calibration and validation package

With no options it uses ./input/ when files are there and falls back to the bundled ./examples/.
"""
import argparse
import os
import sys
import threading
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from wp3_dash import app  # noqa: E402


def pick_default(candidates):
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[-1]


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="WP3 Trust Metrics Dashboard",
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("--definitions", help="metric_definitions.yaml (default: the copy next to this script)")
    p.add_argument("--scored", help="scored_runs.csv or scored_runs.json (default: input/ then examples/)")
    p.add_argument("--calibration", help="calibration results folder (default: input/calibration then examples/calibration)")
    p.add_argument("--label", help="text shown at the top of every page describing what data this is")
    p.add_argument("--host", default="127.0.0.1", help="address to listen on (default 127.0.0.1, this computer only)")
    p.add_argument("--port", type=int, default=8765, help="port (default 8765)")
    p.add_argument("--no-browser", action="store_true", help="do not open a browser window")
    p.add_argument("--export", metavar="DIR", help="write a static copy of every page into DIR and exit")
    return p.parse_args(argv)


def resolve(args):
    d = args.definitions or os.path.join(HERE, "metric_definitions.yaml")
    s = args.scored or pick_default([
        os.path.join(HERE, "input", "scored_runs.csv"), os.path.join(HERE, "input", "scored_runs.json"),
        os.path.join(HERE, "examples", "scored_runs.csv")])
    c = args.calibration or pick_default([
        os.path.join(HERE, "input", "calibration"), os.path.join(HERE, "examples", "calibration")])
    label = args.label
    if label is None and not args.scored and os.path.abspath(s).startswith(os.path.join(HERE, "examples")):
        label = ("bundled example data: the 22-run WP3 test pack scored by the engine. These are test runs built "
                 "to exercise the metrics, not results for any real agent.")
    return d, s, c, label or ""


def main(argv=None):
    args = parse_args(argv)
    d, s, c, label = resolve(args)
    for what, path in (("definitions", d), ("scored runs", s)):
        if not os.path.isfile(path):
            print("Cannot find the %s file: %s" % (what, path), file=sys.stderr)
            return 2
    if not os.path.isdir(c):
        print("Note: calibration folder not found (%s); the Calibration page will be empty." % c)
    config = app.Config(d, s, c, label)
    try:
        config.load()
    except Exception as exc:
        print("Could not read the input files: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 2
    print("Definitions : %s" % d)
    print("Scored runs : %s" % s)
    print("Calibration : %s" % c)
    if args.export:
        files = app.export_site(config, args.export)
        print("Wrote %d pages to %s (open index.html)" % (len(files), os.path.abspath(args.export)))
        return 0
    try:
        httpd = app.serve(config, args.host, args.port)
    except OSError as exc:
        print("Cannot start on %s:%d (%s). Try another port with --port." % (args.host, args.port, exc), file=sys.stderr)
        return 1
    url = "http://%s:%d/" % (args.host, args.port)
    print("Dashboard running at %s  (Ctrl+C to stop)" % url)
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
