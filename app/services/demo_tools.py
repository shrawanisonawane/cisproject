import json
from datetime import datetime, timezone

from app.crypto.canonical import canonicalize
from app.crypto.signing import sha256_hex
from app.services import audit
from app.services.verification import payload_from_row

ALLOWED_TAMPER_FIELDS = {
    "student_name",
    "student_roll_no",
    "program",
    "course",
    "certificate_title",
    "grade_or_result",
    "issue_date",
}


def tamper_field(conn, certificate_id: str, field: str, new_value: str, recompute_hash: bool) -> None:
    if field not in ALLOWED_TAMPER_FIELDS:
        raise ValueError(f"Field '{field}' is not allowed to be tampered.")

    row = conn.execute(
        "SELECT * FROM certificates WHERE certificate_id = ?", (certificate_id,)
    ).fetchone()
    if row is None:
        raise LookupError(f"Certificate {certificate_id} not found.")

    backup = conn.execute(
        "SELECT certificate_id FROM demo_backups WHERE certificate_id = ?", (certificate_id,)
    ).fetchone()
    if backup is None:
        saved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        conn.execute(
            "INSERT INTO demo_backups (certificate_id, original_json, saved_at) VALUES (?, ?, ?)",
            (certificate_id, json.dumps(dict(row)), saved_at),
        )

    # Field name is strictly verified against ALLOWED_TAMPER_FIELDS allow-list
    sql = f"UPDATE certificates SET {field} = ? WHERE certificate_id = ?"
    conn.execute(sql, (new_value, certificate_id))

    if recompute_hash:
        updated_row = conn.execute(
            "SELECT * FROM certificates WHERE certificate_id = ?", (certificate_id,)
        ).fetchone()
        canonical = canonicalize(payload_from_row(updated_row))
        new_hash = sha256_hex(canonical)
        conn.execute(
            "UPDATE certificates SET payload_sha256 = ? WHERE certificate_id = ?",
            (new_hash, certificate_id),
        )

    audit.add_entry(
        conn,
        "DEMO_TAMPER",
        certificate_id,
        f"field={field} recompute_hash={recompute_hash}",
    )


def restore_original(conn, certificate_id: str) -> None:
    backup = conn.execute(
        "SELECT original_json FROM demo_backups WHERE certificate_id = ?", (certificate_id,)
    ).fetchone()
    if backup is None:
        raise LookupError(f"No backup exists for {certificate_id}")

    original = json.loads(backup["original_json"])
    conn.execute(
        """
        UPDATE certificates SET
            student_name = ?,
            student_roll_no = ?,
            program = ?,
            course = ?,
            certificate_title = ?,
            grade_or_result = ?,
            issuing_authority = ?,
            issue_date = ?,
            key_id = ?,
            payload_sha256 = ?,
            signature_b64 = ?,
            created_at = ?
        WHERE certificate_id = ?
        """,
        (
            original["student_name"],
            original["student_roll_no"],
            original["program"],
            original["course"],
            original["certificate_title"],
            original["grade_or_result"],
            original["issuing_authority"],
            original["issue_date"],
            original["key_id"],
            original["payload_sha256"],
            original["signature_b64"],
            original["created_at"],
            certificate_id,
        ),
    )
    conn.execute("DELETE FROM demo_backups WHERE certificate_id = ?", (certificate_id,))
    audit.add_entry(conn, "DEMO_TAMPER", certificate_id, "restored")
