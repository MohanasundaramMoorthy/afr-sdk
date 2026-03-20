# AFR SDK — Tamper-Evident AI Agent Execution

> Record, replay, and verify AI agent decisions with cryptographic integrity.

[![PyPI version](https://img.shields.io/pypi/v/afr-sdk.svg)](https://pypi.org/project/afr-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/afr-sdk.svg)](https://pypi.org/project/afr-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## The problem

AI agents make consequential decisions — blocking transactions, approving requests, triggering actions. When something goes wrong, you need to answer two questions:

1. **What exactly did the agent do?**
2. **Can you prove the log wasn't altered after the fact?**

Observability tools like LangSmith and AgentOps answer question 1. None of them answer question 2.

**AFR answers both.**

Every step the agent takes is recorded into a SHA-256 hash chain. The chain is sealed with an Ed25519 signature and exported as a self-contained proof artifact. Alter a single step — or delete one — and verification fails. No trust required.

```python
from afr_python_sdk import Recorder

rec = Recorder(base_url="http://localhost:3001")
rec.start({"model": "gpt-4o"})
rec.step({"step_type": "model_output", "content": "..."})
rec.step({"step_type": "decision", "selected_option": "block", "confidence": 0.92})
proof = rec.finish()
# proof is a cryptographically signed, tamper-evident record of exactly what happened
```

---

## Features

- **Step-by-step recording** — capture model outputs, tool calls, and decisions as structured events
- **Hash chain integrity** — each step is cryptographically linked to the previous one
- **Replayable runs** — attach an execution context so a run can be deterministically replayed
- **Offline verification** — verify any proof artifact without contacting the runtime
- **Framework-agnostic** — works with LangChain, LangGraph, raw API calls, or any other setup
- **Context manager support** — automatic finish/abort on exception

---

## Installation

```bash
pip install afr-sdk
```

Requires Python 3.8+.

---

## First Run

The quickstart needs the AFR runtime running locally. Two terminals:

**Terminal 1 — start the runtime:**
```bash
# From the AFR repository root:
node runtime/src/server.js
```

**Terminal 2 — run the quickstart:**
```bash
pip install afr-sdk
python quickstart.py
```

If everything is working you'll see:
```
🎉  SUCCESS: AFR SDK is fully working
    You have recorded and verified an agent run.
```

If the runtime is not running you'll see:
```
❌  Cannot connect to AFR runtime
👉  Run:  node runtime/src/server.js
```

---

## Quickstart

Full expected output from `python quickstart.py`:

```
╔══════════════════════════════════════════════════════╗
║           🚀  AFR SDK Quickstart                     ║
║  Ensure the backend is running at http://localhost:3001  ║
╚══════════════════════════════════════════════════════╝

── 1. Importing afr_python_sdk ──────────────────────────────────────
  ✅  afr_python_sdk imported successfully
     module : /usr/local/lib/python3.11/site-packages/afr_python_sdk/__init__.py

── 2. Creating Recorder ─────────────────────────────────────────────
  ✅  Recorder initialised  →  http://localhost:3001

── 3. Starting run ──────────────────────────────────────────────────
  ✅  Run started
     run_id : a3f8c2d1-...

── 4. Recording steps ───────────────────────────────────────────────
  ✅  Step 1 recorded  (model_output)
  ✅  Step 2 recorded  (decision)
     steps recorded : 2

── 5. Completing run ────────────────────────────────────────────────
  ✅  Run completed and sealed
     run_id           : a3f8c2d1-...
     steps in proof   : 2
     replayable       : True
     final_chain_hash : 7e3a1bc94f082d01...

── 6. Verifying hash chain ──────────────────────────────────────────
  ✅  Hash chain intact — tamper-evident proof is valid

════════════════════════════════════════════════════════
  🎉  SUCCESS: AFR SDK is fully working
  You have recorded and verified an agent run.
════════════════════════════════════════════════════════
```

---

## Example Code

### Minimal run

```python
from afr_python_sdk import Recorder

rec = Recorder(base_url="http://localhost:3001")

rec.start({
    "model":           "gpt-4o",
    "runtime_version": "1.0.0",
})

rec.step({
    "step_type":  "model_output",
    "model_name": "gpt-4o",
    "content":    "Transaction shows elevated risk indicators.",
})

rec.step({
    "step_type":       "decision",
    "goal_reference":  "evaluate-transaction",
    "selected_option": "block",
    "confidence":      0.92,
    "reasoning":       "Fraud probability 0.82 exceeds block threshold.",
})

proof = rec.finish()
print(proof["run_id"])
print(proof["final_chain_hash"])
```

### Context manager (auto-finish / abort on exception)

```python
from afr_python_sdk import Recorder

with Recorder(base_url="http://localhost:3001") as rec:
    rec.start({"model": "gpt-4o"})
    rec.step({"step_type": "model_output", "content": "..."})
    rec.step({
        "step_type":       "decision",
        "selected_option": "approve",
        "confidence":      0.88,
    })
# finish() is called automatically
# abort() is called automatically if an exception is raised
```

### Replayable run

Attaching a full execution context marks the run as replayable — the runtime stores the model configuration alongside the proof so the run can be reproduced:

```python
rec.start({
    "model":           "claude-sonnet-4-6",
    "model_version":   "20250514",
    "system_prompt":   "You are a fraud detection agent.",
    "temperature":     0.2,
    "top_p":           0.9,
    "runtime_version": "1.0.0",
    "tools":           [{"name": "risk_score"}],
})
```

### Automatic LLM and tool recording

```python
from afr_python_sdk import Recorder
from afr_python_sdk.wrappers import afr_llm, afr_tool

rec = Recorder(base_url="http://localhost:3001")
rec.start({"model": "gpt-4o"})

# Records input hash, output content, and token usage automatically
reply = afr_llm(rec, call_my_llm, prompt, meta={"model_name": "gpt-4o"})

# Records tool name, input, and output automatically
result = afr_tool(rec, "risk_score", run_risk_score, {"txn_id": "TXN-001"})

proof = rec.finish()
```

---

## Architecture

```
Your Agent Code
      │
      ▼
 afr_python_sdk          ← this package
  Recorder / Client
      │  HTTP
      ▼
 AFR Runtime             ← node runtime/src/server.js
  Step validator
  Hash chain builder
  Proof signer
      │
      ▼
 .afr Proof Artifact     ← JSON, self-contained, portable
      │
      ▼
 Verification            ← offline, no server needed
  Hash chain check
  Signature check
```

The SDK never stores any data locally. Everything is sent to the runtime over HTTP. The runtime is the only component that writes to disk.

---

## Security

- **No hidden reasoning** — every decision the agent makes is recorded as a structured step with a reason field. Nothing is implicit.
- **Tamper-evident logs** — altering, reordering, or deleting any step breaks the hash chain. Verification fails immediately.
- **Verifiable proofs** — the proof artifact contains the full hash chain and a cryptographic signature. It can be verified by anyone with the public key, with no server connection required.
- **No external dependencies** — the SDK only requires `requests`. No telemetry, no analytics, no third-party calls.

---

## Use Cases

| Use case | How AFR helps |
|----------|---------------|
| **AI auditing** | Every agent decision is logged with full context and a tamper-evident chain |
| **Regulatory compliance** | Produce signed, verifiable records of agent behaviour for auditors |
| **Debugging** | Replay any historical run exactly as it happened to reproduce issues |
| **Trust layer** | Give downstream consumers confidence that agent logs have not been altered |
| **Incident response** | Investigate what an agent did and why, with cryptographic certainty |

---

## Project Structure

```
afr_python_sdk/          ← installable package
  __init__.py            ← public API: Recorder, Client, AfrClientError
  recorder.py            ← high-level stateful recorder
  client.py              ← low-level HTTP client
  utils.py               ← internal helpers
  wrappers.py            ← afr_llm / afr_tool convenience wrappers

examples/                ← runnable example scripts
  basic_run.py           ← minimal start → step → finish flow
  async_run.py           ← async usage pattern
  with_llm.py            ← LLM wrapper example

tests/                   ← unit tests
  test_utils.py
  test_wrappers.py

quickstart.py            ← end-to-end first-run script
verify_install.py        ← import + lifecycle verification script
pyproject.toml           ← package metadata and build config
```

---

## License

MIT — see [LICENSE](LICENSE).
