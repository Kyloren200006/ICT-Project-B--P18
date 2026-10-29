"""Read run logs (.json or .jsonl): one file, or a whole directory."""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from .config import DEFAULT_SCHEMA_PATH

SUPPORTED_SUFFIXES = (".json", ".jsonl")


@dataclass
class Item:
    kind: str        # always "run" (a raw run log in the WP3 schema)
    data: dict
    source: str      # file the record came from
    note: str = ""


def _parse_json_bytes(raw: bytes, suffix: str) -> list:
    text = raw.decode("utf-8-sig")
    if suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    try:
        return [json.loads(text)]
    except json.JSONDecodeError:
        return [json.loads(line) for line in text.splitlines() if line.strip()]   # JSON Lines saved as .json


def load_bytes(raw: bytes, name: str) -> Tuple[List[Item], List[dict]]:
    """Load one uploaded file. Returns (items, problems). A problem is {'source','status','detail'}."""
    suffix = pathlib.Path(name).suffix.lower()
    items: List[Item] = []
    problems: List[dict] = []
    if suffix in (".json", ".jsonl"):
        try:
            docs = _parse_json_bytes(raw, suffix)
        except json.JSONDecodeError as exc:
            problems.append({"source": name, "status": "invalid_file", "detail": f"not valid JSON: {exc}"})
            return items, problems
        for doc in docs:
            records = doc if isinstance(doc, list) else [doc]
            for rec in records:
                if isinstance(rec, dict):
                    items.append(Item("run", rec, name))
                else:
                    problems.append({"source": name, "status": "invalid_record", "detail": "record is not a JSON object"})
        return items, problems
    problems.append({"source": name, "status": "invalid_file", "detail": f"unsupported file type {suffix!r}"})
    return items, problems


def collect_files(path) -> List[pathlib.Path]:
    p = pathlib.Path(path)
    if p.is_dir():
        return sorted((f for f in p.rglob("*") if f.is_file() and f.suffix.lower() in SUPPORTED_SUFFIXES),
                      key=lambda f: str(f.relative_to(p)))
    return [p]


def load_path(path) -> Tuple[List[Item], List[dict]]:
    items: List[Item] = []
    problems: List[dict] = []
    base = pathlib.Path(path)
    for f in collect_files(base):
        label = str(f.relative_to(base)) if base.is_dir() else f.name
        it, pr = load_bytes(f.read_bytes(), f.name)
        for i in it:
            i.source = label
        for p in pr:
            p["source"] = label
        items += it
        problems += pr
    return items, problems


_VALIDATOR = None


def get_validator(schema_path: Optional[str] = None):
    """jsonschema validator for the run-log schema, or None if jsonschema is not installed."""
    global _VALIDATOR
    if _VALIDATOR is not None and schema_path is None:
        return _VALIDATOR
    try:
        import jsonschema
    except ImportError:
        return None
    with open(schema_path or DEFAULT_SCHEMA_PATH, encoding="utf-8") as fh:
        schema = json.load(fh)
    validator = jsonschema.Draft202012Validator(schema)
    if schema_path is None:
        _VALIDATOR = validator
    return validator


def validation_errors(run: dict, validator, limit: int = 3) -> List[str]:
    if validator is None:
        return []
    errs = sorted(validator.iter_errors(run), key=lambda e: list(e.absolute_path))
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '(record)'}: {e.message}" for e in errs[:limit]]
