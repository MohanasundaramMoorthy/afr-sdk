#!/usr/bin/env python3
"""
quickstart.py — AFR SDK Quickstart
====================================
Records and verifies a minimal agent run against the AFR runtime.

Usage:
    python quickstart.py

Prerequisites:
    pip install afr-sdk
    node runtime/src/server.js   # AFR runtime on http://localhost:3001
"""

import sys

SERVER = "http://localhost:3001"

BANNER = """
╔══════════════════════════════════════════════════════╗
║           🚀  AFR SDK Quickstart                     ║
║  Ensure the backend is running at http://localhost:3001  ║
╚══════════════════════════════════════════════════════╝
"""


def _ok(msg: str) -> None:
    print(f"  ✅  {msg}")


def _fail(msg: str) -> None:
    print(f"  ❌  {msg}")


def _info(msg: str) -> None:
    print(f"  ⚠️   {msg}")


def main() -> None:
    print(BANNER)

    # ── 1. Import ──────────────────────────────────────────────────────────────
    print("── 1. Importing afr_python_sdk ──────────────────────────────────────")
    try:
        import afr_python_sdk
        from afr_python_sdk import Recorder, AfrClientError
    except ImportError as exc:
        _fail(f"Import failed: {exc}")
        _info("Run:  pip install afr-sdk")
        sys.exit(1)

    _ok("afr_python_sdk imported successfully")
    print(f"     module : {afr_python_sdk.__file__}\n")

    # ── 2. Create recorder ─────────────────────────────────────────────────────
    print("── 2. Creating Recorder ─────────────────────────────────────────────")
    rec = Recorder(base_url=SERVER)
    _ok(f"Recorder initialised  →  {SERVER}\n")

    # ── 3. Start run ───────────────────────────────────────────────────────────
    print("── 3. Starting run ──────────────────────────────────────────────────")
    try:
        run_id = rec.start({
            "model":           "test-model",
            "runtime":         "python",
            "runtime_version": "1.0.0",
        })
    except AfrClientError as exc:
        _fail(f"Server returned HTTP {exc.status}: {exc}")
        _info(f"Is the AFR runtime running at {SERVER}?")
        print("\n  👉  Run:  node runtime/src/server.js\n")
        sys.exit(1)
    except Exception as exc:
        _fail(f"Cannot connect to AFR runtime: {exc}")
        print("\n  👉  Run:  node runtime/src/server.js\n")
        sys.exit(1)

    _ok(f"Run started")
    print(f"     run_id : {run_id}\n")

    # ── 4. Append steps ────────────────────────────────────────────────────────
    print("── 4. Recording steps ───────────────────────────────────────────────")
    try:
        rec.step({
            "step_type":  "model_output",
            "model_name": "test-model",
            "content":    "Analyzing input data for anomalies.",
        })
        _ok("Step 1 recorded  (model_output)")

        rec.step({
            "step_type":       "decision",
            "goal_reference":  "quickstart-goal",
            "selected_option": "pass",
            "confidence":      0.99,
            "reasoning":       "All checks passed during quickstart verification.",
        })
        _ok("Step 2 recorded  (decision)")

    except AfrClientError as exc:
        _fail(f"Failed to append step — HTTP {exc.status}: {exc}")
        sys.exit(1)

    print(f"     steps recorded : {rec.step_count}\n")

    # ── 5. Finish run ──────────────────────────────────────────────────────────
    print("── 5. Completing run ────────────────────────────────────────────────")
    try:
        proof = rec.finish()
    except AfrClientError as exc:
        _fail(f"Failed to complete run — HTTP {exc.status}: {exc}")
        sys.exit(1)

    _ok("Run completed and sealed")
    print(f"     run_id           : {proof.get('run_id')}")
    print(f"     steps in proof   : {len(proof.get('steps', []))}")
    print(f"     replayable       : {proof.get('replayable')}")
    chain_hash = proof.get("final_chain_hash", "")
    print(f"     final_chain_hash : {chain_hash[:24]}{'...' if chain_hash else ''}\n")

    # ── 6. Verify hash chain ───────────────────────────────────────────────────
    print("── 6. Verifying hash chain ──────────────────────────────────────────")
    try:
        result = rec.verify(run_id)
    except AfrClientError as exc:
        _fail(f"Verify call failed — HTTP {exc.status}: {exc}")
        sys.exit(1)

    if result.get("ok"):
        _ok("Hash chain intact — tamper-evident proof is valid\n")
    else:
        _fail(f"Hash chain verification failed: {result.get('error')}\n")
        sys.exit(1)

    # ── 7. Success ─────────────────────────────────────────────────────────────
    print("═" * 56)
    print("  🎉  SUCCESS: AFR SDK is fully working")
    print("  You have recorded and verified an agent run.")
    print("═" * 56 + "\n")


if __name__ == "__main__":
    main()
