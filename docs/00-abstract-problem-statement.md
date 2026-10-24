# 00: Abstract & Problem Statement

## Purpose
This document defines the core problem addressed by the **Meridian Certificate Registry**, outlines why traditional paper and digital credentials fail, and specifies the solution implemented in this project.

---

## The Problem: Credential Forgery and Blind Trust

Academic and professional credentials represent significant value, granting individuals access to employment, advanced education, and licensing. However, the conventional methods for issuing and verifying certificates suffer from critical security vulnerabilities:

1. **Physical Certificates and Scans Lack Verifiable Authenticity**:
   - Paper certificates with embossed seals, signatures, and watermarks can be forged using modern graphic design tools and high-resolution printing.
   - Digital representations (PDF scans, JPEG copies) are trivial to edit; altering a student's name, degree title, or GPA requires minimal technical skill and leaves virtually no visual artifact when inspected on a screen.

2. **The "QR Code Fallacy"**:
   - Many institutions place QR codes on certificates claiming they provide "digital verification".
   - In practice, a standard QR code only encodes a URL pointing to a website.
   - A malicious actor can forge a certificate, host a convincing clone of the university's verification page on a lookalike domain, and link the QR code to their fake portal. Without cryptographic proof tied directly to the certificate's data, a QR code proves nothing by itself.

3. **Insecure Central Databases**:
   - Traditional databases store records in plain text or simple hashes. If database records are modified, there is no cryptographic mechanism embedded in the credential itself to expose the modification.
   - Employers contacting university registrars manually face weeks of turnaround time, prompting many to rely on unverified digital scans.

---

## The Solution: Meridian Certificate Registry

**Meridian Certificate Registry** is an institutional academic credential issuance and verification platform built on modern public-key cryptography. Instead of relying on visual trust or unauthenticated links, every certificate is an immutable, self-verifying cryptographic object.

### Key Capabilities

1. **Deterministic Canonicalization**:
   - Deterministic canonical JSON: fixed field set, keys sorted alphabetically, compact separators (',' and ':'), UTF-8 encoding, and Unicode NFC normalization with surrounding whitespace stripped. It is inspired by JSON Canonicalization Scheme (RFC 8785) but is not a full implementation of it.
   - This eliminates serialization discrepancies across different operating systems, languages, and JSON engines.

2. **Digital Signatures via RSASSA-PSS**:
   - The canonical payload is fingerprinted with SHA-256 and signed by the institution's private key using **RSASSA-PSS** (Probabilistic Signature Scheme) with SHA-256, MGF1-SHA-256, and a 32-byte random salt.
   - PSS provides provable security bounds and resists chosen-ciphertext and signature malleability attacks that plague legacy PKCS#1 v1.5 schemes.

3. **Dual Verification Channels**:
   - **Online Registry Verification**: Verifiers can query by Certificate ID or scan the embedded QR code. The registry dynamically reconstructs the certificate payload from stored database fields, recomputes the SHA-256 hash, verifies the digital signature against the issuer's public key, and verifies revocation status.
   - **Offline Standalone Bundle Verification**: Every certificate can be exported as an offline verification bundle JSON containing the payload, cryptographic signature, and public key identifier. Anyone with the institution's public key can verify the credential offline using the provided CLI tool, independent of server availability.

4. **Tamper Detection and Educational Demonstration**:
   - An integrated **Tamper Lab** demonstrates real-time detection of data tampering.
   - It exposes the critical cryptographic distinction between a hash and a digital signature: modifying data and recomputing its SHA-256 hash allows the hash to match, but the RSA-PSS digital signature fails because the attacker lacks the private signing key.

5. **Separate Revocation Mechanism**:
   - Revocation never alters the signed certificate record; the cryptographic signature remains permanently valid as an artifact of conferral. Revocations are logged in a separate table and queried at verification time.
