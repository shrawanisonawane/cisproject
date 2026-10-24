import sqlite3
from contextlib import contextmanager
from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS certificates (
    certificate_id   TEXT PRIMARY KEY,
    student_name     TEXT NOT NULL,
    student_roll_no  TEXT NOT NULL,
    program          TEXT NOT NULL,
    course           TEXT NOT NULL,
    certificate_title TEXT NOT NULL,
    grade_or_result  TEXT NOT NULL DEFAULT '',
    issuing_authority TEXT NOT NULL,
    issue_date       TEXT NOT NULL,
    key_id           TEXT NOT NULL,
    payload_sha256   TEXT NOT NULL,
    signature_b64    TEXT NOT NULL,
    created_at       TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS revocations (
    certificate_id TEXT PRIMARY KEY REFERENCES certificates(certificate_id),
    revoked_at     TEXT NOT NULL,
    reason         TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    ts             TEXT NOT NULL,
    action         TEXT NOT NULL,
    certificate_id TEXT,
    details        TEXT NOT NULL DEFAULT '',
    prev_hash      TEXT NOT NULL,
    entry_hash     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS verification_log (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    ts             TEXT NOT NULL,
    certificate_id TEXT,
    method         TEXT NOT NULL,
    result         TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS demo_backups (
    certificate_id TEXT PRIMARY KEY,
    original_json  TEXT NOT NULL,
    saved_at       TEXT NOT NULL
);
"""


def get_conn() -> sqlite3.Connection:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
