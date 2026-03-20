"""
AFR HTTP Client — Python SDK
==============================
Low-level HTTP client for the Agent Flight Recorder runtime API.
Mirrors agent-sdk/client.js exactly.

Requires:
  pip install requests

Usage:
  from afr_python_sdk.client import Client, AfrClientError

  client = Client(base_url="http://localhost:3000")
  run    = client.create_run()                # non-replayable
  run    = client.create_run(execution_context={...})  # replayable
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

try:
    import requests as _requests
except ImportError as _e:  # pragma: no cover
    raise ImportError(
        "afr_python_sdk requires 'requests'. Install it with:  pip install requests"
    ) from _e


# ── Exceptions ────────────────────────────────────────────────────────────────

class AfrClientError(Exception):
    """
    Raised when the AFR runtime API returns an HTTP error.

    Attributes
    ----------
    status : int
        HTTP status code returned by the server
    """
    def __init__(self, message: str, status: int) -> None:
        super().__init__(message)
        self.status = status


# ── Client ────────────────────────────────────────────────────────────────────

class Client:
    """
    Low-level HTTP client for the AFR runtime API.
    Mirrors agent-sdk/client.js method-for-method.

    Parameters
    ----------
    base_url : str
        Runtime server URL, e.g. "http://localhost:3000"
    timeout  : float
        Request timeout in seconds (default: 30)
    """

    def __init__(self, base_url: str, timeout: float = 30.0, api_key: Optional[str] = None) -> None:
        if not base_url:
            raise ValueError("base_url is required")
        self.base_url = base_url.rstrip("/")
        self.timeout  = timeout
        self._session = _requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})
        resolved_key = api_key if api_key is not None else os.environ.get("AFR_API_KEY")
        if resolved_key:
            self._session.headers.update({"x-api-key": resolved_key})

    # ── Internal ─────────────────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"

        response = self._session.request(
            method=method,
            url=url,
            json=body,          # None → no body sent
            timeout=self.timeout,
        )

        try:
            data: Dict[str, Any] = response.json()
        except Exception:
            data = {}

        if not response.ok:
            msg = data.get("error") if isinstance(data, dict) else str(data)
            raise AfrClientError(
                msg or f"Request failed ({response.status_code})",
                response.status_code,
            )

        return data

    # ── API methods ───────────────────────────────────────────────────────────

    def create_run(
        self,
        execution_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new run. Returns {"run_id": str}.

        Mirrors client.js createRun():
          Always sends {"execution_context": <value>} — even when None.
          When execution_context is provided the run is replay-verifiable.
          When None the run is non-replayable (backward compatible).

        execution_context shape (when provided):
          {
            "model":           "claude-sonnet-4-6",
            "model_version":   "20250514",        # optional
            "system_prompt":   "You are ...",
            "temperature":     0.2,
            "top_p":           0.9,
            "runtime_version": "1.0.0",
            "tools":           [{"name": "risk_score"}],
          }
        """
        # Always include the key, even when None — mirrors client.js exactly.
        # The existing python_sdk sent {} when None; that left execution_context
        # absent from the body, which the server treated as non-replayable but
        # also prevented a null context_hash from being stored consistently.
        return self._request("POST", "/runs", {"execution_context": execution_context})

    def append_step(
        self,
        run_id: str,
        step_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Append a step to an active run."""
        return self._request("POST", f"/runs/{run_id}/steps", step_data)

    def complete_run(self, run_id: str) -> Dict[str, Any]:
        """Complete and seal a run."""
        return self._request("POST", f"/runs/{run_id}/complete")

    def fail_run(self, run_id: str) -> Dict[str, Any]:
        """Fail a run."""
        return self._request("POST", f"/runs/{run_id}/fail")

    def verify_run(self, run_id: str) -> Dict[str, Any]:
        """Verify hash chain integrity. Returns {"ok": bool, "error"?: str}."""
        return self._request("GET", f"/runs/{run_id}/verify")

    def get_proof(self, run_id: str) -> Dict[str, Any]:
        """Get the cryptographic .afr proof artifact."""
        return self._request("GET", f"/runs/{run_id}/proof")

    def close(self) -> None:
        """Close the underlying requests.Session."""
        self._session.close()

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
