# 03: Cryptographic Design & Implementation

## Purpose
This document provides an in-depth explanation of the cryptographic algorithms, parameters, serialization guarantees, and operational procedures implemented in the **Meridian Certificate Registry**.

---

## 1. Algorithmic Choices & Rationales

### Why SHA-256?
- **Security Margin**: SHA-256 (part of the NIST Secure Hash Standard FIPS 180-4) provides a 128-bit security level against collision attacks and 256-bit security against preimage attacks. There are no known practical collision attacks against SHA-256.
- **Widespread Hardware Acceleration**: SHA-256 is natively supported by hardware extensions on modern x86-64 (Intel SHA-NI) and ARMv8 processors, enabling sub-microsecond hashing.
- **Fixed-Size Compact Fingerprints**: Produces a 32-byte (256-bit) digest (64 hexadecimal characters), which fits comfortably in database columns, audit records, and printed QR codes.

### Why RSA-2048?
- **Industry Standard for Long-Term Academic Records**: NIST Special Publication 800-57 Part 1 Rev. 5 rates 2048-bit RSA as secure for general digital signatures through at least 2030, providing a 112-bit security level.
- **Universal Verification Compatibility**: RSA public key verification is supported by every programming language, cryptography runtime, and web browser without requiring custom elliptic curve bindings.
- **Fast Public-Key Verification**: RSA verification with public exponent $e = 65537$ requires only 17 modular multiplications, making signature verification significantly faster than ECDSA or Ed25519 (~0.2ms vs ~1.5ms on commodity CPUs).

### Why RSASSA-PSS Rather Than PKCS#1 v1.5?
- **Provable Security Bounds**: PKCS#1 v1.5 uses deterministic padding which makes it vulnerable to formatting oracle attacks (e.g., Bleichenbacher's signature forgery attack) if parsing implementations fail to strictly enforce ASN.1 encoding checks.
- **Probabilistic Padding (PSS)**: RSASSA-PSS (RFC 8017 Section 8.1) is provably secure in the Random Oracle Model, reducing the security of the signature scheme directly to the hardness of the RSA problem (inverting the RSA trapdoor permutation).
- **Randomized Signature per Run**: PSS incorporates a cryptographic random salt into the padding. Signing the exact same canonical payload twice produces two distinct, equally valid signatures. This eliminates chosen-message chosen-ciphertext algebraic relations.

### Why Salt Length 32?
- In `app/crypto/signing.py`, the salt length is set explicitly to `32` bytes:
  ```python
  padding.PSS(
      mgf=padding.MGF1(hashes.SHA256()),
      salt_length=32,  # 32 bytes == 256 bits, matching SHA-256 output length
  )
  ```
- Matching the salt length to the hash output size ($h_{len} = 32$) aligns with NIST FIPS 186-4 recommendations and provides the tightest security proof for RSASSA-PSS.

---

## 2. Deterministic Canonicalization

Digital signatures operate on exact bytes. In modern web environments, JSON data is routinely decoded and re-encoded. Standard JSON encoders introduce ambiguities:
1. **Key Ordering**: Python dictionaries may preserve insertion order, while JavaScript engines or SQLite JSON functions may sort alphabetically or hash keys differently.
2. **Whitespace**: Spaces after colons, indentation, and trailing newlines alter the byte representation without changing the semantic data.
3. **Character Encoding**: Escape sequences (e.g., `\u0026` vs `&`) or variable character encodings break raw byte comparisons.

### What Canonicalization Prevents
Without deterministic canonicalization, a verifier testing a valid credential on a different machine, operating system, or runtime would re-serialize the JSON with slightly different spacing or key order. The recomputed SHA-256 hash would differ, and the RSA signature would fail, falsely flagging an authentic certificate as tampered.

### Implementation in `app/crypto/canonical.py`
Deterministic canonical JSON: fixed field set, keys sorted alphabetically, compact separators (',' and ':'), UTF-8 encoding, and Unicode NFC normalization with surrounding whitespace stripped. It is inspired by JSON Canonicalization Scheme (RFC 8785) but is not a full implementation of it.

The exact rules enforced in `canonicalize(payload)` are:
- Rejects non-dict payloads (`CanonicalizationError("Payload must be an object.")`).
- Requires precisely the 11 `SIGNED_FIELDS` (`schema_version`, `certificate_id`, `student_name`, `student_roll_no`, `program`, `course`, `certificate_title`, `grade_or_result`, `issuing_authority`, `issue_date`, `key_id`). Rejects any missing or unexpected extra fields.
- Rejects non-string values (`CanonicalizationError("All signed fields must be text.")`).
- Applies Unicode NFC normalization and strips leading/trailing whitespace via `unicodedata.normalize("NFC", value).strip()`.
- Serializes via `json.dumps(cleaned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")`.

---

## 3. Exact Signing and Verification Algorithms

### Signing Workflow (`app/services/issuance.py` & `app/crypto/signing.py`)
1. **Construct Payload Dictionary**: Assemble student name, roll number, academic program, course, certificate title, grade/result, issue date, issuing authority, certificate ID, and key ID with `schema_version = "1"`.
2. **Canonicalize**: Pass payload dictionary to `canonicalize()`, yielding `canonical_bytes`.
3. **Compute Hash**: Calculate `payload_sha256 = sha256_hex(canonical_bytes)` using Python's `hashlib.sha256(canonical_bytes).hexdigest()`.
4. **Sign**: Pass `canonical_bytes` and the RSA private key to `sign_bytes()`:
   $$\sigma = \text{RSASSA-PSS-Sign}_{K_{\text{priv}}}(\text{canonical\_bytes})$$
   Serialized as an ASCII Base64 string (`signature_b64`).
5. **Persist**: Store individual field columns, `payload_sha256`, and `signature_b64` in the SQLite `certificates` table.

### Verification Workflow (`app/services/verification.py`)
1. **Reconstruct Payload**: Reassemble the payload dictionary using stored database columns (or from an uploaded JSON bundle).
2. **Recompute Canonical Bytes**: Pass reconstructed payload to `canonicalize()`.
3. **Recompute Hash**: Calculate $H_{\text{recomputed}} = \text{sha256\_hex}(\text{canonical\_bytes})$.
4. **Compare Hash**:
   $$\text{hash\_matches} = (H_{\text{recomputed}} == H_{\text{stored}})$$
5. **Verify Digital Signature**:
   Verify Base64 signature using the issuer's public key $K_{\text{pub}}$ via `verify_bytes()`:
   $$\text{signature\_valid} = \text{RSASSA-PSS-Verify}_{K_{\text{pub}}}(\text{canonical\_bytes}, \text{signature\_b64})$$
6. **Query Revocation Registry**:
   Check if `certificate_id` exists in the `revocations` table.
7. **Evaluate Status**:
   - If $\text{signature\_valid} == \text{False} \implies \textbf{TAMPERED}$
   - If $\text{signature\_valid} == \text{True} \land \text{Revoked} \implies \textbf{REVOKED}$
   - If $\text{signature\_valid} == \text{True} \land \neg \text{Revoked} \implies \textbf{VALID}$

---

## 4. Key Lifecycle, Storage & Fingerprinting

### Key Generation (`scripts/generate_keys.py`)
- Generates an RSA keypair with 2048-bit modulus and public exponent $e = 65537$.
- Derives a persistent `key_id` formatted as `KEY-YYYY-XXXX` based on the SHA-256 hash of the public key.
- Private Key Storage: `keys/issuer_private.pem`, serialized as PKCS#8. Encrypted with `BestAvailableEncryption` using a passphrase configured in `.env`. File permissions restricted to the running process.
- Public Key Storage: `keys/issuer_public.pem`, serialized as SubjectPublicKeyInfo (SPKI) in PEM format.

### Public-Key Fingerprint (`app/crypto/keys.py`)
The public-key fingerprint is computed as:
$$\text{Fingerprint} = \text{SHA-256}(\text{DER-encoded SubjectPublicKeyInfo})$$
Formatted as a 64-character lowercase hex string.
This fingerprint is:
- Printed on the physical PDF diploma.
- Returned by `/api/public-key`.
- Checked during verification to allow verifiers to detect out-of-band key substitution.

---

## 5. Hash vs Digital Signature (Core Theoretical Concept)

| Property | Cryptographic Hash (SHA-256) | Digital Signature (RSASSA-PSS) |
|---|---|---|
| **Underlying Math** | Merkle-Damgård iterative compression | Trapdoor permutation (RSA modular exponentiation) |
| **Key Required** | None (public algorithm) | Private key for signing; Public key for verification |
| **What It Proves** | **Integrity only**: Data has not changed since the hash was recorded. | **Integrity + Authenticity + Non-Repudiation**: Proves *who* created the data. |
| **Attacker Ability** | Any attacker who modifies data can simply run SHA-256 again to produce a matching hash. | An attacker cannot forge a signature without factoring $N$ or stealing $K_{\text{priv}}$. |
| **Role in Meridian** | Verifies stored column consistency against the issuance snapshot. | Guarantees the credential originated exclusively from the legitimate institution. |

---

## 6. Audit of Standards, RFCs, and Security Properties

The table below lists every standard, RFC, and cryptographic property claimed across this documentation, and explicitly states whether and how the codebase implements it:

| Standard / Claim | Context | Implemented in Code? | Implementation Details & Code Verification |
|---|---|---|---|
| **FIPS 180-4** (SHA-256) | Hashing canonical payload and public key | **Yes** | Uses Python's standard `hashlib.sha256()`. Generates 256-bit digests across `canonicalize()` output and public key DER bytes. |
| **NIST SP 800-57** (RSA-2048) | Asymmetric key size & security margin | **Yes** | `app/crypto/keys.py` calls `rsa.generate_private_key(public_exponent=65537, key_size=2048)`. |
| **RFC 8017 / PKCS#1 v2.2** | RSASSA-PSS digital signature scheme | **Yes** | `app/crypto/signing.py` configures `padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32)` with `hashes.SHA256()`. |
| **NIST FIPS 186-4** | Salt length = 32 bytes ($h_{len}$) | **Yes** | `app/crypto/signing.py` explicitly sets `SALT_LENGTH = 32`, matching SHA-256 output length. |
| **PKCS#8** | Private key storage format | **Yes** | `app/crypto/keys.py` serializes using `serialization.PrivateFormat.PKCS8` with `BestAvailableEncryption` (passphrase-protected). |
| **SPKI (X.509)** | Public key PEM export | **Yes** | `app/crypto/keys.py` serializes using `serialization.PublicFormat.SubjectPublicKeyInfo`. |
| **RFC 8785 (JCS)** | JSON Canonicalization | **No (Inspired only)** | **Not a full implementation**. `app/crypto/canonical.py` uses fixed field ordering, alphabetized keys, compact separators `(",", ":")`, UTF-8, and Unicode NFC normalization with stripped whitespace. It does not implement general RFC-8785 number/float serialization. |
| **Constant-time Token Compare** | CSRF Token validation | **Yes** | `app/security.py` uses `secrets.compare_digest(cookie_token, form_token)`. Stored hash string comparison uses standard equality since hashes are public. |
| **RFC 3161** | Trusted Time-Stamp Authority | **No** | Timestamps use local system UTC time (`datetime.now(timezone.utc)`). No external TSA is queried. |
| **X.509 CRL / OCSP** | Distributed revocation checking | **No** | Revocation is stored and checked locally via SQLite `revocations` table, not distributed CRL/OCSP responders. |
| **Key Rotation** | Cryptographic key rollover | **No** | Single institutional keypair architecture. Key rotation and multi-key trust chains are not implemented. |
