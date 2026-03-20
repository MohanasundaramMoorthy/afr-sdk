"""
Tests for utils.py — canonical_stringify and hash_prompt.
Verifies byte-identical output to protocol-core/canonicalStringify.js.

Run:
    pip install pytest
    pytest afr_python_sdk/tests/
"""

import math
import pytest

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from afr_python_sdk.utils import canonical_stringify, sort_keys, hash_prompt, compute_step_hash


class TestSortKeys:
    def test_scalars_unchanged(self):
        assert sort_keys(1)      == 1
        assert sort_keys("hi")   == "hi"
        assert sort_keys(True)   == True
        assert sort_keys(None)   is None

    def test_dict_keys_sorted(self):
        result = sort_keys({"b": 2, "a": 1})
        assert list(result.keys()) == ["a", "b"]

    def test_nested_dict_sorted(self):
        result = sort_keys({"z": {"y": 1, "x": 2}, "a": 0})
        assert list(result.keys()) == ["a", "z"]
        assert list(result["z"].keys()) == ["x", "y"]

    def test_array_order_preserved(self):
        result = sort_keys([3, 1, 2])
        assert result == [3, 1, 2]

    def test_array_of_dicts(self):
        result = sort_keys([{"b": 2, "a": 1}, {"d": 4, "c": 3}])
        assert list(result[0].keys()) == ["a", "b"]
        assert list(result[1].keys()) == ["c", "d"]

    def test_nan_raises(self):
        with pytest.raises(TypeError, match="non-finite"):
            sort_keys(float("nan"))

    def test_inf_raises(self):
        with pytest.raises(TypeError, match="non-finite"):
            sort_keys(float("inf"))

    def test_neg_inf_raises(self):
        with pytest.raises(TypeError, match="non-finite"):
            sort_keys(float("-inf"))

    def test_nested_nan_raises(self):
        with pytest.raises(TypeError, match="non-finite"):
            sort_keys({"a": {"b": float("nan")}})


class TestCanonicalStringify:
    """
    Expected outputs computed by running JSON.stringify(sortKeys(value))
    in Node.js with the protocol-core implementation.
    """

    def test_empty_dict(self):
        assert canonical_stringify({}) == "{}"

    def test_simple_dict_sorted(self):
        # JS: JSON.stringify(sortKeys({b:2,a:1})) === '{"a":1,"b":2}'
        assert canonical_stringify({"b": 2, "a": 1}) == '{"a":1,"b":2}'

    def test_nested(self):
        val = {"z": {"b": 2, "a": 1}, "a": [3, 1, 2]}
        # JS result: '{"a":[3,1,2],"z":{"a":1,"b":2}}'
        assert canonical_stringify(val) == '{"a":[3,1,2],"z":{"a":1,"b":2}}'

    def test_string_values(self):
        assert canonical_stringify({"b": "world", "a": "hello"}) == '{"a":"hello","b":"world"}'

    def test_null_value(self):
        assert canonical_stringify({"a": None}) == '{"a":null}'

    def test_bool_values(self):
        # Python True/False → JSON true/false
        assert canonical_stringify({"b": False, "a": True}) == '{"a":true,"b":false}'

    def test_integer(self):
        assert canonical_stringify(42) == "42"

    def test_float(self):
        # 0.2 must round-trip stably
        result = canonical_stringify(0.2)
        assert result == "0.2"

    def test_no_spaces(self):
        # Must use compact separators — no spaces after : or ,
        result = canonical_stringify({"a": 1, "b": 2})
        assert " " not in result

    def test_execution_context_shape(self):
        # Representative execution_context — keys must sort alphabetically
        ctx = {
            "model":           "claude-sonnet-4-6",
            "runtime_version": "1.0.0",
            "system_prompt":   "You are a fraud detection agent.",
            "temperature":     0.2,
            "tools":           [{"name": "risk_score"}],
            "top_p":           0.9,
        }
        result = canonical_stringify(ctx)
        parsed = __import__("json").loads(result)
        assert list(parsed.keys()) == sorted(parsed.keys())
        # Tools array is preserved as-is (no sorting of array elements)
        assert parsed["tools"] == [{"name": "risk_score"}]


class TestHashPrompt:
    def test_returns_64_hex_chars(self):
        result = hash_prompt("hello")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_known_value(self):
        # SHA-256("") = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
        assert hash_prompt("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def test_deterministic(self):
        assert hash_prompt("test") == hash_prompt("test")

    def test_different_inputs_differ(self):
        assert hash_prompt("a") != hash_prompt("b")

    def test_no_prefix(self):
        # Must NOT include "sha256:" prefix — validator expects raw 64-char hex
        result = hash_prompt("prompt text")
        assert not result.startswith("sha256:")


class TestComputeStepHash:
    def test_matches_algorithm(self):
        import hashlib
        previous_hash  = "GENESIS"
        step_for_hash  = {"content": "hello", "step_type": "planning"}
        payload        = previous_hash + canonical_stringify(step_for_hash)
        expected       = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        assert compute_step_hash(previous_hash, step_for_hash) == expected

    def test_key_order_independent(self):
        # Different key order must produce same hash (keys sorted by canonical_stringify)
        h1 = compute_step_hash("GENESIS", {"b": 2, "a": 1})
        h2 = compute_step_hash("GENESIS", {"a": 1, "b": 2})
        assert h1 == h2
