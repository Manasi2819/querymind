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

def encrypt_db_url(url: str) -> str:
    """Encrypts a plaintext database URL."""
    if not url:
        return url
    f = get_fernet()
    return f.encrypt(url.encode('utf-8')).decode('utf-8')

def decrypt_db_url(encrypted: str) -> str:
    """Decrypts an encrypted database URL."""
    if not encrypted:
        return encrypted
    try:
        f = get_fernet()
        return f.decrypt(encrypted.encode('utf-8')).decode('utf-8')
    except Exception:
        return encrypted
