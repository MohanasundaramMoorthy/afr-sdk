"""
Example: Basic run — planning + decision + finish
=================================================
Mirrors the Node SDK quick-start in agent-sdk/recorder.js.

Run against a live runtime:
    pip install afr-python-sdk
    python examples/basic_run.py
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from afr_python_sdk import Recorder

BASE_URL = "http://localhost:3000"

recorder = Recorder(base_url=BASE_URL)

# ── Start a replay-verifiable run ─────────────────────────────────────────────
run_id = recorder.start(execution_context={
    "model":           "claude-sonnet-4-6",
    "model_version":   "20250514",
    "system_prompt":   "You are a financial fraud detection agent.",
    "temperature":     0.2,
    "top_p":           0.9,
    "runtime_version": "1.0.0",
    "tools": [
        {"name": "risk_score"},
        {"name": "transaction_history"},
    ],
})
print(f"Run started: {run_id}")

# ── Planning step ─────────────────────────────────────────────────────────────
recorder.step({
    "step_type":        "planning",
    "goal_reference":   "fraud_decision_txn_001",
    "decision_context": {
        "description": "Determine whether TXN-001 ($4,750) should be approved, flagged, or blocked.",
        "trigger":     "Real-time payment authorisation request",
    },
})
print("Step 1: planning")

# ── Tool result step ──────────────────────────────────────────────────────────
recorder.step({
    "step_type":   "tool_result",
    "tool_name":   "risk_score",
    "tool_input":  {"transaction_id": "TXN-001", "amount_usd": 4750},
    "tool_output": {"fraud_probability": 0.73, "risk_tier": "high"},
})
print("Step 2: tool_result")

# ── Decision step ─────────────────────────────────────────────────────────────
recorder.decision({
    "goal_reference":   "fraud_decision_txn_001",
    "selected_option":  "flag",
    "confidence":       0.81,
    "risk_assessment":  {
        "risk_level":  "high",
        "risk_reason": "Fraud probability 0.73 exceeds flag threshold.",
    },
})
print("Step 3: decision (flag)")

# ── Finish and retrieve proof ─────────────────────────────────────────────────
proof = recorder.finish()
print(f"\nProof schema:  {proof.get('schema_version')}")
print(f"Steps:         {len(proof.get('steps', []))}")
print(f"Replayable:    {proof.get('execution_context') is not None}")
print(f"Chain hash:    {proof.get('final_chain_hash', '')[:16]}...")
