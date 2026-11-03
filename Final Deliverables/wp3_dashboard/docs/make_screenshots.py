#!/usr/bin/env python3
"""Regenerate the screenshots in docs/screenshots/ from the running dashboard.

Needs Playwright with Chromium (optional; not needed to run the dashboard):
    py -m pip install playwright && py -m playwright install chromium

Starts the dashboard on the bundled example data (or the files you give), takes one image per page,
and stops it again:

    py docs/make_screenshots.py [--scored FILE] [--calibration DIR] [--out DIR]
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PORT = 8791

PAGES = [  # file name, path, height of the crop (None = whole page)
    ("01_overview", "/", 1500),
    ("02_metric_definitions", "/metrics", None),
    ("03_score_distributions", "/distributions", None),
    ("04_metric_detail_SIL-001", "/metric/SIL-001", 1250),
    ("05_runs", "/runs", None),
    ("06_calibration", "/calibration", 1700),
    ("07_data_and_checks", "/data", None),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored")
    ap.add_argument("--calibration")
    ap.add_argument("--out", default=os.path.join(HERE, "screenshots"))
    args = ap.parse_args()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed (see the note at the top of this file).", file=sys.stderr)
        return 2
    cmd = [sys.executable, os.path.join(ROOT, "dashboard.py"), "--no-browser", "--port", str(PORT)]
    if args.scored:
        cmd += ["--scored", args.scored]
    if args.calibration:
        cmd += ["--calibration", args.calibration]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = "http://127.0.0.1:%d" % PORT
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(base + "/healthz", timeout=1)
                break
            except Exception:
                time.sleep(0.2)
        else:
            print("The dashboard did not start.", file=sys.stderr)
            return 1
        os.makedirs(args.out, exist_ok=True)
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1280, "height": 900}, color_scheme="light")
            for name, path, h in PAGES:
                pg.goto(base + path)
                pg.wait_for_timeout(250)
                kw = {"clip": {"x": 0, "y": 0, "width": 1280, "height": h}} if h else {}
                pg.screenshot(path=os.path.join(args.out, name + ".png"), full_page=True, **kw)
            pg.goto(base + "/?agent=Agent_A_Baseline")
            pg.wait_for_timeout(250)
            pg.screenshot(path=os.path.join(args.out, "08_overview_filtered_agent_A.png"), full_page=True,
                          clip={"x": 0, "y": 0, "width": 1280, "height": 1500})
            pd = b.new_page(viewport={"width": 1280, "height": 900}, color_scheme="dark")
            pd.goto(base + "/")
            pd.wait_for_timeout(250)
            pd.screenshot(path=os.path.join(args.out, "09_overview_dark.png"), full_page=True,
                          clip={"x": 0, "y": 0, "width": 1280, "height": 1500})
            b.close()
        print("Wrote screenshots to", args.out)
        return 0
    finally:
        proc.terminate()


if __name__ == "__main__":
    sys.exit(main())
