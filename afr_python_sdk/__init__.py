"""
afr-sdk — Agent Flight Recorder Python SDK
===========================================
Tamper-evident execution recording for AI agents.
Works with any LLM framework: LangChain, LangGraph, raw API calls, etc.

Quick start:

    from afr_python_sdk import Recorder

    rec = Recorder(base_url="http://localhost:3000", api_key="...")

    rec.start({"model": "claude-sonnet-4-6", "temperature": 0.2})
    rec.step({"step_type": "planning", "goal_reference": "evaluate-txn",
              "decision_context": {"description": "Check for fraud", "trigger": "payment"}})
    rec.decision({"goal_reference": "evaluate-txn", "selected_option": "block",
                  "confidence": 0.92})
    proof = rec.finish()

Context manager (auto-finish / abort on exception):

    with Recorder(base_url="http://localhost:3000", api_key="...") as rec:
        rec.start({"model": "claude-sonnet-4-6"})
        rec.step(...)
        rec.decision(...)
    # finish() called automatically

LLM / tool wrappers (optional, framework-agnostic):

    from afr_python_sdk.wrappers import afr_llm, afr_tool

    reply  = afr_llm(rec, call_claude, prompt,
                     meta={"model_name": "claude-sonnet-4-6", "temperature": 0.2})
    result = afr_tool(rec, "risk_score", run_risk_score, {"txn_id": "TXN-001"})
"""

# ── Primary public API ────────────────────────────────────────────────────────

from .recorder import Recorder
from .client   import Client, AfrClientError

__all__ = [
    "Recorder",
    "Client",
    "AfrClientError",
]
