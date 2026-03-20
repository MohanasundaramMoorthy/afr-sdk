# AFR SDK

Tamper-evident execution recording for AI agents.

[![PyPI version](https://img.shields.io/pypi/v/afr-sdk.svg)](https://pypi.org/project/afr-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/afr-sdk.svg)](https://pypi.org/project/afr-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## The problem

AI agents make decisions that affect real systems — blocking transactions, approving requests, triggering actions. When something goes wrong, you need to prove what happened and that the record was not altered after the fact.

Observability tools tell you what an agent did. They cannot prove the log was not modified.

AFR solves this. Every step is recorded into a SHA-256 hash chain, sealed with an Ed25519 signature, and exported as a self-contained proof artifact. Alter or delete any step and verification fails — without needing to trust any server.

---

## Quick example

```python
from afr_python_sdk import Recorder

rec = Recorder(base_url="http://localhost:3001")
rec.start({"model": "gpt-4o", "runtime_version": "1.0.0"})

rec.step({"step_type": "model_output", "model_name": "gpt-4o",
          "content": "Transaction shows elevated risk."})

rec.step({"step_type": "decision", "goal_reference": "evaluate-txn",
          "selected_option": "block", "confidence": 0.92,
          "reasoning": "Fraud probability exceeds threshold."})

proof = rec.finish()
print(proof["run_id"])
print(proof["final_chain_hash"])
```

---

## Features

- step-by-step recording of model outputs, tool calls, and decisions
- SHA-256 hash chain — each step is cryptographically linked to the previous one
- Ed25519-signed proof artifact — self-contained, portable, verifiable offline
- replayable runs — attach an execution context so a run can be reproduced
- framework-agnostic — works with LangChain, LangGraph, raw API calls, or anything else
- context manager support — automatic finish on success, abort on exception
- no telemetry — the only dependency is `requests`

---

## Installation

```bash
pip install afr-sdk
```

Requires Python 3.8+.

---

## How it works

The SDK sends recording events to the AFR runtime over HTTP. The runtime builds the hash chain, signs the proof, and stores it. The proof artifact is a plain JSON object that can be verified anywhere — offline, without contacting the runtime.

The default runtime address is `http://localhost:3001`. You can point the SDK at any hosted runtime by changing `base_url`.

```
Agent Code
    │  HTTP
    ▼
AFR Runtime              ← node runtime/src/server.js
  step validator
  hash chain builder
  Ed25519 proof signer
    │
    ▼
.afr Proof Artifact      ← JSON, self-contained
    │
    ▼
Offline Verification
  hash chain check
  signature check
```

---

## First run

The SDK requires the AFR runtime to be running locally. Open two terminals:

**Terminal 1 — start the runtime:**

```bash
# from the AFR repository root
node runtime/src/server.js
```

**Terminal 2 — run the quickstart:**

```bash
pip install afr-sdk
python quickstart.py
```

Expected result:

```
SUCCESS: AFR SDK is fully working
You have recorded and verified an agent run.
```

If the runtime is not running, you will see a connection error with instructions to start it.

---

## Usage

### Basic run

```python
from afr_python_sdk import Recorder

rec = Recorder(base_url="http://localhost:3001")
rec.start({"model": "gpt-4o", "runtime_version": "1.0.0"})

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
```

### Context manager

`finish()` is called automatically on success. `abort()` is called automatically if an exception is raised.

```python
from afr_python_sdk import Recorder

with Recorder(base_url="http://localhost:3001") as rec:
    rec.start({"model": "gpt-4o"})
    rec.step({"step_type": "model_output", "content": "..."})
    rec.step({"step_type": "decision", "selected_option": "approve",
              "confidence": 0.88})
```

### Replayable run

Pass a full execution context to make the run replayable. The runtime stores the model configuration alongside the proof so the run can be reproduced with the same inputs.

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

### LLM and tool wrappers

Wrap existing LLM calls and tool functions to record their inputs and outputs automatically.

```python
from afr_python_sdk import Recorder
from afr_python_sdk.wrappers import afr_llm, afr_tool

rec = Recorder(base_url="http://localhost:3001")
rec.start({"model": "gpt-4o"})

reply  = afr_llm(rec, call_my_llm, prompt, meta={"model_name": "gpt-4o"})
result = afr_tool(rec, "risk_score", run_risk_score, {"txn_id": "TXN-001"})

proof = rec.finish()
```

`afr_llm` records the prompt hash, output content, and token usage. `afr_tool` records the tool name, input, and output. Async variants `afr_llm_async` and `afr_tool_async` are also available.

---

## Security

- **tamper-evident** — altering, reordering, or deleting any step breaks the SHA-256 hash chain. verification fails immediately.
- **offline-verifiable** — the proof artifact contains the full chain and an Ed25519 signature. anyone with the public key can verify it without a server.
- **no hidden state** — every decision is recorded as a structured step with reasoning. nothing is implicit.
- **no external dependencies** — the SDK only requires `requests`. no telemetry, no analytics, no third-party calls.

---

## Use cases

| use case | how AFR helps |
|----------|---------------|
| AI auditing | every decision is logged with full context and a tamper-evident chain |
| regulatory compliance | produce signed, verifiable records of agent behaviour for auditors |
| debugging | replay any historical run exactly as it happened to reproduce issues |
| trust layer | give downstream consumers confidence that logs have not been altered |
| incident response | investigate what an agent did and why, with cryptographic certainty |

---

## Project structure

```
afr_python_sdk/          ← installable package
  __init__.py            ← public API: Recorder, Client, AfrClientError
  recorder.py            ← high-level stateful recorder
  client.py              ← low-level HTTP client
  utils.py               ← internal helpers
  wrappers.py            ← afr_llm / afr_tool wrappers

examples/                ← runnable example scripts
  basic_run.py
  async_run.py
  with_llm.py

tests/
  test_utils.py
  test_wrappers.py

quickstart.py            ← end-to-end first-run script
verify_install.py        ← import and lifecycle verification
pyproject.toml           ← package metadata
```

---

## License

MIT — see [LICENSE](LICENSE).
