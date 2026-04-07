import bcrypt
import sys

print(f"Bcrypt version: {getattr(bcrypt, '__version__', 'unknown')}")
pwd = b'a' * 73
print(f"Testing password length: {len(pwd)}")

try:
    hashed = bcrypt.hashpw(pwd, bcrypt.gensalt())
    print("Success: hashpw worked with 73 bytes")
except Exception as e:
    print(f"Caught exception in hashpw: {type(e).__name__}: {e}")

try:
    # Test passlib's specific pattern: ident 2a
    # This matches the IDENT_2A in passlib/handlers/bcrypt.py
    # $2a$04$......................
    salt = b"$2a$04$2222222222222222222222"
    hashed = bcrypt.hashpw(pwd, salt)
    print("Success: hashpw worked with ident 2a and 73 bytes")
except Exception as e:
    print(f"Caught exception with ident 2a: {type(e).__name__}: {e}")
