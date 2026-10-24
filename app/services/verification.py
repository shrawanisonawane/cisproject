from dataclasses import dataclass, asdict
from datetime import datetime, timezone

from app.crypto import keys as keylib
from app.crypto.canonical import (
    SCHEMA_VERSION, SIGNED_FIELDS, CanonicalizationError, canonicalize,
)
from app.crypto.signing import sha256_hex, verify_bytes

VALID, UNKNOWN, TAMPERED, REVOKED = "VALID", "UNKNOWN", "TAMPERED", "REVOKED"


class BundleFormatError(ValueError):
    pass


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class VerificationResult:
    status: str
    message: str
    method: str
    verified_at: str
    certificate: dict | None = None
    stored_hash: str | None = None
    recomputed_hash: str | None = None
    hash_matches: bool | None = None
    signature_valid: bool | None = None
    registry_match: bool | None = None
    key_id: str | None = None
    fingerprint: str | None = None
    revoked_at: str | None = None
    revocation_reason: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def payload_from_row(row) -> dict:
    """Rebuild the signed payload from the CURRENT database columns."""
    payload = {name: row[name] for name in SIGNED_FIELDS if name != "schema_version"}
    payload["schema_version"] = SCHEMA_VERSION
    return payload


def _log(conn, certificate_id, method, status) -> None:
    conn.execute(
        "INSERT INTO verification_log (ts, certificate_id, method, result) VALUES (?, ?, ?, ?)",
        (now_utc(), certificate_id, method, status),
    )


def _revocation(conn, certificate_id):
    return conn.execute(
        "SELECT revoked_at, reason FROM revocations WHERE certificate_id = ?",
        (certificate_id,),
    ).fetchone()


def verify_by_id(conn, certificate_id: str, public_key, method: str = "ID") -> VerificationResult:
    verified_at = now_utc()
    fingerprint = keylib.fingerprint_colon(public_key)
    certificate_id = (certificate_id or "").strip()
    row = conn.execute(
        "SELECT * FROM certificates WHERE certificate_id = ?", (certificate_id,)
    ).fetchone()

    if row is None:
        result = VerificationResult(
            UNKNOWN, "No certificate with this ID exists in this registry.",
            method, verified_at, fingerprint=fingerprint,
        )
        _log(conn, certificate_id or None, method, result.status)
        return result

    certificate = dict(row)
    stored_hash = row["payload_sha256"]
    try:
        canonical = canonicalize(payload_from_row(row))
    except CanonicalizationError:
        result = VerificationResult(
            TAMPERED,
            "The stored certificate record is malformed and cannot match the signature.",
            method, verified_at, certificate=certificate, stored_hash=stored_hash,
            hash_matches=False, signature_valid=False,
            key_id=row["key_id"], fingerprint=fingerprint,
        )
        _log(conn, certificate_id, method, result.status)
        return result

    recomputed = sha256_hex(canonical)
    hash_matches = recomputed == stored_hash
    signature_valid = verify_bytes(public_key, canonical, row["signature_b64"])

    result = VerificationResult(
        VALID, "", method, verified_at, certificate=certificate,
        stored_hash=stored_hash, recomputed_hash=recomputed,
        hash_matches=hash_matches, signature_valid=signature_valid,
        key_id=row["key_id"], fingerprint=fingerprint,
    )

    if not signature_valid:
        result.status = TAMPERED
        result.message = ("The certificate details do not match the issuer's digital "
                          "signature. They were changed after issuance.")
    else:
        revocation = _revocation(conn, certificate_id)
        if revocation is not None:
            result.status = REVOKED
            result.revoked_at = revocation["revoked_at"]
            result.revocation_reason = revocation["reason"]
            result.message = ("This certificate was genuinely issued, but it has since "
                              "been revoked. Its signature is still authentic.")
        else:
            result.status = VALID
            result.message = ("The digital signature matches the certificate details "
                              "and the certificate has not been revoked.")

    _log(conn, certificate_id, method, result.status)
    return result


def verify_bundle(conn, bundle: dict, public_key, method: str = "BUNDLE") -> VerificationResult:
    """Verify a submitted bundle. Never trusts any hash or status inside the bundle."""
    if not isinstance(bundle, dict) or "payload" not in bundle or "signature_b64" not in bundle:
        raise BundleFormatError("Bundle must contain 'payload' and 'signature_b64'.")
    payload = bundle["payload"]
    signature_b64 = bundle["signature_b64"]
    if not isinstance(signature_b64, str):
        raise BundleFormatError("'signature_b64' must be text.")
    try:
        canonical = canonicalize(payload)
    except CanonicalizationError as exc:
        raise BundleFormatError(str(exc))

    verified_at = now_utc()
    fingerprint = keylib.fingerprint_colon(public_key)
    recomputed = sha256_hex(canonical)
    signature_valid = verify_bytes(public_key, canonical, signature_b64)
    certificate_id = payload["certificate_id"].strip()

    result = VerificationResult(
        VALID, "", method, verified_at, certificate=dict(payload),
        recomputed_hash=recomputed, signature_valid=signature_valid,
        key_id=payload.get("key_id"), fingerprint=fingerprint,
    )

    if not signature_valid:
        result.status = TAMPERED
        result.message = ("The signature does not match the submitted certificate details. "
                          "The details were changed, or the signature is not from this issuer.")
        _log(conn, certificate_id, method, result.status)
        return result

    row = conn.execute(
        "SELECT * FROM certificates WHERE certificate_id = ?", (certificate_id,)
    ).fetchone()
    if row is None:
        result.status = UNKNOWN
        result.message = ("The signature is authentic, but this certificate is not in this "
                          "registry.")
        _log(conn, certificate_id, method, result.status)
        return result

    result.stored_hash = row["payload_sha256"]
    try:
        registry_canonical = canonicalize(payload_from_row(row))
    except CanonicalizationError:
        registry_canonical = None
    result.registry_match = registry_canonical == canonical
    if not result.registry_match:
        result.status = TAMPERED
        result.message = ("The submitted bundle carries an authentic signature, but this "
                          "registry's stored record differs from it. The registry record was altered.")
        _log(conn, certificate_id, method, result.status)
        return result

    revocation = _revocation(conn, certificate_id)
    if revocation is not None:
        result.status = REVOKED
        result.revoked_at = revocation["revoked_at"]
        result.revocation_reason = revocation["reason"]
        result.message = ("This certificate was genuinely issued, but it has since been "
                          "revoked. Its signature is still authentic.")
    else:
        result.status = VALID
        result.message = ("The digital signature matches the certificate details and the "
                          "certificate has not been revoked.")
    _log(conn, certificate_id, method, result.status)
    return result
