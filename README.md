# Agentic AI Fleet Copilot (Production Edition)

A production-grade Agentic Copilot built to analyze device telemetry data securely, enforce strict data isolation parameters across administrative domains, and propose contextually-grounded, verifiable remediation actions.

---

## 🛠️ Architecture Design
The Copilot operates on a **deterministic ReAct / State-Machine Agent loop**:
1. **Administrative Authentication Guardrail**: Parses user's request and matches the targeted company ID to verify compatibility with the Administrator's allowed company ID.
2. **Dynamic Data Retrieval Strategy**: Determines if query requires latest state snapshots (`query_fleet_telemetry`) or full deep temporal metrics (`get_device_history`) depending on the logic complexity.
3. **Reasoning & State Analysis**: Checks calculated storage thresholds (<20GB), rolling average RAM bottlenecks (>85% utilization over time), or degraded battery conditions.
4. **Verifiable State Actions & Audits**: Compiles action objects detailing exact target API properties and records execution in `audit_log.json`.

---

## 📂 Catalog of Files
- `tools.py`: Core tool ecosystem containing tenant isolating guardrails and telemetry analyzers.
- `agent.py`: Coordination loop housing the agent state rules.
- `evaluator.py`: Unit tests reflecting standard query cases.
- `data.csv`: Source database of snapshots and identities.

---

## 🚀 Execution Instructions

Run the testing suite directly to verify operation of all modules against your original data:
```bash
python3 evaluator.py
