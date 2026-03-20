# AFR — Overview

## What is AFR?

AFR (Agent Flight Recorder) is a protocol for recording AI agent execution in a way that cannot be silently tampered with.

The name comes from aviation black boxes — flight recorders that capture everything that happened before a crash. AFR does the same thing for AI agents: it records every step an agent takes so that the sequence of events can be examined, replayed, and independently verified after the fact.

---

## Why does tamper-evidence matter?

AI agents make decisions that can have real consequences — approving loans, blocking transactions, sending communications, modifying systems. When something goes wrong, two questions matter:

1. **What exactly did the agent do?**
2. **Was the record of what it did altered afterwards?**

Without tamper-evidence, you can answer the first question but not the second. Logs can be edited. Databases can be modified. Without a cryptographic guarantee, there is no way to prove that a log accurately reflects what actually happened.

AFR solves this by building a hash chain across all recorded steps. Each step includes the hash of the previous step. If any step is altered, removed, or inserted, the chain breaks — and anyone running verification will see that immediately.

---

## How it works

### 1. Recording

When your agent starts a run, the AFR runtime creates a new run record and assigns it a unique ID. As the agent works, you call `rec.step(...)` to record each event — model outputs, tool calls, decisions. Each step is sent to the runtime over HTTP.

The runtime appends each step to the run's step list and computes a running hash:

```
step_hash = SHA-256(previous_hash + step_data)
```

The first step seeds the chain from either a context hash (if an execution context was provided) or a fixed genesis string.

### 2. Completion

When the agent finishes, you call `rec.finish()`. The runtime seals the run, computes the final chain hash, signs the proof artifact with an Ed25519 private key, and returns the complete `.afr` proof object.

The proof contains:
- the full list of steps
- the hash of each step
- the final chain hash
- the Ed25519 signature
- the public key needed to verify the signature

### 3. Verification

Anyone with the proof artifact can verify it offline:

1. Recompute the hash chain from scratch using the steps in the proof
2. Compare the recomputed final hash against the stored final hash
3. Verify the Ed25519 signature against the public key embedded in the proof

If the chain is intact and the signature is valid, the proof is authentic. If either check fails, the proof has been tampered with.

---

## What gets recorded

AFR supports several step types. The most common are:

| Step type | What it captures |
|-----------|-----------------|
| `model_output` | The raw output from an LLM call, including model name and content |
| `tool_result` | A tool call — the tool name, input parameters, and output |
| `decision` / `decision_evaluation` | A decision the agent made — the options considered, the selected option, confidence, and reasoning |
| `planning` | A planning step — the goal and description of what the agent intends to do |

---

## Replayable runs

A run is replayable if it was started with a full execution context — model name, model version, system prompt, temperature, top_p, and tool list. With this information, the run can be submitted to the same model again with the same parameters to check whether the model produces the same outputs.

A non-replayable run still has a valid, verifiable hash chain — it just cannot be replayed because the model configuration was not captured.

---

## What AFR is not

- **Not a logging service** — AFR records structured execution events, not raw log lines
- **Not a monitoring tool** — AFR does not alert, aggregate metrics, or run in the background
- **Not a model evaluation framework** — AFR records what happened; it does not score or benchmark model outputs
- **Not a proxy** — AFR does not sit between your agent and the model API; you record steps explicitly

---

## Further reading

- [README](../README.md) — installation, quickstart, and example code
- [CONTRIBUTING](../CONTRIBUTING.md) — how to set up locally and submit changes
- [quickstart.py](../quickstart.py) — runnable end-to-end smoke test
