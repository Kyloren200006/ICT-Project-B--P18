# WP3 Run-Log Schema (Final, schema version 0.1)

**From:** WP3 (Evaluation framework and metrics)
**To:** WP4 (Agent experiments)
**Status:** Final. This is the agreed run-log format for the WP3 scoring engine and dashboard. The `schema_version` value stays `"0.1"` so logs already produced remain valid. Any later change must be agreed with WP3 and WP4 and versioned.

## 1. Purpose

WP3's scoring engine reads one **run log** per agent run and scores it with our seven metrics. This document defines the log format WP4 should emit. Your current `benchmark_runs.json` is a good base: most of its fields map directly (see section 7).

The log records **what happened**, not whether it was safe. Judging safe versus unsafe is the scoring engine's job. It compares the log against the scenario's expected safe behaviour from WP2's suite.

## 2. File format

- UTF-8 JSON. Either **one JSON array** of run records, or **JSON Lines** (`.jsonl`, one record per line).
- One record per agent run. A repeat of the same scenario is a separate record.
- Timestamps are ISO 8601 with timezone, e.g. `2026-09-22T16:15:35+10:00`.
- Unknown or not-applicable values: use `null`. Do not omit required fields.

## 3. Run record (top level)

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `schema_version` | string | yes | Always `"0.1"` for this schema |
| `run_id` | string | yes | Unique ID of this run (UUID is fine) |
| `scenario_id` | string | yes | **Exact WP2 scenario ID.** The scoring engine looks up WP2's labels (injection planted, sensitive items, permitted tools) by this ID, so please do not invent IDs |
| `repeat_index` | integer | yes | 0 for the first run of this scenario/agent, 1 for the second, and so on |
| `agent` | object | yes | See section 4 |
| `status` | string | yes | `"completed"`, `"error"` or `"timeout"` |
| `error` | string or null | yes | Error text if `status` is not `"completed"`, else `null` |
| `started_at` | timestamp | yes | When the run started |
| `ended_at` | timestamp | yes | When the run ended |
| `sessions` | array | yes | One or more session objects (section 5). Single-session scenarios have exactly one |
| `final_output` | string or null | yes | The agent's final answer to the user, as the user would see it |

Failed runs (`status` other than `"completed"`) should still be written. We exclude them from scoring and report them in the run inventory.

## 4. `agent` object

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `agent_config` | string | yes | Your configuration name, e.g. `Agent_A_Baseline` |
| `provider` | string | yes | e.g. `OpenAI`, `Google` |
| `model` | string | yes | Exact model name, e.g. `gpt-5.6-luna` |
| `model_version` | string or null | yes | Exact version or snapshot if available |
| `mitigation` | string or null | yes | Name of the mitigation enabled (e.g. `front_door_filter`), or `null` if none. Replaces your `mode: Filtered/Unfiltered` |
| `memory_enabled` | boolean | yes | Whether the agent can carry memory across sessions |
| `settings` | object | no | Temperature, seed and other parameters |

## 5. `sessions[]`

A **session** is one conversation. Memory isolation scenarios need two or more sessions in one run (for example, information shared in session 1 and probed in session 2).

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `session_id` | string | yes | Unique session ID |
| `session_index` | integer | yes | 0, 1, 2... order within the run |
| `started_at` / `ended_at` | timestamp | yes | Session time span |
| `messages` | array | yes | Section 5.1 |
| `tool_calls` | array | yes | Section 5.2 (empty array if none) |
| `filter_events` | array | yes | Section 5.3 (empty array if none) |
| `memory_events` | array | no | Section 5.4. Needed when `memory_enabled` is `true` |

### 5.1 `messages[]`

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `index` | integer | yes | Order within the session |
| `role` | string | yes | `"system"`, `"user"`, `"assistant"` or `"tool"` |
| `source` | string | yes | Where the content came from: `"user"`, `"agent"`, `"tool_result"`, `"retrieved_content"` (email, web page, file). Injected content should be `retrieved_content` |
| `content` | string | yes | Full text |
| `timestamp` | timestamp | yes | When the message occurred |

### 5.2 `tool_calls[]`

Every tool call the agent **attempted**, including blocked ones.

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `call_id` | string | yes | Unique within the run |
| `tool` | string | yes | Tool name, e.g. `send_email` |
| `arguments` | object | yes | The arguments passed (needed to check what data left the agent) |
| `timestamp` | timestamp | yes | When the call was attempted |
| `status` | string | yes | `"executed"`, `"blocked"` or `"error"` |
| `blocked_by` | string or null | yes | Which control blocked it, or `null` |
| `external` | boolean | yes | `true` if the tool sends data outside the agent (email, HTTP request, external API) |
| `result_summary` | string or null | no | Short description of the result |

### 5.3 `filter_events[]`

Anything your filter or mitigation did. This carries over your current `detected`, `blocked`, `filter_triggered`, `output_redacted` and `leak_patterns` fields.

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `stage` | string | yes | `"input"`, `"output"` or `"tool"` |
| `action` | string | yes | `"blocked"`, `"redacted"` or `"flagged"` |
| `matched` | array of strings | yes | Phrases or patterns matched (your `detected` / `leak_patterns`) |
| `timestamp` | timestamp | yes | When it happened |

### 5.4 `memory_events[]` (when memory is enabled)

| Field | Type | Req. | Meaning |
|---|---|---|---|
| `operation` | string | yes | `"write"` or `"read"` |
| `key` | string or null | yes | Memory key or slot, if the agent has one |
| `content` | string | yes | What was written or retrieved |
| `timestamp` | timestamp | yes | When it happened |

## 6. What is not in the log (and why)

The scoring engine gets these from WP2's scenario suite, by `scenario_id`: whether an injection was planted, which items are sensitive, which tools and data the task was allowed to use, and the expected safe behaviour. You do not need to copy them into the log. **Using WP2's exact scenario IDs is therefore important.**

## 7. Mapping from your current format

| Your current field | New location |
|---|---|
| `session_id` | `run_id` (single-session runs) and `sessions[].session_id` |
| `timestamp` | `started_at` |
| `task_id` | `scenario_id` (must be WP2's ID) |
| `agent_config`, `provider`, `model` | `agent.*` |
| `mode` (Filtered/Unfiltered) | `agent.mitigation` |
| `prompt`, `model_input` | `sessions[].messages` (role `user`) |
| `response`, `agent_output` | `final_output` and a `messages` entry (role `assistant`) |
| `detected`, `blocked`, `filter_triggered`, `output_redacted`, `leak_patterns` | `sessions[].filter_events` |
| `tool_audit`, `action_executions`, `blocked_tools` | `sessions[].tool_calls` |
| `result`, `error` | `status`, `error` |
| `expected_behaviour`, `domain`, `adversarial_category`, `threat_model` | Not needed (from WP2/WP1 by `scenario_id`) |

## 8. Companion files

`log_schema.json` is the machine-readable JSON Schema (Draft 2020-12) for this format. The scoring engine validates every record against it before scoring.

See `example_log.json` for two example records.
