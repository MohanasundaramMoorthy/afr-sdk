# Contributing

Thank you for your interest in contributing to AFR SDK.

---

## Local Setup

**1. Clone the repository**

```bash
git clone https://github.com/your-org/afr-sdk.git
cd afr-sdk
```

**2. Create a virtual environment**

```bash
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows
```

**3. Install in editable mode with dev dependencies**

```bash
pip install -e ".[dev]"
```

This installs the package in editable mode so changes to the source files take effect immediately without reinstalling.

---

## Running Tests

```bash
pytest tests/
```

To run with verbose output:

```bash
pytest tests/ -v
```

To run a specific test file:

```bash
pytest tests/test_utils.py -v
```

---

## Running the Quickstart

The quickstart requires the AFR runtime — a Node.js server that receives and
stores recordings. It is a separate component from this Python SDK. Clone the
main AFR repository and start the runtime:

```bash
# In a separate terminal, from the AFR repository root:
node runtime/src/server.js
```

Then run the quickstart script:

```bash
python quickstart.py
```

All six steps should complete with ✅ and the final line should read:

```
🎉  SUCCESS: AFR SDK is fully working
```

---

## Project Structure

```
afr_python_sdk/     ← package source (recorder, client, wrappers, utils)
examples/           ← standalone example scripts
tests/              ← unit tests
quickstart.py       ← end-to-end smoke test
verify_install.py   ← import + lifecycle check
pyproject.toml      ← build and package metadata
```

---

## Submitting a Pull Request

1. Fork the repository and create a branch from `main`:

   ```bash
   git checkout -b fix/your-change-description
   ```

2. Make your changes. Keep commits small and focused.

3. Make sure tests pass:

   ```bash
   pytest tests/ -v
   ```

4. Open a pull request against `main`. Include:
   - a short description of what changed and why
   - any relevant issue numbers

---

## Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Keep functions short and single-purpose
- Add docstrings to public methods
- Avoid adding dependencies — the SDK intentionally has only `requests` as a runtime dependency

---

## Reporting Issues

Open an issue on GitHub with:
- Python version
- SDK version (`pip show afr-sdk`)
- Steps to reproduce
- Full error output
