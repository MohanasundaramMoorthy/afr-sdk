# Changelog

All notable changes to this project will be documented here.

---

## [1.0.1] — 2026-03-20

### Fixed
- Restructured package directory so the installed package is correctly importable
  (`from afr_python_sdk import Recorder` now works after `pip install afr-sdk`)

### Added
- `quickstart.py` — end-to-end first-run script with structured output and error handling
- `verify_install.py` — import + full lifecycle verification script
- `README.md` — full documentation with architecture diagram, examples, security notes, and use cases
- `CONTRIBUTING.md` — local setup, test instructions, and PR workflow
- `docs/overview.md` — conceptual overview of AFR, tamper-evidence, and how the hash chain works
- `examples/` — `basic_run.py`, `async_run.py`, `with_llm.py`

### Improved
- Developer onboarding: first-run experience now works in under 30 seconds

---

## [1.0.0] — 2026-03-10

### Added
- `Recorder` — high-level stateful recorder with `start()`, `step()`, `decision()`, `finish()`, `abort()`, `verify()`
- `Client` — low-level HTTP client for the AFR runtime API
- `AfrClientError` — typed exception with HTTP status code
- `afr_llm` / `afr_tool` wrappers — automatic step recording for LLM calls and tool calls
- `afr_llm_async` / `afr_tool_async` — async variants of the wrappers
- `detect_anomalies()` — proof artifact analyser for step-sequence anomalies
- Context manager support — `finish()` called automatically; `abort()` called on exception
- SHA-256 hash chain integrity across all recorded steps
- Ed25519-signed proof artifact — self-contained, portable, verifiable offline
- Replayable runs — full execution context captured alongside the proof
