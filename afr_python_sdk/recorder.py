"""
AFR Recorder — Python SDK
===========================
High-level stateful recorder for a single agent run.
Mirrors agent-sdk/recorder.js method-for-method.

Usage — basic:
    from afr_python_sdk.recorder import Recorder

    recorder = Recorder(base_url="http://localhost:3000")
    recorder.start()

    recorder.step({"step_type": "planning", "goal_reference": "fraud_check"})
    recorder.decision({
        "goal_reference": "fraud_check",
        "selected_option": "block",
        "confidence": 0.91,
    })

    proof = recorder.finish()

Usage — replay-verifiable run:
    recorder.start(execution_context={
        "model":           "claude-sonnet-4-6",
        "model_version":   "20250514",
        "system_prompt":   "You are a fraud detection agent.",
        "temperature":     0.2,
        "top_p":           0.9,
        "runtime_version": "1.0.0",
        "tools": [{"name": "risk_score"}, {"name": "transaction_history"}],
    })

Usage — context manager (auto-finish / abort):
    with Recorder(base_url="http://localhost:3000") as recorder:
        recorder.start()
        recorder.step(...)
        recorder.decision(...)
    # finish() called automatically; abort() on exception
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .client import Client


class Recorder:
    """
    High-level stateful recorder for a single agent run.

    Thread-safety: not thread-safe. Use one Recorder per thread/coroutine.

    Parameters
    ----------
    base_url : str
        Runtime server URL, e.g. "http://localhost:3000"
    timeout  : float
        HTTP request timeout in seconds (default: 30)
    """

    def __init__(self, base_url: str, timeout: float = 30.0, api_key: Optional[str] = None) -> None:
        self._client     = Client(base_url, timeout=timeout, api_key=api_key)
        self._run_id:    Optional[str] = None
        self._step_count = 0

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(
        self,
        execution_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Start a new run on the recorder.

        Mirrors recorder.js start():
          Pass execution_context to produce a replay-verifiable proof.
          Omit or pass None for a non-replayable run (backward compatible).

        Parameters
        ----------
        execution_context : dict or None
            Model configuration for a replayable run. Shape:
              {
                "model":           str,   # e.g. "claude-sonnet-4-6"
                "model_version":   str,   # optional
                "system_prompt":   str,
                "temperature":     float,
                "top_p":           float,
                "runtime_version": str,
                "tools":           list[{"name": str}],
              }

        Returns
        -------
        str
            The run_id assigned by the runtime.
        """
        data             = self._client.create_run(execution_context)
        self._run_id     = data["run_id"]
        self._step_count = 0
        return self._run_id

    def step(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Append a generic step to the active run.

        Mirrors recorder.js step():
          step_data must include step_type.
          Unlike the existing python_sdk, this does NOT inject step_schema_version —
          the runtime injects it server-side, matching Node SDK behaviour.

        Parameters
        ----------
        step_data : dict
            Must include "step_type". All other fields are step-type specific.

        Returns
        -------
        dict
            The recorded step as returned by the runtime.
        """
        self._assert_started()
        if "step_type" not in step_data:
            raise ValueError("step_type is required")
        self._step_count += 1
        return self._client.append_step(self._run_id, step_data)  # type: ignore[arg-type]

    def decision(self, decision_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Append a decision_evaluation step (thin wrapper).

        Convenience wrapper that sets step_type = "decision_evaluation".
        For the simplified builder interface use decision_evaluation().

        Parameters
        ----------
        decision_data : dict
            Must include goal_reference and selected_option at minimum.
        """
        return self.step({"step_type": "decision_evaluation", **decision_data})

    def decision_evaluation(
        self,
        *,
        goal: str,
        options: list,
        selected: str,
        confidence: float,
        reasoning: str,
        risk: Dict[str, str],
        scores: Optional[Dict[str, Dict[str, float]]] = None,
        trigger: str = "agent_decision",
    ) -> Dict[str, Any]:
        """
        Append a decision_evaluation step using the simplified builder shape.

        Mirrors recorder.js decision() builder path.  Builds the full
        decision_evaluation schema internally so callers only supply
        the essential details.

        Parameters
        ----------
        goal      : Goal reference string, e.g. "approve_or_deny_loan"
        options   : List of option IDs, e.g. ["approve", "deny"]
        selected  : The chosen option_id
        confidence: Confidence score 0-1
        reasoning : Human-readable explanation for the decision
        risk      : {"level": "low"|"medium"|"high", "reason": str}
        scores    : Optional dict mapping option_id → {criterion: score}.
                    If omitted, defaults to {"agent_confidence": ...}.
        trigger   : decision_context.trigger (default "agent_decision")

        Returns
        -------
        dict
            The recorded step as returned by the runtime.

        Example
        -------
        recorder.decision_evaluation(
            goal="approve_or_deny_loan",
            options=["approve", "deny"],
            selected="approve",
            confidence=0.87,
            reasoning="Credit score above threshold with low fraud risk.",
            risk={"level": "low", "reason": "Score below threshold"},
        )
        """
        if not goal:
            raise ValueError("decision_evaluation: goal is required")
        if not options:
            raise ValueError("decision_evaluation: options must be a non-empty list")
        if not selected:
            raise ValueError("decision_evaluation: selected is required")
        if confidence is None:
            raise ValueError("decision_evaluation: confidence is required")
        if not reasoning:
            raise ValueError("decision_evaluation: reasoning is required")
        if not risk or not risk.get("level") or not risk.get("reason"):
            raise ValueError("decision_evaluation: risk.level and risk.reason are required")

        alternatives = [{"option_id": o, "label": o, "metadata": {}} for o in options]
        rejected_options = [
            {"option_id": o, "reason_code": "not_selected"}
            for o in options if o != selected
        ]

        if scores is not None:
            evaluation_criteria = list(next(iter(scores.values())).keys())
            evaluation_scores   = scores
        else:
            evaluation_criteria = ["agent_confidence"]
            evaluation_scores   = {
                o: {"agent_confidence": confidence if o == selected else 0.0}
                for o in options
            }

        return self.step({
            "step_type":           "decision_evaluation",
            "goal_reference":      goal,
            "decision_context":    {"description": reasoning, "trigger": trigger},
            "alternatives":        alternatives,
            "evaluation_criteria": evaluation_criteria,
            "evaluation_scores":   evaluation_scores,
            "selected_option":     selected,
            "rejected_options":    rejected_options,
            "confidence":          confidence,
            "risk_assessment":     {"risk_level": risk["level"], "risk_reason": risk["reason"]},
        })

    def finish(self) -> Dict[str, Any]:
        """
        Complete the run, seal it, and return the .afr proof artifact.

        Mirrors recorder.js finish():
          After finish() the recorder is reset and can be reused with start().

        Returns
        -------
        dict
            The .afr proof artifact returned by the runtime.
        """
        self._assert_started()
        self._client.complete_run(self._run_id)  # type: ignore[arg-type]
        proof            = self._client.get_proof(self._run_id)  # type: ignore[arg-type]
        self._run_id     = None
        self._step_count = 0
        return proof

    def abort(self) -> Dict[str, Any]:
        """
        Fail the active run (e.g. on exception).

        Safe to call even if the run has already ended — the server is idempotent.

        Returns
        -------
        dict
            Server response.
        """
        self._assert_started()
        result           = self._client.fail_run(self._run_id)  # type: ignore[arg-type]
        self._run_id     = None
        self._step_count = 0
        return result

    def verify(self, run_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify hash chain integrity for the current or a named run.

        Mirrors recorder.js verify():
          Can be called on any completed run by passing run_id explicitly.

        Returns
        -------
        dict
            {"ok": bool, "error"?: str}
        """
        target = run_id or self._run_id
        if not target:
            raise RuntimeError("No run_id — call start() or pass run_id explicitly.")
        return self._client.verify_run(target)

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def run_id(self) -> Optional[str]:
        """The active run_id, or None if no run is in progress."""
        return self._run_id

    @property
    def step_count(self) -> int:
        """Number of steps appended in the current run."""
        return self._step_count

    # ── Context manager ───────────────────────────────────────────────────────

    def __enter__(self) -> "Recorder":
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any,
    ) -> bool:
        if self._run_id:
            if exc_type is not None:
                try:
                    self.abort()
                except Exception:
                    pass
            else:
                self.finish()
        return False  # never suppress exceptions

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._client.close()

    # ── Internal ─────────────────────────────────────────────────────────────

    def _assert_started(self) -> None:
        if not self._run_id:
            raise RuntimeError("Recorder not started. Call start() first.")
