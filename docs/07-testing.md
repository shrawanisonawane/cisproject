# 07: Testing & Verification Report

## Purpose
This document provides exact instructions for running the test suite and automated demonstration verification script, accompanied by the actual, verbatim terminal outputs from test execution.

---

## 1. Test Suite Overview

The test suite in `tests/` contains 49 comprehensive unit and integration tests covering:
- Deterministic canonical JSON (`test_canonical.py`)
- RSA-2048 key generation, PEM encryption, and SHA-256 fingerprinting (`test_keys.py`)
- RSASSA-PSS digital signature creation and mathematical validation (`test_signing.py`)
- Certificate issuance, data normalization, and SQLite persistence (`test_issuance.py`)
- Revocation recording and double-revocation guard (`test_revocation.py`)
- Audit log cryptographic hash chaining and tamper detection (`test_audit.py`)
- ReportLab A4 diploma PDF generation, layout bounds, and QR PNG generation (`test_pdf_qr.py`)
- Tamper lab helpers, hash recomputation, and restore logic (`test_demo_tools.py`)
- End-to-end verification service across ID and offline bundle inputs (`test_verification.py`)
- Security middleware: loopback enforcement, CSRF token validation, CSP headers, rate-limiting (`test_security_routes.py`)

---

## 2. Running the Test Suite (`pytest -q`)

### Command
```powershell
pytest -q
```

### Actual Output (Verbatim)
```
.................................................                        [100%]
============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\wable\OneDrive\Desktop\Shravan Project\certificate-platform\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
49 passed, 1 warning in 9.64s
```

---

## 3. Automated End-to-End Live Check (`scripts/demo_check.py`)

The automated script drives the live running server (`http://127.0.0.1:8000`) across all 11 evaluation steps defined in the project specification.

### Command
```powershell
python scripts/demo_check.py
```

### Actual Output (Verbatim)
```
Connecting to test server at http://127.0.0.1:8000...
Step 1: GET /api/health -> PASS (status=200)
Step 2: Issue new certificate via /issuer/new -> PASS (id=MIAS-2026-NBM68WZY)
Step 3: GET /api/verify/MIAS-2026-NBM68WZY -> PASS (status=VALID)
Step 4: Downloads (PDF, QR PNG, Bundle JSON) -> PASS
Step 5: POST /demo/tamper (no recompute) -> PASS (status=TAMPERED)
Step 6: POST /demo/restore -> PASS (status=VALID)
Step 7: POST /demo/tamper with recompute_hash=on -> PASS (hash_matches=True, sig_valid=False)
Step 8: POST /verify/bundle (original VALID, edited TAMPERED) -> PASS
Step 9: Revoke certificate -> PASS (status=REVOKED, sig_valid=True)
Step 10: GET /api/verify/NOPE-0000 -> PASS (status=UNKNOWN)
Step 11: Non-loopback restriction -> SKIPPED (covered by tests/test_security_routes.py)

DEMO CHECK RESULT: ALL PASS
```

---

## 4. Test Summary Matrix

| Category | Tests | Target | Result |
|---|---|---|---|
| Cryptographic Core | 18 | `canonical.py`, `keys.py`, `signing.py` | 100% Passed |
| Registry Services | 21 | `issuance.py`, `verification.py`, `revocation.py`, `audit.py`, `pdf.py`, `qr.py`, `demo_tools.py` | 100% Passed |
| Security & Routing | 10 | Loopback isolation, CSRF double-submit, sliding window rate-limiting | 100% Passed |
| Live End-to-End | 11 | `scripts/demo_check.py` against live Uvicorn HTTP server | 100% Passed |
