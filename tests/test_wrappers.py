"""
Tests for wrappers.py — afr_llm, afr_tool, detect_anomalies.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from unittest.mock import MagicMock, call
from afr_python_sdk.wrappers import afr_llm, afr_tool, detect_anomalies, hash_prompt


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_recorder():
    """Return a mock Recorder with a spy on .step()."""
    recorder = MagicMock()
    recorder.step = MagicMock(return_value={})
    return recorder


# ── afr_llm ───────────────────────────────────────────────────────────────────

class TestAfrLlm:
    def test_calls_fn_with_input(self):
        fn       = MagicMock(return_value="response text")
        recorder = make_recorder()
        result   = afr_llm(recorder, fn, "my prompt")
        fn.assert_called_once_with("my prompt")
        assert result == "response text"

    def test_records_model_output_step(self):
        recorder = make_recorder()
        afr_llm(recorder, lambda x: "hello", "prompt")
        recorder.step.assert_called_once()
        step = recorder.step.call_args[0][0]
        assert step["step_type"] == "model_output"
        assert step["content"]   == "hello"

    def test_hashes_prompt_when_provided(self):
        recorder = make_recorder()
        prompt   = "Classify this."
        afr_llm(recorder, lambda x: "ok", "x", meta={"prompt": prompt})
        step = recorder.step.call_args[0][0]
        assert "prompt_hash" in step
        assert step["prompt_hash"] == hash_prompt(prompt)
        assert len(step["prompt_hash"]) == 64

    def test_raw_prompt_not_stored(self):
        recorder = make_recorder()
        afr_llm(recorder, lambda x: "ok", "x", meta={"prompt": "secret prompt"})
        step = recorder.step.call_args[0][0]
        assert "prompt" not in step
        assert "secret prompt" not in str(step)

    def test_model_name_recorded(self):
        recorder = make_recorder()
        afr_llm(recorder, lambda x: "ok", "x", meta={"model_name": "claude-sonnet-4-6"})
        step = recorder.step.call_args[0][0]
        assert step["model_name"] == "claude-sonnet-4-6"

    def test_temperature_recorded(self):
        recorder = make_recorder()
        afr_llm(recorder, lambda x: "ok", "x", meta={"temperature": 0.2})
        step = recorder.step.call_args[0][0]
        assert step["temperature"] == 0.2

    def test_no_optional_fields_when_meta_empty(self):
        recorder = make_recorder()
        afr_llm(recorder, lambda x: "ok", "x")
        step = recorder.step.call_args[0][0]
        assert "prompt_hash" not in step
        assert "model_name"  not in step
        assert "temperature" not in step

    def test_returns_raw_result_before_recording(self):
        """fn is called first; its result is returned unchanged."""
        calls = []
        def fn(x):
            calls.append("fn_called")
            return "raw"
        recorder = make_recorder()
        def recording_side_effect(*a, **kw):
            calls.append("step_called")
        recorder.step.side_effect = recording_side_effect
        result = afr_llm(recorder, fn, "x")
        assert result == "raw"
        assert calls == ["fn_called", "step_called"]

    def test_rejects_coroutine_fn(self):
        async def async_fn(x): return "x"
        with pytest.raises(TypeError, match="coroutine"):
            afr_llm(make_recorder(), async_fn, "x")

    def test_extracts_content_attribute(self):
        class Resp:
            content = "extracted content"
        recorder = make_recorder()
        afr_llm(recorder, lambda x: Resp(), "x")
        step = recorder.step.call_args[0][0]
        assert step["content"] == "extracted content"

    def test_extracts_text_attribute(self):
        class Resp:
            text = "text content"
        recorder = make_recorder()
        afr_llm(recorder, lambda x: Resp(), "x")
        step = recorder.step.call_args[0][0]
        assert step["content"] == "text content"

    def test_token_usage_anthropic_shape(self):
        class Usage:
            input_tokens  = 100
            output_tokens = 50
        class Resp:
            content = "hi"
            usage   = Usage()
        recorder = make_recorder()
        afr_llm(recorder, lambda x: Resp(), "x")
        step = recorder.step.call_args[0][0]
        assert step["tokens"] == {"input_tokens": 100, "output_tokens": 50}

    def test_token_usage_openai_shape(self):
        class Usage:
            prompt_tokens     = 80
            completion_tokens = 40
        class Resp:
            content = "hi"
            usage   = Usage()
        recorder = make_recorder()
        afr_llm(recorder, lambda x: Resp(), "x")
        step = recorder.step.call_args[0][0]
        assert step["tokens"] == {"input_tokens": 80, "output_tokens": 40}


# ── afr_tool ──────────────────────────────────────────────────────────────────

class TestAfrTool:
    def test_calls_fn_with_input(self):
        fn       = MagicMock(return_value={"score": 0.5})
        recorder = make_recorder()
        result   = afr_tool(recorder, "scorer", fn, {"txn": "001"})
        fn.assert_called_once_with({"txn": "001"})
        assert result == {"score": 0.5}

    def test_records_tool_result_step(self):
        recorder = make_recorder()
        afr_tool(recorder, "risk_score", lambda x: {"p": 0.7}, {"id": "t1"})
        step = recorder.step.call_args[0][0]
        assert step["step_type"]   == "tool_result"
        assert step["tool_name"]   == "risk_score"
        assert step["tool_input"]  == {"id": "t1"}
        assert step["tool_output"] == {"p": 0.7}

    def test_returns_raw_output(self):
        recorder = make_recorder()
        result   = afr_tool(recorder, "t", lambda x: 42, {})
        assert result == 42

    def test_empty_tool_name_raises(self):
        with pytest.raises(ValueError, match="tool_name"):
            afr_tool(make_recorder(), "", lambda x: x, {})

    def test_rejects_coroutine_fn(self):
        async def async_fn(x): return x
        with pytest.raises(TypeError, match="coroutine"):
            afr_tool(make_recorder(), "t", async_fn, {})


# ── detect_anomalies ──────────────────────────────────────────────────────────

def _make_step(step_number, step_type):
    return {"step_number": step_number, "step_type": step_type}


class TestDetectAnomalies:
    def _proof(self, steps):
        return {"steps": [_make_step(i + 1, t) for i, t in enumerate(steps)]}

    def test_empty_proof_no_anomalies(self):
        assert detect_anomalies({"steps": []}) == []

    def test_no_model_output(self):
        proof = self._proof(["planning", "tool_result", "decision_evaluation"])
        codes = [a["code"] for a in detect_anomalies(proof)]
        assert "missing_expected_steps" in codes

    def test_tool_before_planning(self):
        proof = self._proof(["tool_result", "planning"])
        codes = [a["code"] for a in detect_anomalies(proof)]
        assert "step_sequence_anomaly" in codes

    def test_decision_without_tools(self):
        proof = self._proof(["planning", "model_output", "decision_evaluation"])
        codes = [a["code"] for a in detect_anomalies(proof)]
        assert "decision_without_tools" in codes

    def test_decision_without_model(self):
        proof = self._proof(["planning", "tool_result", "decision_evaluation"])
        codes = [a["code"] for a in detect_anomalies(proof)]
        assert "decision_without_model" in codes

    def test_multiple_decisions(self):
        proof = self._proof(["planning", "model_output", "tool_result",
                              "decision_evaluation", "decision_evaluation"])
        codes = [a["code"] for a in detect_anomalies(proof)]
        assert "multiple_decisions" in codes

    def test_summary_before_decision(self):
        proof = self._proof(["planning", "model_output", "tool_result",
                              "summary", "decision_evaluation"])
        codes = [a["code"] for a in detect_anomalies(proof)]
        assert "summary_before_decision" in codes

    def test_clean_run_no_anomalies(self):
        proof = self._proof(["planning", "model_output", "tool_result",
                              "decision_evaluation", "summary"])
        assert detect_anomalies(proof) == []

    def test_step_numbers_in_anomaly(self):
        proof = self._proof(["planning", "tool_result", "decision_evaluation"])
        anomalies = detect_anomalies(proof)
        decision_anom = next(a for a in anomalies if a["code"] == "decision_without_model")
        assert "step_numbers" in decision_anom
        assert decision_anom["step_numbers"] == [3]
