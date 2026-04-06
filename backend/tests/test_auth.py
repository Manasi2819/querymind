import pytest
from datetime import datetime, timedelta
from jose import jwt, JWTError
from auth import create_access_token, verify_token
from config import get_settings

settings = get_settings()

def test_create_access_token():
    data = {"sub": "admin"}
    token = create_access_token(data)
    
    # decode to veriy
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    assert payload.get("sub") == "admin"
    assert "exp" in payload

def test_verify_token_valid():
    token = create_access_token({"sub": "test_user"})
    payload = verify_token(token)
    assert payload.get("sub") == "test_user"

# Additional testing could include mocked expiration, but standard JWT logic behaves predictably.
