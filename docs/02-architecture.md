# 02: System Architecture

## Purpose
This document presents the architectural design, component model, data flow, entity relationships, and sequence interactions of the **Meridian Certificate Registry**.

---

## 1. System Architecture & Boundaries

```mermaid
graph TB
    subgraph ClientLayer["Clients & Verification Channels"]
        Browser["Modern Web Browser<br/>(Verifiers & Students)"]
        Phone["Mobile Camera / QR Scanner"]
        LocalAdmin["Local Administrator<br/>(Loopback 127.0.0.1)"]
        OfflineCLI["Offline Verifier Script<br/>(verify_offline.py)"]
    end

    subgraph SecurityBoundary["FastAPI Application Boundary (app/main.py)"]
        SecHeaders["SecurityHeadersMiddleware<br/>(CSP, HSTS, X-Content-Type)"]
        LoopbackGuard["Loopback Check<br/>(require_loopback)"]
        CSRFGuard["CSRF Protection<br/>(check_csrf)"]
        RateLimiter["Rate Limiter<br/>(30 req/min)"]

        subgraph Routers["FastAPI Routers"]
            PubR["public.py<br/>(/, /verify, /certificates/*)"]
            IssR["issuer.py<br/>(/issuer/*)"]
            DemoR["demo.py<br/>(/demo/*)"]
            ApiR["api.py<br/>(/api/*)"]
        end

        subgraph ServiceLayer["Service Layer (app/services/)"]
            IssSvc["issuance.py<br/>(Certificate creation & canonicalization)"]
            VerSvc["verification.py<br/>(Signature, hash & revocation check)"]
            RevSvc["revocation.py<br/>(Revocation recording)"]
            AudSvc["audit.py<br/>(Hash-chained event log)"]
            PdfSvc["pdf.py<br/>(ReportLab certificate generation)"]
            QrSvc["qr.py<br/>(PNG generation & URL building)"]
            DemoSvc["demo_tools.py<br/>(Tamper & restore simulator)"]
        end

        subgraph CryptoEngine["Cryptographic Core (app/crypto/)"]
            Canonical["canonical.py<br/>(Deterministic canonical JSON)"]
            Signing["signing.py<br/>(RSASSA-PSS SHA-256 sign/verify)"]
            Keys["keys.py<br/>(Keypair generation, PEM I/O, fingerprints)"]
        end
    end

    subgraph StorageLayer["Data & Key Storage"]
        SQLite[("SQLite Database<br/>(certificates.db)")]
        KeyFiles["Key Store<br/>(keys/issuer_private.pem & issuer_public.pem)"]
    end

    %% Client connections
    Browser -->|HTTP GET /verify| SecHeaders
    Phone -->|Scan QR /verify/{id}| SecHeaders
    LocalAdmin -->|HTTP GET/POST /issuer| SecHeaders
    OfflineCLI -.->|Reads Bundle + Public Key| CryptoEngine

    SecHeaders --> PubR
    SecHeaders --> ApiR
    SecHeaders --> LoopbackGuard
    LoopbackGuard --> CSRFGuard
    CSRFGuard --> IssR
    CSRFGuard --> DemoR

    PubR --> RateLimiter
    ApiR --> RateLimiter
    RateLimiter --> VerSvc

    IssR --> IssSvc
    DemoR --> DemoSvc
    PubR --> PdfSvc
    PubR --> QrSvc

    IssSvc --> Canonical
    IssSvc --> Signing
    VerSvc --> Canonical
    VerSvc --> Signing
    IssSvc --> AudSvc
    RevSvc --> AudSvc

    Signing --> KeyFiles
    IssSvc --> SQLite
    VerSvc --> SQLite
    RevSvc --> SQLite
    AudSvc --> SQLite
    DemoSvc --> SQLite
```

---

## 2. Component Descriptions

| Component | File Path | Responsibility |
|---|---|---|
| **Security Middleware** | `app/security.py` | Enforces Content-Security-Policy, strict loopback IP validation, SameSite CSRF cookies, and IP sliding-window rate limiting. |
| **Public Router** | `app/routers/public.py` | Serves public landing page, certificate search/verify forms, verification result page, PDF downloads, QR codes, and public key PEM. |
| **Issuer Router** | `app/routers/issuer.py` | Handles administrative issuance workflow, listing with search/filter, certificate details, and revocation dialog. Restricted to loopback. |
| **Demo Router** | `app/routers/demo.py` | Provides classroom tamper lab to alter database records, recompute hashes, and verify manipulated bundles. Restricted to loopback and demo mode. |
| **API Router** | `app/routers/api.py` | Provides JSON REST endpoints for health checks, public key information, certificate creation, verification, and revocation. |
| **Canonicalizer** | `app/crypto/canonical.py` | Deterministic canonical JSON: fixed field set, keys sorted alphabetically, compact separators (',' and ':'), UTF-8 encoding, and Unicode NFC normalization with surrounding whitespace stripped. It is inspired by JSON Canonicalization Scheme (RFC 8785) but is not a full implementation of it. |
| **Signer** | `app/crypto/signing.py` | Generates and verifies RSASSA-PSS signatures with SHA-256 and 32-byte salt using the `cryptography` library. |
| **Key Manager** | `app/crypto/keys.py` | Manages 2048-bit RSA keys, PKCS#8 encrypted PEM storage, and computes public-key SHA-256 fingerprints. |
| **Verification Service** | `app/services/verification.py` | Orchestrates end-to-end verification: payload reconstruction, hash recomputation, signature validation, and revocation lookup. |
| **Audit Service** | `app/services/audit.py` | Logs events into a cryptographically chained audit log where each record commits to the previous record's SHA-256 hash. |
| **PDF Service** | `app/services/pdf.py` | Renders high-fidelity A4 landscape PDF diplomas with double borders, official typography, QR code, and public key fingerprint. |

---

## 3. Entity-Relationship Diagram (Database Schema)

Derived directly from `app/db.py`:

```mermaid
erDiagram
    certificates ||--o| revocations : "may have"
    certificates ||--o{ audit_log : "references"
    certificates ||--o| demo_backups : "may have temporary backup"

    certificates {
        TEXT certificate_id PK "Format: MIAS-YYYY-XXXX"
        TEXT student_name "Full student name"
        TEXT student_roll_no "Institutional roll number"
        TEXT program "Academic degree program"
        TEXT course "Specific course or major"
        TEXT certificate_title "Title of the credential"
        TEXT grade_or_result "Grade or classification"
        TEXT issue_date "Date of conferral (YYYY-MM-DD)"
        TEXT issuing_authority "Name of issuing university"
        TEXT payload_sha256 "SHA-256 hash of canonical JSON (64 hex)"
        TEXT signature_b64 "RSASSA-PSS digital signature (Base64)"
        TEXT key_id "Public key identifier"
        TEXT created_at "UTC ISO-8601 timestamp"
    }

    revocations {
        TEXT certificate_id PK, FK "References certificates.certificate_id"
        TEXT reason "Reason for revocation (3-200 chars)"
        TEXT revoked_at "UTC ISO-8601 timestamp"
    }

    audit_log {
        INTEGER id PK "Auto-increment primary key"
        TEXT ts "UTC ISO-8601 timestamp"
        TEXT action "ISSUED, REVOKED, DEMO_TAMPER, DEMO_RESTORE"
        TEXT certificate_id "Target certificate ID or NULL"
        TEXT details "Human-readable context"
        TEXT prev_hash "SHA-256 hash of preceding row (or 64 zeros for row 1)"
        TEXT entry_hash "SHA-256(id || ts || action || cert_id || details || prev_hash)"
    }

    demo_backups {
        TEXT certificate_id PK, FK "References certificates.certificate_id"
        TEXT original_json "Complete pristine row serialized as JSON"
        TEXT saved_at "UTC ISO-8601 timestamp"
    }
```

---

## 4. Issuance Sequence Flow

```mermaid
sequenceDiagram
    autonumber
    actor Issuer as Local Administrator
    participant Router as issuer.py (/issuer/new)
    participant Svc as issuance.py
    participant Canon as canonical.py
    participant Sign as signing.py
    participant DB as SQLite (certificates.db)
    participant Audit as audit.py

    Issuer->>Router: POST /issuer/new (form fields + CSRF token)
    Note over Router: Enforce require_loopback & check_csrf
    Router->>Svc: issue_certificate(conn, cert_in, priv_key, pub_key)
    Svc->>Svc: Generate ID: MIAS-2026-XXXX
    Svc->>Canon: canonicalize(payload_dict)
    Canon-->>Svc: canonical_bytes (alphabetical keys, compact UTF-8)
    Svc->>Svc: Compute payload_sha256 = sha256_hex(canonical_bytes)
    Svc->>Sign: sign_bytes(priv_key, canonical_bytes)
    Sign-->>Svc: signature_b64 (RSASSA-PSS Base64 string)
    Svc->>DB: INSERT INTO certificates (...)
    Svc->>Audit: add_entry(conn, "ISSUED", cert_id, "student=...")
    Audit->>DB: Fetch last entry_hash, compute new entry_hash, INSERT INTO audit_log
    Svc-->>Router: Certificate row dictionary
    Router-->>Issuer: Redirect 303 -> /issuer/certificates/{id}
```

---

## 5. Verification Sequence Flow

```mermaid
sequenceDiagram
    autonumber
    actor Verifier as Employer / Verifier
    participant Router as public.py (/verify/{id})
    participant VerSvc as verification.py
    participant Canon as canonical.py
    participant Sign as signing.py
    participant DB as SQLite (certificates.db)

    Verifier->>Router: GET /verify/{id} (or scan QR code)
    Note over Router: Rate limit check (30 req/min)
    Router->>VerSvc: verify_by_id(conn, cert_id, pub_key, method="ID")
    VerSvc->>DB: SELECT * FROM certificates WHERE certificate_id = ?
    alt Record Not Found
        VerSvc-->>Router: VerificationResult(status="UNKNOWN", message="Certificate not found")
    else Record Found
        VerSvc->>Canon: Reconstruct payload dict from stored columns -> canonicalize()
        Canon-->>VerSvc: recomputed_canonical_bytes
        VerSvc->>VerSvc: recomputed_hash = sha256_hex(recomputed_canonical_bytes)
        VerSvc->>Sign: verify_bytes(pub_key, recomputed_canonical_bytes, signature_b64)
        Sign-->>VerSvc: signature_valid (True / False)

        VerSvc->>DB: SELECT * FROM revocations WHERE certificate_id = ?
        alt Signature Fails
            VerSvc-->>Router: VerificationResult(status="TAMPERED", signature_valid=False)
        else Signature Valid and Revoked
            VerSvc-->>Router: VerificationResult(status="REVOKED", signature_valid=True)
        else Signature Valid and Not Revoked
            VerSvc-->>Router: VerificationResult(status="VALID", signature_valid=True)
        end
    end
    Router-->>Verifier: Render verify_result.html with Status Badge & Technical Details
```
