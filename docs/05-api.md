# 05: REST API Reference

## Purpose
This document provides complete technical specifications for every HTTP endpoint in the **Meridian Certificate Registry**, including HTTP methods, access permissions, request parameters, and example JSON or HTML responses.

---

## Endpoint Summary

| Method | Path | Access | Description |
|---|---|---|---|
| `GET` | `/` | Public | Institutional landing page and overview |
| `GET` | `/verify` | Public | Verification search portal (ID and bundle tabs) |
| `POST` | `/verify/id` | Public | Submits Certificate ID; redirects to `/verify/{id}` |
| `GET` | `/verify/{certificate_id}` | Public | Public verification result page (rate-limited) |
| `POST` | `/verify/bundle` | Public | Verifies uploaded or pasted JSON bundle |
| `GET` | `/certificates/{id}/pdf` | Public | Generates and downloads official A4 diploma PDF |
| `GET` | `/certificates/{id}/qr.png` | Public | Returns standalone QR code PNG pointing to verification URL |
| `GET` | `/certificates/{id}/bundle.json` | Public | Downloads standalone offline verification JSON bundle |
| `GET` | `/.well-known/issuer-public-key.pem` | Public | Returns issuer's public key in standard PEM format |
| `GET` | `/api/health` | Public | Health check returning status and database connectivity |
| `GET` | `/api/public-key` | Public | Returns public key SPKI PEM and SHA-256 fingerprint |
| `GET` | `/api/verify/{certificate_id}` | Public | JSON verification result for a certificate ID |
| `POST` | `/api/verify/bundle` | Public | JSON verification result for submitted JSON bundle |
| `GET` | `/api/certificates` | Local Only | Lists certificates with optional search and filter queries |
| `POST` | `/api/certificates` | Local Only | Programmatically signs and issues a new certificate |
| `POST` | `/api/certificates/{id}/revoke`| Local Only | Revokes a certificate by ID with reason |
| `GET` | `/issuer` | Local Only | Issuer dashboard listing registered certificates |
| `GET` | `/issuer/new` | Local Only | Form to issue a new certificate |
| `POST` | `/issuer/new` | Local Only | Handles certificate creation and redirects to detail |
| `GET` | `/issuer/certificates/{id}` | Local Only | Detailed view of certificate with download and revoke actions |
| `POST` | `/issuer/certificates/{id}/revoke`| Local Only | Revokes a certificate and records reason |
| `GET` | `/issuer/audit` | Local Only | Displays append-only audit trail and chain integrity status |
| `GET` | `/demo` | Demo Only | Interactive classroom tamper lab |
| `POST` | `/demo/tamper` | Demo Only | Tampers with a database field (with optional hash recomputation) |
| `POST` | `/demo/restore` | Demo Only | Restores original pristine record from temporary backup |
| `POST` | `/demo/bundle-check` | Demo Only | Verifies tampered or edited verification bundle JSON |

---

## 1. Public Verification Endpoints

### `GET /api/health`
- **Access**: Public
- **Description**: Verifies server health and database connectivity.
- **Example Response (200 OK)**:
  ```json
  {
    "status": "ok",
    "timestamp": "2026-10-17T13:30:00Z",
    "version": "1.0.0"
  }
  ```

### `GET /api/public-key`
- **Access**: Public
- **Description**: Returns the active issuer public key and its SHA-256 fingerprint.
- **Example Response (200 OK)**:
  ```json
  {
    "key_id": "KEY-2026-A1B2",
    "algorithm": "RSASSA-PSS",
    "hash_algorithm": "SHA-256",
    "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A...\n-----END PUBLIC KEY-----\n",
    "fingerprint_sha256": "4a5e9f8b2c1d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f"
  }
  ```

### `GET /api/verify/{certificate_id}`
- **Access**: Public (Rate-limited: 30 calls/min)
- **Description**: Performs full cryptographic verification on a certificate ID.
- **Example Response: VALID (200 OK)**:
  ```json
  {
    "certificate_id": "MIAS-2026-B8F2",
    "status": "VALID",
    "message": "Certificate signature is valid and record is active.",
    "signature_valid": true,
    "hash_matches": true,
    "revoked": false,
    "revocation": null,
    "payload": {
      "certificate_id": "MIAS-2026-B8F2",
      "student_name": "Aarav Mehta",
      "student_roll_no": "TY-CS-2026-014",
      "program": "B.Sc. Computer Science",
      "course": "Applied Cryptography",
      "certificate_title": "Certificate of Completion",
      "grade_or_result": "Distinction",
      "issue_date": "2026-10-12",
      "issuing_authority": "Meridian Institute of Advanced Studies",
      "key_id": "KEY-2026-A1B2"
    },
    "stored_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "recomputed_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "key_id": "KEY-2026-A1B2",
    "public_key_fingerprint": "4a5e9f8b2c1d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f",
    "verified_at": "2026-10-17T13:30:00Z"
  }
  ```

- **Example Response: TAMPERED (200 OK)**:
  ```json
  {
    "certificate_id": "MIAS-2026-B8F2",
    "status": "TAMPERED",
    "message": "Signature verification failed. Data has been altered.",
    "signature_valid": false,
    "hash_matches": false,
    "revoked": false,
    "revocation": null,
    "payload": { ... },
    "stored_hash": "e3b0c4...",
    "recomputed_hash": "a1b2c3...",
    "key_id": "KEY-2026-A1B2",
    "public_key_fingerprint": "4a5e9f...",
    "verified_at": "2026-10-17T13:30:00Z"
  }
  ```

- **Example Response: UNKNOWN (200 OK)**:
  ```json
  {
    "certificate_id": "MIAS-2026-9999",
    "status": "UNKNOWN",
    "message": "Certificate not found in registry.",
    "signature_valid": false,
    "hash_matches": false,
    "revoked": false,
    "revocation": null,
    "payload": null,
    "stored_hash": null,
    "recomputed_hash": null,
    "key_id": null,
    "public_key_fingerprint": null,
    "verified_at": "2026-10-17T13:30:00Z"
  }
  ```

---

## 2. Protected Administrative Endpoints (Local Only: 127.0.0.1)

### `POST /api/certificates`
- **Access**: Local Only (HTTP 403 for non-loopback clients; CSRF token required)
- **Description**: Issues a new certificate, creates RSASSA-PSS digital signature, and logs to audit trail.
- **Request Headers**:
  `X-CSRF-Token: <token>`
- **Request Body (JSON)**:
  ```json
  {
    "student_name": "Priya Sharma",
    "student_roll_no": "TY-CS-2026-088",
    "program": "B.Sc. Computer Science",
    "course": "Network Security",
    "certificate_title": "Certificate of Excellence",
    "grade_or_result": "First Class with Distinction",
    "issue_date": "2026-10-16"
  }
  ```
- **Response (201 Created)**:
  ```json
  {
    "certificate_id": "MIAS-2026-F9A1",
    "student_name": "Priya Sharma",
    "student_roll_no": "TY-CS-2026-088",
    "program": "B.Sc. Computer Science",
    "course": "Network Security",
    "certificate_title": "Certificate of Excellence",
    "grade_or_result": "First Class with Distinction",
    "issue_date": "2026-10-16",
    "issuing_authority": "Meridian Institute of Advanced Studies",
    "payload_sha256": "8f3b2a...",
    "signature_hex": "5c9d1e...",
    "key_id": "KEY-2026-A1B2",
    "created_at": "2026-10-17T13:35:00Z"
  }
  ```

### `POST /api/certificates/{certificate_id}/revoke`
- **Access**: Local Only (CSRF token required)
- **Description**: Revokes an existing certificate by recording the revocation reason.
- **Request Body (JSON)**:
  ```json
  {
    "reason": "Administrative correction: duplicate record issued."
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "certificate_id": "MIAS-2026-F9A1",
    "revoked": true,
    "reason": "Administrative correction: duplicate record issued.",
    "revoked_at": "2026-10-17T13:40:00Z"
  }
  ```

---

## 3. Demonstration & Tamper Lab Endpoints

### `POST /demo/tamper`
- **Access**: Local Only, Demo Mode Enabled
- **Form Parameters**:
  - `certificate_id`: ID of target certificate
  - `field`: Field name to edit (`student_name`, `grade_or_result`, etc.)
  - `new_value`: Replacement value
  - `recompute_hash`: `"on"` or empty. When `"on"`, updates `payload_sha256` to the new hash without re-signing.
  - `csrf_token`: Valid CSRF token
- **Response**: 303 Redirect to `/demo?cert={certificate_id}`.

### `POST /demo/restore`
- **Access**: Local Only, Demo Mode Enabled
- **Form Parameters**:
  - `certificate_id`: ID of target certificate
  - `csrf_token`: Valid CSRF token
- **Response**: 303 Redirect to `/demo?cert={certificate_id}`. Restores original un-tampered record.
