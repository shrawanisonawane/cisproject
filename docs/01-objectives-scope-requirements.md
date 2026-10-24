# 01: Objectives, Scope & Requirements

## Purpose
This document defines the project scope, technical objectives, functional requirements, and non-functional requirements for the **Meridian Certificate Registry**.

---

## Objectives

1. **Defensible Cryptographic Issuance**: Implement cryptographically authentic academic credentials signed with RSA-2048 and RSASSA-PSS, preventing unauthorized forgery.
2. **Transparent Verification**: Allow verifiers (employers, academic boards) to verify credentials in under two seconds via web UI, REST API, or offline CLI script.
3. **Tamper Detection Demonstration**: Provide concrete, demonstrable proof of how digital signatures expose data tampering, including sophisticated hash-recalculation attacks.
4. **Institutional Aesthetic & Complete Offline Capability**: Deliver a production-grade, warm-ivory/deep-navy user interface with zero internet dependencies (no CDNs, external fonts, or online scripts).
5. **Auditable Integrity**: Maintain an append-only, SHA-256 hash-chained log for all critical registry actions (issuance, revocation, tampering).

---

## Scope

### In-Scope
- RSA-2048 key generation, PEM export/import, and public-key SHA-256 fingerprinting.
- Deterministic canonical JSON: fixed field set, keys sorted alphabetically, compact separators (',' and ':'), UTF-8 encoding, and Unicode NFC normalization with surrounding whitespace stripped. It is inspired by JSON Canonicalization Scheme (RFC 8785) but is not a full implementation of it.
- RSASSA-PSS digital signing with SHA-256, MGF1-SHA-256, and 32-byte salt.
- SQLite-backed storage for certificates, revocations, and audit entries.
- Loopback-restricted Issuer workspace (`/issuer`, `/issuer/new`, `/issuer/audit`) for managing credentials.
- Public web verification endpoints (`/`, `/verify`, `/verify/{id}`, `/verify/bundle`).
- REST API for verification, certificate listing, and public key discovery.
- PDF generation (ReportLab) embedding certificate details, SHA-256 fingerprint, and QR code pointing to the verification link.
- QR PNG generation (`qrcode` library) strictly encoding canonical verification URLs.
- Standalone verification script (`scripts/verify_offline.py`) operating fully offline with only the public key.
- Tamper demonstration lab (`/demo`) showing unauthorized modification detection.

### Out-of-Scope
- Decentralized Ledger / Blockchain infrastructure (unnecessary operational overhead and financial cost for a single-institution registry).
- Distributed multi-tenant identity systems (OAuth2/SAML/OIDC).
- Hardware Security Modules (HSMs) or smartcard key storage (keys stored in encrypted PEM files on local filesystem).
- Multi-signature issuance workflows (single institutional key architecture).
- RFC 3161 trusted third-party timestamping authorities.

---

## Functional Requirements

| ID | Requirement | Description |
|---|---|---|
| **FR-01** | Key Management | Generate RSA-2048 keypairs with optional passphrase encryption; export public key PEM and SHA-256 fingerprint. |
| **FR-02** | Payload Canonicalization | Serialize credential fields using deterministic canonical JSON: fixed field set, keys sorted alphabetically, compact separators (',' and ':'), UTF-8 encoding, and Unicode NFC normalization with surrounding whitespace stripped. Inspired by RFC 8785 but not a full implementation. |
| **FR-03** | Digital Signing | Sign canonical bytes with RSASSA-PSS (SHA-256, 32-byte salt); record Base64-encoded signature (`signature_b64`). |
| **FR-04** | Certificate Issuance | Web form and API to input student, degree, and course details, generating a unique ID (`MIAS-YYYY-XXXX`). |
| **FR-05** | Online Verification | Reconstruct canonical payload from database fields, recompute hash, verify signature, and check revocation status. |
| **FR-06** | Bundle Export & Verification | Export signed JSON bundle; verify uploaded or pasted JSON bundle against public key and database. |
| **FR-07** | Certificate Revocation | Revoke certificates with mandatory reason without altering signed record; record in `revocations` table. |
| **FR-08** | PDF & QR Generation | Render printable A4 landscape PDF with verification URL and QR code; render standalone QR PNG. |
| **FR-09** | Audit Trail | Log every issuance, revocation, and demo action into a SHA-256 hash-chained `audit_log` table. |
| **FR-10** | Tamper Lab | Classroom interface to modify stored fields, toggle hash recomputation, and demonstrate verification failure. |

---

## Non-Functional Requirements

| Category | Requirement | Specification |
|---|---|---|
| **Security** | Loopback Isolation | Issuer and demo endpoints reject all non-loopback connections (`127.0.0.1`, `::1`) with HTTP 403. |
| **Security** | CSRF Protection | State-changing POST endpoints enforce `SameSite=Lax` CSRF tokens matching hidden form inputs / headers. |
| **Security** | Content Security Policy | `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:`. Zero inline styles or scripts. |
| **Security** | Rate Limiting | In-memory sliding window rate limiter (30 requests/minute per client IP) on verification endpoints. |
| **Performance** | Verification Latency | Verification completes in under 50ms on standard hardware (RSA-2048 verification requires ~0.5ms). |
| **Reliability** | Zero Online Dependencies | Zero CDN links, external web fonts, or remote API dependencies; operates completely in air-gapped environments. |
| **Usability** | Responsive Institutional UI | Semantic HTML5, WCAG AA contrast (≥ 4.5:1), responsive layout supporting screens from 375px mobile to 1080p desktop. |
| **Standards** | Protocol Standards | RFC-8017 (PKCS#1 v2.2 RSASSA-PSS), RFC-3339 / ISO-8601 (Timestamps), inspired by RFC 8785 for canonical JSON formatting. |
