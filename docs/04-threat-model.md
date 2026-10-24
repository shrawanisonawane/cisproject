# 04: Threat Model & Honest Limitations

## Purpose
This document provides a security analysis of the **Meridian Certificate Registry**, detailing protected assets, potential attackers, technical mitigations, and an explicit disclosure of system limitations.

---

## 1. Protected Assets

1. **Issuer Private Key (`keys/issuer_private.pem`)**: The root of cryptographic trust. Used to produce valid RSASSA-PSS digital signatures.
2. **Credential Integrity & Authenticity**: Guaranteeing that validly issued certificates cannot be altered or fabricated.
3. **Revocation Registry**: Ensuring that certificates marked as revoked cannot falsely appear valid to verifiers.
4. **Audit Trail**: Append-only log preserving an immutable record of issuance and revocation events.
5. **Verifiers' Trust**: Ensuring that verifiers receive mathematically sound verification results rather than spoofed answers.

---

## 2. Attacker Profiles & Threat Scenarios

| Attacker Profile | Capabilities | Goal |
|---|---|---|
| **Discredited Student / Forger** | Access to PDF editors, vector graphics software, web browser. | Alter grades, student name, or degree title on a PDF diploma or fabricate a fake diploma. |
| **Network Attacker (LAN / Public WiFi)** | Can inspect or manipulate network traffic, intercept DNS, or run rogue WiFi hotspots. | Spoof verification responses, replay old certificates, or access the issuer workspace across the local network. |
| **Malicious Insider / Database Operator** | Has local access or read/write access to the SQLite database file (`certificates.db`). | Modify stored student names or grades directly in database tables; attempt to forge or bypass revocation. |
| **Denial-of-Service Attacker** | Can flood public verification routes with rapid HTTP requests. | Overwhelm the server runtime or CPU through repeated RSA verification operations. |

---

## 3. Mitigations Implemented

| Threat | Mitigation Mechanism | Implementation |
|---|---|---|
| **Credential Forgery** | RSASSA-PSS Digital Signatures on deterministic canonical JSON bytes. | Any alteration to student details renders the signature mathematically invalid against the public key. |
| **Hash-Recalculation Attack** | Dual verification of both SHA-256 hash AND digital signature. | If an attacker recalculates the stored hash, `hash_matches` passes, but `signature_valid` fails. |
| **LAN Unauthorized Issuance** | Loopback network isolation (`require_loopback`). | Issuer (`/issuer/*`) and demo (`/demo/*`) routes reject any IP other than `127.0.0.1` and `::1` with HTTP 403. |
| **Cross-Site Request Forgery (CSRF)** | Double-submit CSRF cookie token with `SameSite=Lax`. | POST requests to administrative routes require matching cookie and hidden form field / header. |
| **Cross-Site Scripting (XSS)** | Strict Content Security Policy. | `default-src 'self'; script-src 'self'; style-src 'self'`. Zero inline scripts, styles, or eval. |
| **DoS on Verification** | In-memory sliding window rate limiting. | Limits client IPs to 30 verification calls per minute. |
| **Audit Log Tampering** | Cryptographic hash chaining. | Each log entry commits to the SHA-256 hash of the previous row; altering row $N$ breaks row $N+1$. |

---

## 4. Honest Limitations & Architectural Boundaries

In cryptography, transparency about what a system does *not* protect against is just as essential as describing what it does protect. The following limitations are acknowledged:

### 1. Loopback Restriction is Not Authentication
- Restricting `/issuer/*` to `127.0.0.1` prevents remote clients on the LAN from issuing credentials. However, it does **not** provide multi-user identity or authentication.
- Any process, user account, or script running locally on the server machine can issue credentials using the server's private key. In a production deployment, this must be replaced with multi-factor institutional SSO (e.g., SAML 2.0 / OpenID Connect with hardware tokens).

### 2. Public Key Served by the Same Host
- The server provides the issuer public key at `/.well-known/issuer-public-key.pem` and `/api/public-key`.
- If an attacker compromises the server or conducts DNS hijacking, they could replace both the private key and public key simultaneously.
- **Remedy**: Verifiers should compare the public key fingerprint printed on the physical certificate against an independently published out-of-band registry or use the provided offline verifier script (`scripts/verify_offline.py`) with a verified local public key copy.

### 3. No RFC 3161 Trusted Timestamping
- Certificate issue dates and audit timestamps represent the local system clock of the server when the operation occurred.
- The system does not incorporate an external RFC 3161 Time-Stamp Authority (TSA). An administrator with root access who rolls back the server clock could issue a back-dated certificate with a valid signature.

### 4. No Blockchain (By Design)
- The platform uses a centralized relational database (SQLite) rather than a distributed blockchain.
- Blockchains incur high transaction fees, public data exposure risks (violating GDPR / FERPA), and latency. For an institutional authority, standard public-key signatures provide mathematical authenticity without distributed consensus overhead.

### 5. Revocation is Local to the Registry
- When a certificate is revoked, the digital signature on the certificate is **not** altered (it remains a mathematically valid signature of past conferral).
- Offline verifiers inspecting only the verification bundle or PDF cannot detect revocation unless they check the online registry. Revocation status can only be asserted by querying the registry's revocation table.

### 6. Single Key Architecture & No Key Rotation
- If the private key in `keys/issuer_private.pem` is stolen or leaked, an attacker can issue forged credentials that pass all signature checks.
- Key rotation, certificate revocation lists (CRLs), and hierarchical public key infrastructure (PKI) with intermediate CAs are not implemented in this prototype.

### 7. Audit Chain Detects Casual Edits Only
- The hash chain in `audit_log` easily exposes manual edits, column overwrites, or deleted rows performed by casual administrative tampering.
- However, because the audit log is stored in the same SQLite database, an attacker with full database write permissions who modifies an early row could write a script to recompute all subsequent `entry_hash` values forward. Cryptographic immutability against database root compromise requires external append-only log replication (e.g., Certificate Transparency logs).

### 8. Built-in PDF Latin-1 Font Restrictions
- The PDF generation engine uses ReportLab's standard built-in core fonts (`Helvetica`, `Times-Roman`, `Courier`) to guarantee 100% offline functionality without embedding external `.ttf` or `.woff` files.
- These standard Type 1 fonts use standard Adobe Latin-1 character encoding. Names containing non-Latin scripts (such as Devanagari, Arabic, Cyrillic, or CJK characters) will raise encoding exceptions and must be transliterated.
