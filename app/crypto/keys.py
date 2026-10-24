import hashlib
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

PRIVATE_NAME = "issuer_private.pem"
PUBLIC_NAME = "issuer_public.pem"


def generate_keypair(key_dir: Path, passphrase: str = "", force: bool = False) -> None:
    key_dir = Path(key_dir)
    key_dir.mkdir(parents=True, exist_ok=True)
    priv_path = key_dir / PRIVATE_NAME
    pub_path = key_dir / PUBLIC_NAME
    if (priv_path.exists() or pub_path.exists()) and not force:
        raise FileExistsError("Keys already exist. Use --force to overwrite.")
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    if passphrase:
        enc = serialization.BestAvailableEncryption(passphrase.encode("utf-8"))
    else:
        enc = serialization.NoEncryption()
    priv_path.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            enc,
        )
    )
    try:
        os.chmod(priv_path, 0o600)
    except OSError:
        pass
    pub_path.write_bytes(
        private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )


def load_private_key(key_dir: Path, passphrase: str = ""):
    data = (Path(key_dir) / PRIVATE_NAME).read_bytes()
    pw = passphrase.encode("utf-8") if passphrase else None
    return serialization.load_pem_private_key(data, password=pw)


def load_public_key(key_dir: Path):
    data = (Path(key_dir) / PUBLIC_NAME).read_bytes()
    return serialization.load_pem_public_key(data)


def public_key_pem(public_key) -> str:
    return public_key.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")


def fingerprint_hex(public_key) -> str:
    der = public_key.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(der).hexdigest()


def fingerprint_colon(public_key) -> str:
    h = fingerprint_hex(public_key)
    return ":".join(h[i : i + 2] for i in range(0, len(h), 2))


def key_id(public_key) -> str:
    return fingerprint_hex(public_key)[:16]
