# 09: Viva Voce & Technical Defense Q&A

## Purpose
This document provides 30 technical questions and concise, mathematically rigorous answers for evaluators, examiners, and viva voce defense.

---

### Q1: What is the fundamental difference between a cryptographic hash and a digital signature?
**Answer**: A cryptographic hash (e.g., SHA-256) is an unkeyed one-way function that produces a fixed-size digest representing data integrity; anyone can compute the hash of any input. A digital signature (e.g., RSASSA-PSS) uses asymmetric key cryptography (private key to sign, public key to verify) to provide data integrity, authenticity of origin, and non-repudiation. A hash proves that data hasn't accidentally changed; a digital signature proves *who* issued it.

---

### Q2: Why did you choose RSASSA-PSS over the older PKCS#1 v1.5 padding scheme?
**Answer**: RSASSA-PSS (RFC 8017) has a mathematical proof of security in the Random Oracle Model, reducing its security directly to the hardness of the RSA problem. PKCS#1 v1.5 is ad-hoc, deterministic, and susceptible to formatting oracle attacks (such as Bleichenbacher's attack) if verification implementations fail to parse ASN.1 structures strictly. PSS incorporates random salt, ensuring probabilistic signatures that resist malleability.

---

### Q3: Why is 2048-bit RSA modulus chosen instead of 1024 or 4096 bits?
**Answer**: 1024-bit RSA has been deprecated by NIST since 2013 due to feasible factorization by well-funded adversaries. 2048-bit RSA provides approximately 112 bits of symmetric security margin, which NIST and BSI evaluate as fully secure for digital signatures through at least 2030. 4096-bit RSA increases signature generation and verification times by 4x to 8x with diminishing security returns for general institutional documents.

---

### Q4: Why is deterministic JSON canonicalization necessary before signing, and how does your implementation work?
**Answer**: Digital signatures operate strictly on sequences of raw bytes, not abstract data structures. Standard JSON encoders vary in dictionary key ordering, whitespace around delimiters, and character normalization across programming languages (e.g., Python vs JavaScript). Without canonicalization, decoding and re-encoding valid data creates different byte streams, causing signature verification to fail falsely.
In this project, we implement: Deterministic canonical JSON: fixed field set, keys sorted alphabetically, compact separators (',' and ':'), UTF-8 encoding, and Unicode NFC normalization with surrounding whitespace stripped. It is inspired by JSON Canonicalization Scheme (RFC 8785) but is not a full implementation of it.

---

### Q5: What does a QR code on a certificate prove, and what does it NOT prove?
**Answer**: A QR code on a certificate encodes only a URL pointing to the verification portal. It proves **nothing** by itself because an attacker can forge a physical certificate, create a spoofed website on a fake domain, and print a QR code linking to their fake portal. The cryptographic proof comes solely from the verification endpoint reconstructing the certificate's canonical bytes and mathematically validating the RSASSA-PSS signature against the institution's public key.

---

### Q6: Why does the "hash-recompute attack" in your Tamper Lab fail?
**Answer**: In the Tamper Lab, an attacker alters a student's name and recalculates the SHA-256 hash in the database. When the verifier runs, the recomputed hash matches the stored hash, passing the hash check. However, the verifier then checks the RSASSA-PSS digital signature over the altered canonical bytes using the public key. Because the attacker lacks the institution's RSA private key, they cannot generate a valid signature for the altered bytes. The signature verification fails, exposing the tampering.

---

### Q7: How does certificate revocation work, and why does it not alter the signed certificate?
**Answer**: Revocation is recorded in an independent `revocations` table containing the `certificate_id`, `reason`, and `revoked_at` timestamp. The signed certificate record is intentionally left unaltered. Altering or deleting the signed record would invalidate the cryptographic signature, destroying the historical truth that the institution did legitimately confer that credential at that date and time. Revocation is a registry status query, not a deletion of historical conferral.

---

### Q8: What happens if the institution's private key is stolen or leaked?
**Answer**: The entire security model is compromised. An attacker in possession of `issuer_private.pem` can forge arbitrary credentials that will pass all cryptographic signature checks against the public key. In production, this requires an immediate emergency key revocation notice, transitioning verifiers to a new keypair, and implementing Hardware Security Modules (HSMs) with strict multi-party access control.

---

### Q9: Why didn't you use a blockchain (e.g., Ethereum or Hyperledger) for this registry?
**Answer**: Academic credential issuance by an accredited university is an authoritative, single-entity trust model. Blockchains solve Byzantine consensus among untrusted, decentralized peers, which introduces high transaction costs, network latency, energy consumption, and irreversible public ledger storage that violates data privacy regulations (GDPR "Right to be Forgotten" and FERPA). Standard public-key cryptography provides mathematically unforgeable credentials without distributed consensus overhead.

---

### Q10: What is a replay attack in this context, and how is it prevented?
**Answer**: A replay attack involves taking a validly issued certificate belonging to Student A and presenting it under the identity of Student B. This is impossible because the signed canonical payload irrevocably binds the student's unique institutional roll number, student name, degree program, course, and certificate ID into a single cryptographic digest. Any attempt to substitute Student B's name causes signature verification to fail immediately.

---

### Q11: Why does online verification rebuild the payload from stored database fields instead of reading an uploaded file?
**Answer**: Rebuilding the payload directly from individual database columns guarantees that the verifier tests the exact current state of the database record. If an attacker modifies an individual database column (e.g., changes grade from 'Pass' to 'Distinction'), reconstructing the payload from the modified column causes the hash and signature checks to fail, immediately exposing database tampering.

---

### Q12: How does offline verification work without server or internet connectivity?
**Answer**: The standalone offline verification script (`python scripts/verify_offline.py <bundle.json> <issuer_public.pem>`) takes an exported verification bundle JSON (containing the payload and Base64-encoded signature `signature_b64`) and the institution's public key PEM file. It serializes the payload using our deterministic canonical JSON rules, recomputes the SHA-256 hash, and verifies the RSASSA-PSS signature locally using the `cryptography` library. No network traffic or database access occurs.

---

### Q13: Why are the Issuer workspace routes loopback-only, and what does this NOT protect against?
**Answer**: Restricting `/issuer/*` to `127.0.0.1` and `::1` ensures that remote computers on the local network (LAN) cannot access the credential issuance form or trigger administrative actions. However, it does **not** protect against unauthorized users who have physical or SSH access to the server machine itself. In production, this network guard must be augmented with cryptographic identity and multi-factor authentication (SSO).

---

### Q14: What is the significance of the 32-byte salt length in your RSASSA-PSS configuration?
**Answer**: In RSASSA-PSS, the salt length determines the degree of randomization injected during signature generation. Setting `salt_length=32` bytes matches the digest size of SHA-256 ($256 \text{ bits} = 32 \text{ bytes}$). This adheres to NIST FIPS 186-4 recommendations and yields the tightest mathematical security proof reduction in the Random Oracle Model.

---

### Q15: What is the difference between a `key_id` and a public-key fingerprint?
**Answer**: A `key_id` (e.g., `KEY-2026-A1B2`) is a short, human-readable identifier assigned to a specific keypair to quickly index which key was used during issuance. A public-key fingerprint is the full, cryptographically collision-resistant SHA-256 digest of the DER-encoded SubjectPublicKeyInfo structure (64 hex characters). The fingerprint is the authoritative cryptographic binding; the key ID is merely an administrative tag.

---

### Q16: How does the append-only audit log work, and what are its limitations?
**Answer**: The `audit_log` table implements a cryptographic hash chain: each record includes `prev_hash`, which is the SHA-256 digest of the immediately preceding record, and `entry_hash`, which hashes the current row's fields concatenated with `prev_hash`. If an adversary modifies row 2, the `prev_hash` stored in row 3 will no longer match the recomputed hash of row 2, breaking the chain. However, because the audit log resides in the same SQLite file, an attacker with full database write permissions could rewrite the entire chain forward from the point of modification.

---

### Q17: Why does the system use ReportLab built-in fonts rather than custom TrueType fonts?
**Answer**: Standard Type 1 core fonts (`Helvetica`, `Times-Roman`, `Courier`) are part of the native PDF specification and are rendered by all PDF readers worldwide without requiring embedded font files. This guarantees 100% offline operation and eliminates external font downloads or network dependencies, satisfying our strict air-gapped design requirement.

---

### Q18: What is the vulnerability of serving the public key from the same web server as the verification portal?
**Answer**: If a server is completely compromised, an attacker could replace both the private key and the public key simultaneously, or redirect DNS to a malicious server serving their own public key. To defend against this, verifiers should check the public-key fingerprint printed on the certificate against an out-of-band published fingerprint, or use the offline verifier with a pre-trusted public key.

---

### Q19: What is the purpose of the sliding-window rate limiter on the verification routes?
**Answer**: RSASSA-PSS verification involves modular exponentiation. While fast (~0.2ms), flooding the endpoint with thousands of requests per second could lead to CPU exhaustion (Denial-of-Service). The rate limiter restricts client IPs to 30 requests per minute, preventing automated scrapers and brute-force attacks.

---

### Q20: Why do you enforce Content-Security-Policy (CSP) with `script-src 'self'` and `style-src 'self'`?
**Answer**: Preventing inline `<style>` and `<script>` tags, inline event handlers (`onclick=`), and external CDNs mitigates Cross-Site Scripting (XSS) and data exfiltration attacks. Any injected script from an attacker is blocked by the browser engine. Furthermore, it ensures the application operates entirely offline with zero external network leaks.

---

### Q21: What prevents an attacker from generating a certificate with a future or past date?
**Answer**: In this prototype, the issue date is an input field signed by the local issuer. There is no external RFC 3161 Time-Stamp Authority (TSA). An authorized issuer could backdate a certificate. In an enterprise deployment, the canonical payload would be submitted to a trusted TSA to obtain an unalterable cryptographic timestamp token embedded alongside the signature.

---

### Q22: What happens if someone tries to upload a massive file to `/verify/bundle`?
**Answer**: `app/routers/public.py` checks uploaded file sizes against `settings.max_upload_bytes` (1 MB) by reading only up to the limit plus one byte. If the payload exceeds 1 MB, it aborts immediately and raises HTTP 413 Payload Too Large, preventing memory exhaustion attacks.

---

### Q23: Why is SQLite used with synchronous `def` functions rather than `async def` in FastAPI?
**Answer**: Python's standard `sqlite3` driver is synchronous and blocking. Running blocking SQLite queries inside an `async def` route blocks FastAPI's main asyncio event loop, degrading concurrency. Declaring route functions with standard `def` causes FastAPI to run them in an external threadpool (`starlette.concurrency.run_in_threadpool`), preserving server responsiveness.

---

### Q24: What is the mathematical relationship between the private key, public key, and signature in RSA?
**Answer**: The RSA public key consists of modulus $N = p \cdot q$ and public exponent $e$. The private key includes private exponent $d$, where $e \cdot d \equiv 1 \pmod{\phi(N)}$. Signing computes $\sigma = (M_{\text{padded}})^d \pmod{N}$. Verification computes $M' = \sigma^e \pmod{N}$ and checks that $M'$ satisfies the PSS padding format for the message digest.

---

### Q25: Why is the certificate ID formatted as `MIAS-YYYY-XXXX`?
**Answer**: `MIAS` identifies the institution (Meridian Institute of Advanced Studies), `YYYY` represents the academic conferral year, and `XXXX` is a 4-character random uppercase hexadecimal string generated from cryptographic randomness (`secrets.token_hex(2)`), providing 65,536 unique IDs per year with negligible collision probability.

---

### Q26: Can a revoked certificate ever be "un-revoked"?
**Answer**: In our security model, revocations are designed to be permanent. The `revocations` table uses `certificate_id` as a primary key. Re-issuing an invalidated credential requires generating a brand new certificate with a new certificate ID, new cryptographic signature, and fresh audit record.

---

### Q27: How does CSRF token verification protect the issuer workspace?
**Answer**: The server sets a cryptographically random token in an HTTP-only/SameSite=Lax cookie and requires the exact matching token in a hidden form input or `X-CSRF-Token` header. If a logged-in user visits a malicious website, the attacker's script cannot read or forge the custom header/field, preventing unauthorized credential issuance or revocation.

---

### Q28: What is the role of the `_demo_backups` table?
**Answer**: The `_demo_backups` table is a demonstration-only utility used by `/demo/tamper` to snapshot the original, pristine certificate row as JSON before modifying fields. This allows live demonstration evaluators to click "Restore original" to return the database to a valid state without resetting the entire database.

---

### Q29: What happens if a non-Latin character (e.g., Hindi or Japanese) is entered into the student name field?
**Answer**: The canonicalization and cryptographic signing engines handle all UTF-8 characters flawlessly. However, because ReportLab uses built-in Standard Type 1 Latin-1 fonts to remain 100% offline, generating a PDF diploma for names with characters outside the Latin-1 range raises an encoding error. In production, this would be addressed by embedding an open-source Unicode font (such as Noto Sans).

---

### Q30: What is the single biggest security takeaway of this project?
**Answer**: Visual inspection and unkeyed hashes are fundamentally incapable of proving credential authenticity. A cryptographic digital signature—where data is deterministically serialized and signed with an asymmetric private key—is the only mechanism that allows verifiers to mathematically prove integrity, origin authenticity, and non-repudiation, both online and completely offline.
