import secrets
from datetime import datetime, timezone

from app.config import settings

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford base32


def new_certificate_id() -> str:
    year = datetime.now(timezone.utc).year
    suffix = "".join(secrets.choice(ALPHABET) for _ in range(8))
    return f"{settings.id_prefix}-{year}-{suffix}"
