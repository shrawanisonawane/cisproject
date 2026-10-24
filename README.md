# Meridian Certificate Registry

**Cryptographically Verifiable Academic Credential Issuance and Validation Platform**

Meridian Certificate Registry is an institutional credential platform built on modern asymmetric cryptography. It issues tamper-proof academic credentials signed with **RSASSA-PSS** using a 2048-bit RSA private key, formatted using deterministic canonical JSON (inspired by RFC 8785), and validated via web, REST API, or offline CLI with zero internet dependencies.

---

## Key Features

- **Mathematical Proof of Authenticity**: Every certificate contains an RSASSA-PSS digital signature (SHA-256 with 32-byte salt). Any modification to student details, courses, or grades breaks the signature.
- **Deterministic Canonicalization**: Deterministic canonical JSON: fixed field set, keys sorted alphabetically, compact separators (',' and ':'), UTF-8 encoding, and Unicode NFC normalization with surrounding whitespace stripped. It is inspired by JSON Canonicalization Scheme (RFC 8785) but is not a full implementation of it.
- **Dual Verification Modes**:
  - **Online Registry Verification**: Instant verification via Certificate ID or QR code lookup with live revocation check and hash comparison.
  - **Offline Bundle Verification**: Standalone CLI verification (`python scripts/verify_offline.py <bundle.json> <issuer_public.pem>`) verifying exported JSON credential bundles against the institution's public key with zero server connection.
- **Tamper Lab Demonstration**: Interactive classroom simulation (`/demo`) showing real-time detection of data tampering, including why "hash-recomputation attacks" succeed at matching hashes but fail digital signature checks.
- **Cryptographic Audit Trail**: Append-only log where every issuance, revocation, and tamper action is hash-chained to the SHA-256 digest of the previous row.
- **Institutional UI & Strict Security**: Built with warm ivory, deep navy, and muted teal design tokens. Fully CSP-compliant (`script-src 'self'; style-src 'self'`) with zero external CDNs, zero inline scripts/styles, and loopback network isolation (`127.0.0.1`) on all administrative routes.
- **Printable A4 Diploma Generation**: High-fidelity PDF generation (ReportLab) embedding double borders, formal typography, verification URL, QR code, and public-key fingerprint.

---

## Quick Start Guide

### 1. Environment Setup (Windows PowerShell)

```powershell
# Clone or open the repository
cd certificate-platform

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Copy environment template
Copy-Item .env.example .env
```

*(On macOS/Linux, use `source .venv/bin/activate` and `cp .env.example .env`)*

### 2. Initialize Keys & Database

```powershell
# 1. Generate RSA-2048 keypair (keys/issuer_private.pem & issuer_public.pem)
python scripts/generate_keys.py

# 2. Create SQLite tables (certificates.db)
python scripts/init_db.py

# 3. Seed demonstration credentials
python scripts/seed_demo.py
```

### 3. Run Application Server

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## Platform Navigation

| Page | URL | Description |
|---|---|---|
| **Landing Page** | [http://127.0.0.1:8000/](http://127.0.0.1:8000/) | Institutional overview and cryptographic explanation |
| **Verify Credential** | [http://127.0.0.1:8000/verify](http://127.0.0.1:8000/verify) | Public search portal (by ID or uploaded JSON bundle) |
| **Issuer Workspace** | [http://127.0.0.1:8000/issuer](http://127.0.0.1:8000/issuer) | Registered credentials list with search and filters (Local Only) |
| **Issue New** | [http://127.0.0.1:8000/issuer/new](http://127.0.0.1:8000/issuer/new) | Credential issuance and signing form (Local Only) |
| **Audit Trail** | [http://127.0.0.1:8000/issuer/audit](http://127.0.0.1:8000/issuer/audit) | Hash-chained event log and chain integrity validator (Local Only) |
| **Tamper Lab** | [http://127.0.0.1:8000/demo](http://127.0.0.1:8000/demo) | Interactive classroom tamper and attack demonstration |
| **Public Key** | [http://127.0.0.1:8000/api/public-key](http://127.0.0.1:8000/api/public-key) | Issuer public key PEM and SHA-256 fingerprint |

---

## Testing & Verification

```powershell
# Run the complete automated test suite (all 49 tests pass)
pytest -q

# Run the 11-step automated live server verification script
python scripts/demo_check.py
```

---

## Technical Documentation (`docs/`)

- [`docs/00-abstract-problem-statement.md`](docs/00-abstract-problem-statement.md): Core problem, forgery risks, and solution overview.
- [`docs/01-objectives-scope-requirements.md`](docs/01-objectives-scope-requirements.md): Functional and non-functional requirements.
- [`docs/02-architecture.md`](docs/02-architecture.md): Mermaid diagrams, component models, ER diagram, and sequence flows.
- [`docs/03-cryptography.md`](docs/03-cryptography.md): Deep-dive into RSA-2048, RSASSA-PSS, salt length 32, and canonicalization.
- [`docs/04-threat-model.md`](docs/04-threat-model.md): Threat modeling, attacker profiles, mitigations, and honest limitations.
- [`docs/05-api.md`](docs/05-api.md): Complete REST API endpoint reference.
- [`docs/06-setup-and-run.md`](docs/06-setup-and-run.md): Multi-platform installation and LAN phone testing guide.
- [`docs/07-testing.md`](docs/07-testing.md): Pytest execution logs and demo check test run outputs.
- [`docs/08-demo-script.md`](docs/08-demo-script.md): Timed 5-to-7 minute presentation script for live evaluators.
- [`docs/09-viva-qa.md`](docs/09-viva-qa.md): 30 technical defense questions and answers for viva voce.
- [`docs/10-file-map.md`](docs/10-file-map.md): Structural repository inventory and file descriptions.

---

## License & Academic Disclaimer
Demonstration data and academic prototype for Third Year Cryptography & Information Security course. Not a real legal credential.
