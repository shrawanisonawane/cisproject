# 08: Live Demonstration Script (5 to 7 Minutes)

## Purpose
This document provides a timed, step-by-step presentation script designed for evaluators, faculty examiners, and project reviews. It details exact user clicks, screen navigation, and spoken commentary demonstrating the cryptographic rigor of the platform.

---

## Timeline Overview

| Timestamp | Phase | Topic / Action | Core Takeaway |
|---|---|---|---|
| **0:00 - 1:00** | Introduction & Problem | Landing page (`/`), problem of credential forgery | Signatures prove authenticity; QR codes prove nothing alone |
| **1:00 - 2:00** | Issuance Workflow | Issuer workspace (`/issuer/new`), sign & issue | Exact canonical serialization, RSASSA-PSS signature |
| **2:00 - 3:15** | Verification & PDF | Public verification (`/verify/{id}`), PDF inspection | Self-verifying document, public-key fingerprint match |
| **3:15 - 4:45** | Tamper Lab Demo | `/demo`: Field edit, hash recompute attack | Changing one char breaks signature; hash matching ≠ signature |
| **4:45 - 5:30** | Revocation Demo | Revoke certificate, inspect audit log (`/issuer/audit`)| Revocation is separate; audit log is hash-chained |
| **5:30 - 6:30** | Offline Verifier & Q&A | Run `scripts/verify_offline.py` via terminal | Independent offline verification with zero server dependency |

---

## Detailed Step-by-Step Script

### Phase 1: Problem Statement & Architecture (0:00 – 1:00)
- **Action**: Open browser to `http://127.0.0.1:8000/`.
- **What to say**:
  > *"Good morning. Today I am presenting the Meridian Certificate Registry, a platform for issuing and verifying academic credentials using public-key cryptography. Traditional credentials—whether paper certificates or PDF scans—are trivial to modify with standard graphics software. Worse, standard QR codes only link to websites; an attacker can easily forge a certificate and link the QR code to a fake verification portal. Meridian solves this by turning every certificate into a self-verifying cryptographic object signed using RSASSA-PSS with a 2048-bit RSA private key."*

### Phase 2: Issuance & Cryptographic Signing (1:00 – 2:00)
- **Action**: Click **"Issuer workspace"** (`http://127.0.0.1:8000/issuer`), then click **"Issue new certificate"** (`/issuer/new`).
- **Action**: Fill in the form:
  - Student Name: `Devika Patel`
  - Roll Number: `TY-CS-2026-077`
  - Program: `B.Sc. Computer Science`
  - Course: `Applied Cryptography`
  - Certificate Title: `Certificate of Completion`
  - Grade: `Distinction`
  - Issue Date: Today's date
- **Action**: Click **"Sign and issue"**.
- **What to say**:
  > *"When I click 'Sign and issue', several critical cryptographic steps occur instantly. First, the fields are serialized into deterministic canonical JSON: fixed field set, keys sorted alphabetically, compact separators (',' and ':'), UTF-8 encoding, and Unicode NFC normalization with surrounding whitespace stripped. It is inspired by JSON Canonicalization Scheme (RFC 8785) but is not a full implementation of it. Next, a SHA-256 fingerprint of these bytes is computed. Finally, the server signs the canonical bytes using RSASSA-PSS with a 32-byte salt. The private key never leaves this server."*

### Phase 3: Public Verification & PDF Generation (2:00 – 3:15)
- **Action**: The browser redirects to `/issuer/certificates/MIAS-...`. Copy the Certificate ID.
- **Action**: Click **"Download PDF"** to preview the diploma in a new tab. Point out the double border, authority title, QR code, and bottom fingerprint block.
- **Action**: Open `/verify`, paste the Certificate ID into the search field, and click **"Verify"**.
- **Action**: Expand the **"Technical details"** `<details>` panel.
- **What to say**:
  > *"Here on the public verification page, the server reconstructs the certificate payload from stored database fields, recomputes the SHA-256 hash, and verifies the digital signature using the institution's public key. Notice that both the hash comparison and signature verification show 'Match' and 'Passed'. The public-key fingerprint printed on the certificate matches the server's public key."*

### Phase 4: Tamper Lab & The Hash-Recompute Attack (3:15 – 4:45)
- **Action**: Navigate to `http://127.0.0.1:8000/demo`.
- **Action**: Select the certificate just created (`Devika Patel`). Verification displays `VALID`.
- **Action**: Under **"2. Edit a signed field"**:
  - Select field: `student_name`
  - Enter new value: `Mallory Attacker`
  - Leave *"Also recompute the stored hash"* **UNCHECKED**.
  - Click **"Apply change"**.
- **Observation**: Status immediately flips to **TAMPERED** (Red banner).
- **What to say**:
  > *"We just altered the student name directly in the database. When the verifier checks it, the reconstructed bytes produce a completely different SHA-256 hash, and the digital signature immediately fails. Now let's test a smarter attacker."*
- **Action**: Under **"2. Edit a signed field"**:
  - Keep field: `student_name`, value: `Mallory Attacker`.
  - **CHECK** *"Also recompute the stored hash (a smarter attacker)"*.
  - Click **"Apply change"**.
- **Observation**: Status remains **TAMPERED**, but expand technical details:
  - `Hash comparison: Match`
  - `Signature verification: Failed`
- **What to say**:
  > *"This is the central cryptographic lesson of our project. The attacker updated the stored hash to match their altered text. The hash check passes! But the status is still TAMPERED because RSASSA-PSS signature verification fails. Anyone can compute a SHA-256 hash, but only the holder of the private key can create a valid signature. A hash proves integrity against accidental corruption; only a digital signature proves authenticity."*
- **Action**: Click **"Restore original record"**. Status returns to **VALID**.

### Phase 5: Revocation & Hash-Chained Audit Trail (4:45 – 5:30)
- **Action**: Navigate to `/issuer/certificates/{id}`.
- **Action**: Under **"Revoke certificate"**, enter reason: `Academic misconduct investigation upheld`.
- **Action**: Click **"Revoke"**, then confirm the modal dialog: **"Yes, revoke certificate"**.
- **Action**: Open the public `/verify/{id}` page.
- **Observation**: Banner displays **REVOKED** (Amber banner). Under technical details: `Signature verification: Passed`, `Revocation status: Revoked`.
- **What to say**:
  > *"Notice that revoking the credential does NOT modify or delete the signed record. The digital signature remains mathematically valid because the student did earn the credential at that point in time. Revocation is recorded separately. Finally, let's inspect the audit trail."*
- **Action**: Navigate to `/issuer/audit`. Show the green **"Chain Intact"** banner and the rows.
- **What to say**:
  > *"Every action—issuance, tamper simulation, restoration, and revocation—is recorded in an append-only log where each entry contains the SHA-256 hash of the preceding entry, forming a cryptographic tamper-evident hash chain."*

### Phase 6: Offline Verification & Conclusion (5:30 – 6:30)
- **Action**: Download the verification bundle JSON from the certificate detail page (`/certificates/{id}/bundle.json`).
- **Action**: Open terminal and execute:
  ```bash
  python scripts/verify_offline.py test_cert-bundle.json keys/issuer_public.pem
  ```
- **What to say**:
  > *"Even if our registry server goes offline or is decommissioned years from now, employers can verify the standalone JSON bundle using only the institution's public key. The offline script runs completely standalone with zero internet or server connection. Thank you, I am ready for questions."*
