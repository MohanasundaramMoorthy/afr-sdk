"""
Example: Async wrappers with context manager
=============================================
Demonstrates afr_llm_async + afr_tool_async with asyncio.

Run:
    python examples/async_run.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from afr_python_sdk          import Recorder
from afr_python_sdk.wrappers import afr_llm_async, afr_tool_async


async def call_claude_async(prompt: str) -> str:
    """Stub async LLM call."""
    await asyncio.sleep(0)  # yield to event loop
    return "Transaction shows elevated fraud risk. Recommend flag for human review."


async def run_risk_score_async(tool_input: dict) -> dict:
    """Stub async tool."""
    await asyncio.sleep(0)
    return {"fraud_probability": 0.61, "risk_tier": "medium"}


async def main() -> None:
    PROMPT = "Evaluate TXN-003 for fraud risk."

    # Context manager: recorder.finish() called automatically on clean exit;
    # recorder.abort() called if an exception propagates out.
    with Recorder(base_url="http://localhost:3000") as recorder:
        recorder.start(execution_context={
            "model":           "claude-sonnet-4-6",
            "system_prompt":   "You are a fraud detection agent.",
            "temperature":     0.1,
            "top_p":           0.95,
            "runtime_version": "1.0.0",
            "tools":           [{"name": "risk_score"}],
        })

        recorder.step({
            "step_type":      "planning",
            "goal_reference": "fraud_check_txn_003",
            "decision_context": {
                "description": "Classify TXN-003.",
                "trigger":     "Payment request",
            },
        })

        risk = await afr_tool_async(
            recorder,
            "risk_score",
            run_risk_score_async,
            {"transaction_id": "TXN-003", "amount_usd": 2100},
        )
        print(f"Risk score: {risk['fraud_probability']}")

        response = await afr_llm_async(
            recorder,
            call_claude_async,
            PROMPT,
            meta={
                "prompt":      PROMPT,
                "model_name":  "claude-sonnet-4-6",
                "temperature": 0.1,
            },
        )
        print(f"Response: {response[:50]}...")

        recorder.decision({
            "goal_reference":  "fraud_check_txn_003",
            "selected_option": "flag",
            "confidence":      0.76,
        })
    # finish() called here by __exit__

    print("Run complete.")


if __name__ == "__main__":
    asyncio.run(main())
