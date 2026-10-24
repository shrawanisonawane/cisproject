import re
from datetime import datetime, timezone
from pydantic import BaseModel, field_validator

from app.config import settings
from app.crypto import keys as keylib
from app.crypto.canonical import SCHEMA_VERSION, canonicalize
from app.crypto.signing import sha256_hex, sign_bytes
from app.services import audit
from app.services.ids import new_certificate_id
from app.services.verification import payload_from_row


def _clean_str(v: str, name: str, min_len: int, max_len: int) -> str:
    if not isinstance(v, str):
        raise ValueError(f"{name} must be a string")
    v = v.strip()
    if any(ord(c) < 32 for c in v):
        raise ValueError(f"{name} cannot contain control characters")
    if len(v) < min_len or len(v) > max_len:
        raise ValueError(f"{name} length must be between {min_len} and {max_len} characters")
    return v


class CertificateIn(BaseModel):
    student_name: str
    student_roll_no: str
    program: str
    course: str
    certificate_title: str
    grade_or_result: str = ""
    issue_date: str

    @field_validator("student_name")
    @classmethod
    def val_student_name(cls, v: str) -> str:
        return _clean_str(v, "student_name", 1, 100)

    @field_validator("student_roll_no")
    @classmethod
    def val_student_roll_no(cls, v: str) -> str:
        return _clean_str(v, "student_roll_no", 1, 40)

    @field_validator("program")
    @classmethod
    def val_program(cls, v: str) -> str:
        return _clean_str(v, "program", 1, 120)

    @field_validator("course")
    @classmethod
    def val_course(cls, v: str) -> str:
        return _clean_str(v, "course", 1, 120)

    @field_validator("certificate_title")
    @classmethod
    def val_certificate_title(cls, v: str) -> str:
        return _clean_str(v, "certificate_title", 1, 120)

    @field_validator("grade_or_result")
    @classmethod
    def val_grade_or_result(cls, v: str) -> str:
        return _clean_str(v, "grade_or_result", 0, 60)

    @field_validator("issue_date")
    @classmethod
    def val_issue_date(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("issue_date must match YYYY-MM-DD format")
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("issue_date must be a valid calendar date")
        return v


def issue_certificate(conn, data: CertificateIn, private_key, public_key) -> dict:
    while True:
        certificate_id = new_certificate_id()
        existing = conn.execute(
            "SELECT 1 FROM certificates WHERE certificate_id = ?", (certificate_id,)
        ).fetchone()
        if not existing:
            break

    kid = keylib.key_id(public_key)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "certificate_id": certificate_id,
        "student_name": data.student_name,
        "student_roll_no": data.student_roll_no,
        "program": data.program,
        "course": data.course,
        "certificate_title": data.certificate_title,
        "grade_or_result": data.grade_or_result,
        "issuing_authority": settings.issuing_authority,
        "issue_date": data.issue_date,
        "key_id": kid,
    }

    canonical = canonicalize(payload)
    payload_sha256 = sha256_hex(canonical)
    signature_b64 = sign_bytes(private_key, canonical)
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    conn.execute(
        """
        INSERT INTO certificates (
            certificate_id, student_name, student_roll_no, program, course,
            certificate_title, grade_or_result, issuing_authority, issue_date,
            key_id, payload_sha256, signature_b64, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            certificate_id,
            data.student_name,
            data.student_roll_no,
            data.program,
            data.course,
            data.certificate_title,
            data.grade_or_result,
            settings.issuing_authority,
            data.issue_date,
            kid,
            payload_sha256,
            signature_b64,
            created_at,
        ),
    )

    audit.add_entry(conn, "ISSUED", certificate_id, f"student={data.student_roll_no}")
    row = conn.execute(
        "SELECT * FROM certificates WHERE certificate_id = ?", (certificate_id,)
    ).fetchone()
    return dict(row)


def build_bundle(row) -> dict:
    return {
        "format": "meridian-certificate-bundle",
        "version": 1,
        "payload": payload_from_row(row),
        "signature_b64": row["signature_b64"],
        "payload_sha256": row["payload_sha256"],
    }


def list_certificates(conn, q=None, status="all", program=None, sort="issue_date_desc"):
    sql = """
        SELECT c.*, (r.certificate_id IS NOT NULL) AS is_revoked, r.revoked_at, r.reason AS revocation_reason
        FROM certificates c
        LEFT JOIN revocations r ON c.certificate_id = r.certificate_id
    """
    conditions = []
    params = []

    if q and q.strip():
        term = f"%{q.strip()}%"
        conditions.append("(c.student_name LIKE ? OR c.student_roll_no LIKE ? OR c.certificate_id LIKE ?)")
        params.extend([term, term, term])

    if program and program.strip():
        conditions.append("c.program = ?")
        params.append(program.strip())

    if status == "active":
        conditions.append("r.certificate_id IS NULL")
    elif status == "revoked":
        conditions.append("r.certificate_id IS NOT NULL")

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    if sort == "issue_date_asc":
        sql += " ORDER BY c.issue_date ASC, c.created_at ASC"
    elif sort == "name_asc":
        sql += " ORDER BY c.student_name ASC, c.issue_date DESC"
    else:
        sql += " ORDER BY c.issue_date DESC, c.created_at DESC"

    rows = conn.execute(sql, params).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d["revoked"] = bool(r["is_revoked"])
        results.append(d)
    return results
