#!/usr/bin/env python3
"""
verify_install.py — End-to-end smoke test for the afr-sdk package.

Run:
    python verify_install.py

Requires the AFR runtime running at http://localhost:3001.
"""

import sys

SERVER = "http://localhost:3001"

# ── Step 1: Import check ───────────────────────────────────────────────────────

print("\n🚀 afr-sdk installation verifier\n")

try:
    import afr_python_sdk
    from afr_python_sdk import Recorder, AfrClientError
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("   Run:  pip install afr-sdk  or  pip install -e .")
    sys.exit(1)

print(f"✅ afr_python_sdk imported successfully")
print(f"   Location : {afr_python_sdk.__file__}")
print(f"   Exports  : Recorder, Client, AfrClientError\n")

# ── Step 2: Connect and start a run ───────────────────────────────────────────

rec = Recorder(base_url=SERVER)

try:
    run_id = rec.start({
        "model":           "test-model",
        "runtime":         "python",
        "runtime_version": "1.0.0",
    })
except AfrClientError as e:
    print(f"❌ Server returned HTTP {e.status}: {e}")
    print(f"   Check that the AFR runtime is running at {SERVER}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Could not reach server at {SERVER}: {e}")
    print(f"   Make sure the AFR runtime is running on localhost:3001")
    sys.exit(1)

print(f"✅ Run started")
print(f"   run_id : {run_id}\n")

# ── Step 3: Append steps ───────────────────────────────────────────────────────

try:
    rec.step({
        "step_type":  "model_output",
        "model_name": "test-model",
        "content":    "Analyzing input data for anomalies.",
    })
    print(f"✅ Step 1 recorded  (model_output)")

    rec.step({
        "step_type":        "decision",
        "goal_reference":   "verify-sdk",
        "selected_option":  "pass",
        "confidence":       0.99,
        "reasoning":        "All checks succeeded.",
    })
    print(f"✅ Step 2 recorded  (decision)")

except AfrClientError as e:
    print(f"❌ Failed to append step — HTTP {e.status}: {e}")
    sys.exit(1)

print(f"\n   Steps recorded: {rec.step_count}\n")

# ── Step 4: Complete run and retrieve proof ────────────────────────────────────

try:
    proof = rec.finish()
except AfrClientError as e:
    print(f"❌ Failed to complete run — HTTP {e.status}: {e}")
    sys.exit(1)

print(f"✅ Run completed and sealed")
print(f"   run_id           : {proof.get('run_id')}")
print(f"   steps            : {len(proof.get('steps', []))}")
print(f"   replayable       : {proof.get('replayable')}")
print(f"   final_chain_hash : {proof.get('final_chain_hash', '')[:20]}...")

# ── Step 5: Verify hash chain ─────────────────────────────────────────────────

try:
    result = rec.verify(run_id)
    if result.get("ok"):
        print(f"✅ Hash chain verified — tamper-evident proof is intact\n")
    else:
        print(f"❌ Hash chain verification failed: {result.get('error')}\n")
        sys.exit(1)
except AfrClientError as e:
    print(f"❌ Verify call failed — HTTP {e.status}: {e}\n")
    sys.exit(1)

print("✅ All checks passed — SDK is installed and working correctly.\n")
