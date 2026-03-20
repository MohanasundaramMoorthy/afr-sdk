"""
Example: afr_llm + afr_tool wrappers
======================================
Demonstrates the Truth Boundary Layer wrappers.
Uses stub functions in place of real API calls.

Run:
    python examples/with_llm.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from afr_python_sdk          import Recorder
from afr_python_sdk.wrappers import afr_llm, afr_tool, detect_anomalies

BASE_URL = "http://localhost:3000"

# ── Stub implementations (replace with real SDK calls in production) ──────────

def call_claude(prompt: str) -> str:
    """Stub: returns a fixed model response."""
    return "Based on the risk signals, I recommend flagging this transaction for human review."


def run_risk_score(tool_input: dict) -> dict:
    """Stub: returns deterministic risk score."""
    return {
        "fraud_probability": 0.73,
        "risk_tier":         "high",
        "signals":           ["amount_anomaly", "velocity_flag"],
    }


# ── Run ───────────────────────────────────────────────────────────────────────

PROMPT = "Analyse transaction TXN-002 for fraud risk. Risk score: 0.73. What action should I take?"

recorder = Recorder(base_url=BASE_URL)
recorder.start(execution_context={
    "model":           "claude-sonnet-4-6",
    "system_prompt":   "You are a fraud detection agent.",
    "temperature":     0.2,
    "top_p":           0.9,
    "runtime_version": "1.0.0",
    "tools": [{"name": "risk_score"}],
})

# ── Planning ──────────────────────────────────────────────────────────────────
recorder.step({
    "step_type":      "planning",
    "goal_reference": "fraud_check_txn_002",
    "decision_context": {
        "description": "Classify TXN-002 as approve / flag / block.",
        "trigger":     "Payment request received",
    },
})

# ── Tool call via afr_tool (captures input + output together) ─────────────────
risk = afr_tool(
    recorder,
    "risk_score",
    run_risk_score,
    {"transaction_id": "TXN-002", "amount_usd": 3200},
)
print(f"Tool output: {risk}")

# ── LLM call via afr_llm (prompt hashed; raw response captured) ───────────────
response = afr_llm(
    recorder,
    call_claude,
    PROMPT,
    meta={
        "prompt":      PROMPT,                  # stored as SHA-256 hash only
        "model_name":  "claude-sonnet-4-6",
        "temperature": 0.2,
    },
)
print(f"Model response: {response[:60]}...")

# ── Decision ──────────────────────────────────────────────────────────────────
recorder.decision({
    "goal_reference":  "fraud_check_txn_002",
    "selected_option": "flag",
    "confidence":      0.84,
    "risk_assessment": {
        "risk_level":  "high",
        "risk_reason": "Risk score 0.73 exceeds flag threshold (0.40).",
    },
})

# ── Finish ────────────────────────────────────────────────────────────────────
proof = recorder.finish()

# ── Anomaly detection ─────────────────────────────────────────────────────────
anomalies = detect_anomalies(proof)
if anomalies:
    print("\nAnomalies detected:")
    for a in anomalies:
        print(f"  [{a['code']}] {a['message']}")
else:
    print("\nNo anomalies detected.")

print(f"\nProof steps:   {len(proof.get('steps', []))}")
print(f"Replayable:    {proof.get('execution_context') is not None}")
