import json
import unicodedata

SCHEMA_VERSION = "1"

SIGNED_FIELDS = (
    "schema_version",
    "certificate_id",
    "student_name",
    "student_roll_no",
    "program",
    "course",
    "certificate_title",
    "grade_or_result",
    "issuing_authority",
    "issue_date",
    "key_id",
)


class CanonicalizationError(ValueError):
    pass


def _clean(value):
    if not isinstance(value, str):
        raise CanonicalizationError("All signed fields must be text.")
    return unicodedata.normalize("NFC", value).strip()


def canonicalize(payload: dict) -> bytes:
    """Return the exact bytes that are hashed and signed."""
    if not isinstance(payload, dict):
        raise CanonicalizationError("Payload must be an object.")
    expected = set(SIGNED_FIELDS)
    given = set(payload.keys())
    missing = expected - given
    extra = given - expected
    if missing:
        raise CanonicalizationError("Missing fields: " + ", ".join(sorted(missing)))
    if extra:
        raise CanonicalizationError("Unexpected fields: " + ", ".join(sorted(extra)))
    cleaned = {name: _clean(payload[name]) for name in SIGNED_FIELDS}
    return json.dumps(
        cleaned, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
