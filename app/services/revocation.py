from datetime import datetime, timezone
from app.services import audit


def revoke_certificate(conn, certificate_id: str, reason: str) -> None:
    certificate_id = (certificate_id or "").strip()
    reason = (reason or "").strip()

    if len(reason) < 3 or len(reason) > 200:
        raise ValueError("Reason must be between 3 and 200 characters.")

    cert = conn.execute(
        "SELECT certificate_id FROM certificates WHERE certificate_id = ?",
        (certificate_id,),
    ).fetchone()
    if cert is None:
        raise LookupError(f"Certificate {certificate_id} not found.")

    rev = conn.execute(
        "SELECT certificate_id FROM revocations WHERE certificate_id = ?",
        (certificate_id,),
    ).fetchone()
    if rev is not None:
        raise FileExistsError(f"Certificate {certificate_id} is already revoked.")

    revoked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.execute(
        "INSERT INTO revocations (certificate_id, revoked_at, reason) VALUES (?, ?, ?)",
        (certificate_id, revoked_at, reason),
    )
    audit.add_entry(conn, "REVOKED", certificate_id, reason)
