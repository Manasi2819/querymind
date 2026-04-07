import sys
import os

# Mock the password hash check
try:
    from auth import verify_password, get_password_hash
    print("Successfully imported auth functions")
except Exception as e:
    print(f"Failed to import auth functions: {e}")
    sys.exit(1)

# Test with a long password (73 bytes)
long_pwd = "a" * 73
print(f"Testing with password length: {len(long_pwd)}")

try:
    # This should trigger initialization of pwd_context
    # and perform the wrap bug check.
    hashed = get_password_hash(long_pwd)
    print("Successfully hashed a 73-byte password!")
    
    # Verify it
    is_valid = verify_password(long_pwd, hashed)
    print(f"Verification result: {is_valid}")
    
    if is_valid:
        print("\nSUCCESS: The bcrypt limitation has been bypassed successfully!")
    else:
        print("\nFAILURE: Verification failed.")
except Exception as e:
    print(f"CRITICAL: System still crashing: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
