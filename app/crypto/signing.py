import base64
import hashlib

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

SALT_LENGTH = 32


def _pss():
    return padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=SALT_LENGTH)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sign_bytes(private_key, data: bytes) -> str:
    signature = private_key.sign(data, _pss(), hashes.SHA256())
    return base64.b64encode(signature).decode("ascii")


def verify_bytes(public_key, data: bytes, signature_b64: str) -> bool:
    try:
        signature = base64.b64decode(signature_b64, validate=True)
    except Exception:
        return False
    try:
        public_key.verify(signature, data, _pss(), hashes.SHA256())
        return True
    except InvalidSignature:
        return False
    except Exception:
        return False
