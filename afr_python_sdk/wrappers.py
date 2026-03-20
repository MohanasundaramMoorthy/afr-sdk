"""
AFR Trusted Wrappers — Python SDK
====================================
Mirrors agent-sdk/wrappers.js exactly.

TRUST MODEL
-----------
AFR provides tamper-evidence, NOT ground truth.

These wrappers call the real function first, capture the raw result before any
transformation, then record immediately. The guarantee is:

  "Whatever the function returned was recorded without modification."

What is NOT guaranteed:
  - The function actually called the model it claimed to
  - The model identity matches execution_context.model

See README: Trust Model section.

Usage — sync:
    from afr_python_sdk.wrappers import afr_llm, afr_tool

    response = afr_llm(
        recorder,
        call_claude,               # callable; must be sync (not async)
        prompt,                    # positional arg forwarded to call_claude
        meta={
            "prompt":      prompt,                # raw text; hashed before storage
            "model_name":  "claude-sonnet-4-6",
            "temperature": 0.2,
        },
    )

    result = afr_tool(recorder, "risk_score", run_risk_score, tool_input)

Usage — async:
    response = await afr_llm_async(recorder, call_claude_async, prompt, meta={...})
    result   = await afr_tool_async(recorder, "risk_score", run_risk_async, input)
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, Dict, List, Optional

from .recorder import Recorder
from .utils    import hash_prompt as _hash_prompt


# ── Re-export hash_prompt so callers can import from one place ────────────────

hash_prompt = _hash_prompt


# ── afr_llm ──────────────────────────────────────────────────────────────────

def afr_llm(
    recorder: Recorder,
    fn: Callable[..., Any],
    input: Any,
    meta: Optional[Dict[str, Any]] = None,
) -> Any:
    """
    Wrap a synchronous LLM call and record its output as a model_output step.

    Mirrors afrLLM() in agent-sdk/wrappers.js.

    The function is called first. The raw return value is captured before any
    transformation, then model_output is appended to the run.

    Parameters
    ----------
    recorder : Recorder
        Active recorder (start() must have been called).
    fn       : callable
        The LLM function to call. Must be synchronous.
        Raise TypeError for coroutine functions — use afr_llm_async instead.
    input    : any
        Positional argument forwarded to fn.
    meta     : dict, optional
        Recording metadata. Supported keys:
          prompt      (str)   — raw prompt text; SHA-256 hashed before storage
          model_name  (str)   — model identifier, e.g. "claude-sonnet-4-6"
          temperature (float) — sampling temperature

    Returns
    -------
    any
        The raw return value of fn (unchanged).

    Raises
    ------
    TypeError  if fn is a coroutine function
    """
    if inspect.iscoroutinefunction(fn):
        raise TypeError(
            "afr_llm: fn is a coroutine function. Use afr_llm_async() for async functions."
        )

    result = fn(input)

    _record_model_output(recorder, result, meta or {})
    return result


async def afr_llm_async(
    recorder: Recorder,
    fn: Callable[..., Any],
    input: Any,
    meta: Optional[Dict[str, Any]] = None,
) -> Any:
    """
    Async variant of afr_llm for use with async LLM clients.

    Parameters
    ----------
    recorder : Recorder
    fn       : async callable
    input    : any
    meta     : dict, optional — same keys as afr_llm

    Returns
    -------
    any
        Raw return value of fn (unchanged).
    """
    result = await fn(input)
    _record_model_output(recorder, result, meta or {})
    return result


def _record_model_output(
    recorder: Recorder,
    result: Any,
    meta: Dict[str, Any],
) -> None:
    """Extract content from result and append a model_output step."""
    # Extract text content from common LLM SDK response shapes
    if isinstance(result, str):
        content = result
    elif hasattr(result, "content"):
        content = str(result.content)
    elif hasattr(result, "text"):
        content = str(result.text)
    elif hasattr(result, "output"):
        content = str(result.output)
    elif isinstance(result, dict):
        content = (
            result.get("content")
            or result.get("text")
            or result.get("output")
            or str(result)
        )
    else:
        content = str(result)

    # Extract token usage (Anthropic / OpenAI response shapes)
    tokens:  Optional[Dict[str, int]] = None
    usage_src = (
        getattr(result, "usage", None)
        if not isinstance(result, dict)
        else result.get("usage")
    )
    if usage_src is not None:
        if isinstance(usage_src, dict):
            raw_in  = usage_src.get("input_tokens")  or usage_src.get("prompt_tokens")
            raw_out = usage_src.get("output_tokens") or usage_src.get("completion_tokens")
        else:
            raw_in  = getattr(usage_src, "input_tokens",  None) or getattr(usage_src, "prompt_tokens",     None)
            raw_out = getattr(usage_src, "output_tokens", None) or getattr(usage_src, "completion_tokens", None)
        if raw_in is not None or raw_out is not None:
            tokens = {}
            if raw_in  is not None: tokens["input_tokens"]  = int(raw_in)
            if raw_out is not None: tokens["output_tokens"] = int(raw_out)

    # Build step — only include optional fields when present
    prompt_text: Optional[str]   = meta.get("prompt")
    model_name:  Optional[str]   = meta.get("model_name")
    temperature: Optional[float] = meta.get("temperature")

    step_data: Dict[str, Any] = {"step_type": "model_output", "content": content}
    if prompt_text  is not None: step_data["prompt_hash"]  = _hash_prompt(prompt_text)
    if model_name   is not None: step_data["model_name"]   = model_name
    if temperature  is not None: step_data["temperature"]  = temperature
    if tokens       is not None: step_data["tokens"]       = tokens

    recorder.step(step_data)


# ── afr_tool ─────────────────────────────────────────────────────────────────

def afr_tool(
    recorder: Recorder,
    tool_name: str,
    fn: Callable[..., Any],
    input: Any,
) -> Any:
    """
    Wrap a synchronous tool call and record its I/O as a tool_result step.

    Mirrors afrTool() in agent-sdk/wrappers.js.

    The function is called first. The raw output is captured immediately
    before the step is recorded.

    Parameters
    ----------
    recorder  : Recorder
        Active recorder (start() must have been called).
    tool_name : str
        Tool identifier (recorded verbatim as tool_name).
    fn        : callable
        The tool function. Receives input as its sole positional argument.
    input     : any
        Input passed to fn and recorded as tool_input.

    Returns
    -------
    any
        The raw return value of fn (unchanged).
    """
    if not tool_name or not isinstance(tool_name, str):
        raise ValueError("afr_tool: tool_name must be a non-empty string")
    if inspect.iscoroutinefunction(fn):
        raise TypeError(
            "afr_tool: fn is a coroutine function. Use afr_tool_async() for async functions."
        )

    output = fn(input)

    recorder.step({
        "step_type":   "tool_result",
        "tool_name":   tool_name,
        "tool_input":  input,
        "tool_output": output,
    })

    return output


async def afr_tool_async(
    recorder: Recorder,
    tool_name: str,
    fn: Callable[..., Any],
    input: Any,
) -> Any:
    """
    Async variant of afr_tool.

    Parameters
    ----------
    recorder  : Recorder
    tool_name : str
    fn        : async callable
    input     : any

    Returns
    -------
    any
        Raw return value of fn (unchanged).
    """
    if not tool_name or not isinstance(tool_name, str):
        raise ValueError("afr_tool_async: tool_name must be a non-empty string")

    output = await fn(input)

    recorder.step({
        "step_type":   "tool_result",
        "tool_name":   tool_name,
        "tool_input":  input,
        "tool_output": output,
    })

    return output


# ── Anomaly detection ─────────────────────────────────────────────────────────

def detect_anomalies(proof: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Analyse a completed proof for step-sequence anomalies.

    Mirrors detectAnomalies() in agent-sdk/wrappers.js.
    Returns a list of anomaly dicts. Empty list means no anomalies.

    Anomaly codes
    -------------
    missing_expected_steps   — no model_output steps recorded
    step_sequence_anomaly    — tool_result before any planning step
    decision_without_tools   — decision with no preceding tool_result
    decision_without_model   — decision with no preceding model_output
    multiple_decisions       — more than one decision_evaluation step
    summary_before_decision  — summary step appears before decision_evaluation

    Parameters
    ----------
    proof : dict
        Parsed .afr proof object (or any dict with a "steps" key).

    Returns
    -------
    list[dict]
        Each anomaly: {"code": str, "message": str, "step_numbers"?: list[int]}
    """
    anomalies: List[Dict[str, Any]] = []
    steps = proof.get("steps", [])
    if not steps:
        return anomalies

    types = [s["step_type"] for s in steps]

    def _step_nums(indices: List[int]) -> List[int]:
        return [steps[i]["step_number"] for i in indices]

    # 1. No model_output steps
    if "model_output" not in types:
        anomalies.append({
            "code":    "missing_expected_steps",
            "message": "No model_output steps recorded. LLM calls may be untracked.",
        })

    # 2. tool_result before any planning
    first_plan = next((i for i, t in enumerate(types) if t == "planning"),    None)
    first_tool = next((i for i, t in enumerate(types) if t == "tool_result"), None)
    if first_tool is not None and (first_plan is None or first_tool < first_plan):
        anomalies.append({
            "code":         "step_sequence_anomaly",
            "message":      "tool_result step appears before any planning step.",
            "step_numbers": _step_nums([first_tool]),
        })

    # 3. decision without preceding tool_result or model_output
    decision_indices = [i for i, t in enumerate(types) if t == "decision_evaluation"]
    for di in decision_indices:
        preceding = types[:di]
        if "tool_result" not in preceding:
            anomalies.append({
                "code":         "decision_without_tools",
                "message":      f"Decision at step {steps[di]['step_number']} has no preceding tool_result steps.",
                "step_numbers": _step_nums([di]),
            })
        if "model_output" not in preceding:
            anomalies.append({
                "code":         "decision_without_model",
                "message":      f"Decision at step {steps[di]['step_number']} has no preceding model_output steps.",
                "step_numbers": _step_nums([di]),
            })

    # 4. Multiple decisions
    if len(decision_indices) > 1:
        anomalies.append({
            "code":         "multiple_decisions",
            "message":      f"Run contains {len(decision_indices)} decision_evaluation steps. Expected at most 1.",
            "step_numbers": _step_nums(decision_indices),
        })

    # 5. summary before decision
    first_decision = next((i for i, t in enumerate(types) if t == "decision_evaluation"), None)
    first_summary  = next((i for i, t in enumerate(types) if t == "summary"),             None)
    if first_summary is not None and first_decision is not None and first_summary < first_decision:
        anomalies.append({
            "code":         "summary_before_decision",
            "message":      "summary step appears before decision_evaluation.",
            "step_numbers": _step_nums([first_summary]),
        })

    return anomalies
