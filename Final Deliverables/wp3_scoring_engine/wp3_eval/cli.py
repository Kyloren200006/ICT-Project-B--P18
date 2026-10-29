"""Command line: python -m wp3_eval <command> ...

  score      Score run logs (one file or a whole folder) -> scored_runs.csv/.json, run_inventory.csv, summary.json
  wp2-lookup Build a scenario lookup CSV from WP2 scenario files (prose-only labels are left blank)
"""
from __future__ import annotations

import argparse
import sys
from typing import Dict, List, Optional

from . import __version__
from .config import ConfigError, load_config, load_rules
from .labels import build_lookup_from_wp2, load_lookup, write_lookup_csv
from .scoring import score_path, write_outputs


def _parse_map(pairs: Optional[List[str]]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for p in pairs or []:
        if "=" not in p:
            raise SystemExit(f"--map expects name=Header, got {p!r}")
        k, v = p.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--metrics", help="metric definitions YAML (default: metric_definitions.yaml next to the package)")
    p.add_argument("--rules", help="detection rules YAML (default: detection_rules.yaml)")
    p.add_argument("--scenarios", help="scenario lookup CSV (WP2 labels: workflow, risk IDs, sensitive items, ...)")
    p.add_argument("--map", action="append", metavar="NAME=HEADER",
                   help="map a lookup column, e.g. --map workflow=Workflow --map risk_ids='Linked risk IDs' (repeatable)")
    p.add_argument("--no-data", choices=["score_one", "not_measured"],
                   help="override how a metric with no data is scored")
    p.add_argument("--out", default="wp3_output", help="output folder (default: wp3_output)")


def _load_all(args):
    cfg = load_config(args.metrics, args.no_data)
    lookup = load_lookup(args.scenarios, _parse_map(args.map)) if args.scenarios else None
    return cfg, lookup


def _cmd_score(args) -> int:
    cfg, lookup = _load_all(args)
    rules = load_rules(args.rules)
    result = score_path(args.input, cfg, rules, lookup, validate=not args.no_validate, schema_path=args.schema)
    paths = write_outputs(args.out, cfg, result)
    _print_score_summary(cfg, result, paths)
    if args.strict and any(r["status"] in ("invalid_schema", "invalid_file", "invalid_record") for r in result.inventory):
        print("strict mode: some input did not validate (see run_inventory.csv)", file=sys.stderr)
        return 2
    return 0 if result.rows else 1


def _print_score_summary(cfg, result, paths) -> None:
    from .scoring import summarise
    s = summarise(cfg, result)
    print(f"Scored {s['runs_scored']} run(s). Inventory: {s['inventory']}")
    if s["mean_overall_trust_score"] is not None:
        print(f"Mean overall trust score: {s['mean_overall_trust_score']:.3f} ({s['trust_level']})  [no-data rule: {cfg.no_data}]")
    gaps = {k: v for k, v in s["runs_with_no_data_per_metric"].items() if v}
    if gaps:
        print("Runs with no data per metric: " + ", ".join(f"{k}={v}" for k, v in gaps.items()))
    print("Wrote: " + ", ".join(paths.values()))


def _cmd_wp2(args) -> int:
    rules = load_rules(args.rules)
    rows = build_lookup_from_wp2(args.paths, rules.get("category_to_risk") or {})
    if not rows:
        print("No WP2 scenario files found.", file=sys.stderr)
        return 1
    write_lookup_csv(rows, args.out)
    print(f"Wrote {len(rows)} scenario(s) to {args.out}.")
    print("sensitive_items and forbidden_markers are blank: WP2 holds them as prose, so fill them in by hand.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="wp3_eval", description="WP3 trust-metric scoring engine")
    p.add_argument("--version", action="version", version=f"wp3_eval {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("score", help="score run logs")
    s.add_argument("input", help="a log file (.json or .jsonl) or a folder of them")
    _add_common(s)
    s.add_argument("--schema", help="run-log JSON Schema (default: log_schema.json)")
    s.add_argument("--no-validate", action="store_true", help="skip JSON Schema validation of run logs")
    s.add_argument("--strict", action="store_true", help="exit with code 2 if any input fails validation")
    s.set_defaults(func=_cmd_score)

    w = sub.add_parser("wp2-lookup", help="build a scenario lookup CSV from WP2 scenario files")
    w.add_argument("paths", nargs="+", help="WP2 scenario files or folders (.json/.yml/.yaml)")
    w.add_argument("--out", default="scenario_lookup.csv")
    w.add_argument("--rules")
    w.set_defaults(func=_cmd_wp2)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ConfigError, ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
