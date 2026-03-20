"""
AFR Canonical Utilities — Python SDK
=====================================
Mirrors protocol-core/canonicalStringify.js exactly.

Rules (single source of truth — keep in sync with JS):
  - Object keys sorted alphabetically (recursive)
  - Array order preserved
  - NaN / ±Infinity rejected with TypeError (JSON.stringify silently drops them)
  - float representation: json.dumps with no trailing whitespace (separators=(',',':'))

These utilities are used for:
  - Offline proof verification (recompute step hashes locally)
  - Canonical JSON generation matching the runtime's hash inputs
"""

import hashlib
import json
import math
from typing import Any


# ── Canonical JSON serialization ──────────────────────────────────────────────

def sort_keys(value: Any, path: str = "") -> Any:
    """
    Recursively sort object keys alphabetically.

    Mirrors sortKeys() in protocol-core/canonicalStringify.js:
      - None  → None
      - scalar → unchanged
      - list  → items recurse, order preserved
      - dict  → keys sorted alphabetically, values recurse
      - float NaN / ±Infinity → TypeError

    Parameters
    ----------
    value : any JSON-compatible value
    path  : dot-notation path used in error messages
    """
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        raise TypeError(
            f'canonical_stringify: non-finite number at "{path}" ({value}). '
            f'NaN and Infinity cannot be represented in JSON.'
        )

    if value is None:
        return None

    if isinstance(value, list):
        return [
            sort_keys(item, f"{path}[{i}]")
            for i, item in enumerate(value)
        ]

    if isinstance(value, dict):
        sorted_keys = sorted(value.keys())
        return {
            k: sort_keys(value[k], f"{path}.{k}" if path else k)
            for k in sorted_keys
        }

    return value


def canonical_stringify(value: Any) -> str:
    """
    Deterministic JSON serialization with recursively sorted keys.

    Mirrors canonicalStringify() in protocol-core/canonicalStringify.js:
      - Calls sort_keys() first
      - Uses compact separators (no spaces) matching JS JSON.stringify
      - Throws TypeError if any float is NaN or ±Infinity

    Parameters
    ----------
    value : any JSON-compatible value

    Returns
    -------
    str
        Deterministic JSON string (compact, no whitespace)
    """
    return json.dumps(sort_keys(value), separators=(',', ':'), ensure_ascii=False)


# ── Prompt hashing ────────────────────────────────────────────────────────────

def hash_prompt(text: str) -> str:
    """
    Hash a prompt string to a 64-character lowercase hex SHA-256 digest.

    Mirrors hashPrompt() in agent-sdk/wrappers.js.
    The raw prompt is never stored — only the digest is written as prompt_hash.

    Parameters
    ----------
    text : str
        Raw prompt text to hash

    Returns
    -------
    str
        64-character lowercase hex string (SHA-256 digest)

    Examples
    --------
    >>> hash_prompt("Classify this document.")
    'a7f3c...'  # 64 hex chars
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ── Step hash recomputation (for offline verification) ────────────────────────

def compute_step_hash(previous_hash: str, step_for_hash: dict) -> str:
    """
    Recompute a step hash for offline verification.

    Mirrors computeStepHash() in protocol-core/hashChain.js:
      step_hash = SHA256(previous_hash + canonical_stringify(step_for_hash))

    The step_for_hash dict must NOT include previous_hash or step_hash fields
    (strip them before passing, exactly as the verifier does).

    Parameters
    ----------
    previous_hash  : str  SHA-256 hex of the preceding step (or context_hash / "GENESIS")
    step_for_hash  : dict Step fields excluding previous_hash and step_hash

    Returns
    -------
    str
        SHA-256 hex digest
    """
    payload = previous_hash + canonical_stringify(step_for_hash)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
