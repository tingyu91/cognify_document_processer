import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.config import settings

_NONCE_SIZE = 12  # bytes — GCM standard


def _get_key() -> bytes:
    return base64.b64decode(settings.encryption_key)


def encrypt(plaintext: str) -> str:
    """Encrypt a string. Returns base64(nonce + ciphertext+tag)."""
    key = _get_key()
    nonce = os.urandom(_NONCE_SIZE)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ciphertext).decode()


def decrypt(token: str) -> str:
    """Decrypt a token produced by encrypt()."""
    key = _get_key()
    raw = base64.b64decode(token)
    nonce, ciphertext = raw[:_NONCE_SIZE], raw[_NONCE_SIZE:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None).decode()


def generate_key() -> str:
    """Generate a new base64-encoded 256-bit key. Run once, store in Railway env vars."""
    return base64.b64encode(os.urandom(32)).decode()
