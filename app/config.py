import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent


def _bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    app_name: str = os.getenv("APP_NAME", "Sanjivani University Certificate Registry")
    issuing_authority: str = os.getenv("ISSUING_AUTHORITY", "Sanjivani University")
    id_prefix: str = os.getenv("ID_PREFIX", "SU")
    base_url: str = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    demo_mode: bool = _bool(os.getenv("DEMO_MODE", "true"))
    db_path: Path = ROOT / os.getenv("DB_PATH", "data/certificates.db")
    key_dir: Path = ROOT / os.getenv("KEY_DIR", "keys")
    key_passphrase: str = os.getenv("ISSUER_KEY_PASSPHRASE", "")
    max_upload_bytes: int = 256 * 1024


settings = Settings()
