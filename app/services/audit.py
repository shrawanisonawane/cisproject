import hashlib
from datetime import datetime, timezone

GENESIS = "0" * 64


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _entry_hash(prev_hash, ts, action, certificate_id, details) -> str:
    text = "|".join([prev_hash, ts, action, certificate_id or "", details])
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def add_entry(conn, action: str, certificate_id=None, details: str = "") -> None:
    row = conn.execute("SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
    prev_hash = row["entry_hash"] if row else GENESIS
    ts = _now()
    entry_hash = _entry_hash(prev_hash, ts, action, certificate_id, details)
    conn.execute(
        "INSERT INTO audit_log (ts, action, certificate_id, details, prev_hash, entry_hash) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (ts, action, certificate_id, details, prev_hash, entry_hash),
    )


def list_entries(conn):
    return conn.execute("SELECT * FROM audit_log ORDER BY id DESC").fetchall()


def verify_chain(conn):
    """Return (ok: bool, message: str). Detects edited or removed entries."""
    rows = conn.execute("SELECT * FROM audit_log ORDER BY id ASC").fetchall()
    prev = GENESIS
    for row in rows:
        if row["prev_hash"] != prev:
            return False, f"Chain broken at entry {row['id']} (previous hash mismatch)."
        expected = _entry_hash(row["prev_hash"], row["ts"], row["action"],
                               row["certificate_id"], row["details"])
        if expected != row["entry_hash"]:
            return False, f"Entry {row['id']} was modified."
        prev = row["entry_hash"]
    return True, f"Chain intact ({len(rows)} entries)."
