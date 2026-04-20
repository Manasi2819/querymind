"""
Encryption utilities using python cryptography Fernet module for DB URLs
"""
from cryptography.fernet import Fernet
from config import get_settings

settings = get_settings()

def get_fernet() -> Fernet:
    """Returns a Fernet instance configured with FERNET_KEY."""
    if not settings.fernet_key:
        raise ValueError("FERNET_KEY is not configured in environment variables.")
    return Fernet(settings.fernet_key.encode('utf-8'))

def encrypt_secret(plain_text: str) -> str:
    """Encrypts a plaintext secret using Fernet."""
    if not plain_text:
        return plain_text
    try:
        f = get_fernet()
        return f.encrypt(plain_text.encode('utf-8')).decode('utf-8')
    except Exception:
        return plain_text

def decrypt_secret(encrypted_text: str) -> str:
    """Decrypts an encrypted secret. Falls back to original text if decryption fails."""
    if not encrypted_text:
        return encrypted_text
    try:
        f = get_fernet()
        return f.decrypt(encrypted_text.encode('utf-8')).decode('utf-8')
    except Exception:
        # Fallback for plain-text legacy data or malformed strings
        return encrypted_text

# Backward-compatible aliases
encrypt_db_url = encrypt_secret
decrypt_db_url = decrypt_secret
