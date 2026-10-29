"""Shared builders for the tests."""
import copy
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TS = "2026-10-20T10:00:00+11:00"


def call(tool, args=None, status="executed", external=False, blocked_by=None, call_id="c"):
    return {"call_id": call_id, "tool": tool, "arguments": args or {}, "timestamp": TS,
            "status": status, "blocked_by": blocked_by, "external": external, "result_summary": None}


def msg(role, content, source=None, index=0):
    source = source or {"user": "user", "assistant": "agent", "tool": "tool_result", "system": "user"}[role]
    return {"index": index, "role": role, "source": source, "content": content, "timestamp": TS}


def session(idx=0, messages=None, calls=None, memory=None, filters=None):
    return {"session_id": f"s{idx}", "session_index": idx, "started_at": TS, "ended_at": TS,
            "messages": messages or [], "tool_calls": calls or [], "filter_events": filters or [],
            "memory_events": memory or []}


def run(run_id="r1", scenario="S1", sessions=None, agent="AgentA", status="completed", final="", repeat=0,
        model="m1", mitigation=None):
    return {"schema_version": "0.1", "run_id": run_id, "scenario_id": scenario, "repeat_index": repeat,
            "agent": {"agent_config": agent, "provider": "P", "model": model, "model_version": None,
                      "mitigation": mitigation, "memory_enabled": False},
            "status": status, "error": None if status == "completed" else "boom",
            "started_at": TS, "ended_at": TS, "sessions": sessions if sessions is not None else [session()],
            "final_output": final}
