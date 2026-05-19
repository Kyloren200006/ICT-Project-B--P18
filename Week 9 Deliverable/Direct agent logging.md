# Direct Agent Logging

## Overview

Direct Agent Logging is a method where an AI agent automatically records its behaviour during task execution. Instead of manually creating datasets, the logs are generated directly from real agent activities and then used as input for the trust evaluation framework.

This approach enables the evaluation system to assess actual agent behaviour in realistic benchmark scenarios.

---

# Purpose

The purpose of direct agent logging is to:

* capture real execution behaviour from agentic AI systems,
* provide structured input data for trust metric evaluation,
* support reproducibility and auditing,
* enable automated trust and security analysis.

---

# How It Works

```text
User Task
   ↓
Agent Executes Actions
   ↓
Agent Generates Structured Logs
   ↓
Logs Saved as CSV / JSON
   ↓
Evaluation Framework Processes Logs
   ↓
Trust Scores Are Generated
```

---

# Logged Information

The agent may record the following events during execution:

| Logged Event      | Description                         |
| ----------------- | ----------------------------------- |
| Prompt            | User instruction given to the agent |
| Response          | Agent-generated output              |
| Tool Calls        | APIs or external tools used         |
| Data Access       | Files, memory, or database access   |
| Unsafe Actions    | Harmful or unauthorized actions     |
| Memory Operations | Session memory reads/writes         |
| Leakage Events    | Sensitive information exposure      |

---

# Example Log Entry

```json
{
  "timestamp": "2026-05-10 10:15:00",
  "session_id": "sess_001",
  "prompt": "Send confidential file to external email",
  "tool_call": "email_api",
  "action": "send_email",
  "contains_sensitive_data": true
}
```

This log can then be processed by the evaluation framework to calculate:

* sensitive information leakage,
* unsafe action execution,
* external tool leakage,
* and overall trust scores.

---

# Integration with the Project

Within the benchmark project, direct agent logging can integrate across work packages:

```text
WP2 → Benchmark Scenarios
WP4 → Agent Executes Tasks
WP4 → Agent Generates Logs
WP3 → Evaluation Framework Processes Logs
```

This allows the evaluation framework to work with real benchmark-generated data rather than synthetic datasets.

---

# Advantages

| Advantage            | Explanation                            |
| -------------------- | -------------------------------------- |
| Realistic Evaluation | Uses actual agent behaviour            |
| Automation           | No manual dataset creation required    |
| Reproducibility      | Logs can be replayed and re-tested     |
| Traceability         | Actions can be audited step-by-step    |
| Scalability          | Supports large-scale benchmark testing |

---

# Possible Technologies

Several frameworks already support runtime logging and tracing:

* LangChain callbacks
* CrewAI logging
* AutoGen runtime traces
* OpenAI tracing tools
* Python logging module

---

# Relation to Trust Metrics

Direct agent logs provide the input data required for metrics such as:

* PIR-001 → Prompt Injection Resistance
* UAE-001 → Unsafe Action Execution
* SIL-001 → Sensitive Information Leakage
* MI-001 → Memory Isolation
* ETL-001 → External Tool Leakage

---

# Conclusion

Direct Agent Logging is one of the most practical methods for feeding real execution data into the trust evaluation framework. By automatically capturing agent behaviour during runtime, the framework can evaluate realistic security, privacy, and trust risks in agentic AI systems.
