



## **Evaluation Framework v1.0**

### **Overview**

The Evaluation Framework v1.0 is a Python-based system designed to assess the trustworthiness of agentic AI systems. It processes structured agent logs and computes standardized trust metrics.

---

### **Pipeline Architecture**

The framework follows a modular pipeline:

1. **Input Layer** – Reads structured log data (.csv)
2. **Preprocessing Module** – Cleans and normalizes data
3. **Metric Engine** – Computes trust metrics
4. **Aggregation Module** – Generates summary statistics
5. **Output Module** – Produces CSV and JSON outputs

---

### **Implemented Metrics**

| Metric  | Description                     |
| ------- | ------------------------------- |
| DM_001  | Data minimization efficiency    |
| PIR_001 | Prompt injection resistance     |
| UAE_001 | Unsafe action avoidance         |
| SIL_001 | Sensitive information leakage   |
| MI_001  | Memory isolation  |
| EA_001  | Excessive agent behaviour       |
| ETL_001 | External tool leakage detection |

---

### **Scoring**

* Each metric is normalized between **0 and 1**
* **1 = Fully safe behaviour**
* **0 = High-risk behaviour**

---

### **Aggregation**

The framework computes:

* Individual metric scores
* Weighted **overall trust score**
* Average scores across all logs

---

### **Outputs**

* **evaluation_results_v1.csv** → Detailed per-log scores
* **evaluation_summary_v1.json** → Aggregated metrics

---

### **Key Features**

* Fully automated evaluation
* Modular and extensible design
* Reproducible results
* Compatible with future benchmark datasets

---

