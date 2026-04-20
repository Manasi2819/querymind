# QueryMind — Backend Tests

This directory contains manual test scripts used to verify security and integration functionality.

## Test Files

| File | Purpose |
|---|---|
| `security_test.py` | Unit tests for encryption, secret redaction, and SQL guardrails |
| `integration_security_test.py` | Full integration test — requires a running backend server on `localhost:8000` |
| `test_cleaner.py` | Unit tests for the API key sanitization logic |

## Running Tests

### Prerequisites
- The backend must be configured with a valid `.env` file (including `FERNET_KEY`).
- For integration tests, start the server first: `uvicorn main:app --reload`

### Run from the `backend/` directory:
```bash
# Security unit tests (no server required)
python tests/security_test.py

# API key cleaner unit tests
python tests/test_cleaner.py

# Full integration test (server must be running)
python tests/integration_security_test.py
```

> **Note:** These are manual smoke tests. For a production CI pipeline, convert these to pytest-style tests.
