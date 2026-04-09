from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
import passlib.handlers.bcrypt
import bcrypt

# --- Robust Patch for passlib 1.7.4 + bcrypt 4.0.0+ Compatibility ---
# passlib's internal tests for "wrap bug" use passwords > 72 bytes.
# Modern bcrypt raises ValueError for passwords > 72 bytes.
# This patch truncates passwords at the bcrypt library level to fix the crash.

_original_hashpw = bcrypt.hashpw
def patched_hashpw(password, salt):
    if isinstance(password, str):
        password = password.encode('utf-8')
    if len(password) > 72:
        password = password[:72]
    return _original_hashpw(password, salt)
bcrypt.hashpw = patched_hashpw

_original_checkpw = bcrypt.checkpw
def patched_checkpw(password, hashed_password):
    if isinstance(password, str):
        password = password.encode('utf-8')
    if len(password) > 72:
        password = password[:72]
    return _original_checkpw(password, hashed_password)
bcrypt.checkpw = patched_checkpw

# Ensure bcrypt has __about__ for passlib compatibility
if not hasattr(bcrypt, "__about__"):
    class Dummy: __version__ = bcrypt.__version__
    bcrypt.__about__ = Dummy()
# --------------------------------------------------------------------

from config import get_settings

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/admin/token")

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def verify_token(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        # payload will contain {"sub": username, "user_id": 1}
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
