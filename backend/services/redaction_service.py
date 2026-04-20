import re

# Common patterns for sensitive information
PATTERNS = {
    # OpenAI and other sk-... style keys
    "api_key": r"sk-[a-zA-Z0-9]{32,}", 
    # Generic high-entropy keys or passwords (heuristic)
    "generic_key": r"(?:key|password|secret|token|apikey)[\s:=]+([a-zA-Z0-9_\-\.\~]{16,})",
    # Connection URLs (blocking components like password)
    "db_url": r"(?:mysql|postgresql|sqlite|mssql|oracle|redis|mongodb)://[^:]+:([^@]+)@",
}

def redact_secrets(text: str) -> str:
    """
    Scans text for sensitive patterns and replaces them with [REDACTED].
    """
    if not text:
        return text
        
    redacted = text
    
    # 1. Redact explicit API key patterns
    redacted = re.sub(PATTERNS["api_key"], "[REDACTED_API_KEY]", redacted)
    
    # 2. Redact DB connection passwords in URLs
    # This specifically targets the section between : and @ in a URL
    def redact_url_pass(match):
        full_match = match.group(0)
        password = match.group(1)
        return full_match.replace(password, "********")
        
    redacted = re.sub(PATTERNS["db_url"], redact_url_pass, redacted)
    
    # 3. Redact common field=value patterns
    # We use a positive lookbehind/lookahead to only redact the value part
    def redact_generic(match):
        full_match = match.group(0)
        secret_value = match.group(1)
        return full_match.replace(secret_value, "********")
        
    redacted = re.sub(PATTERNS["generic_key"], redact_generic, redacted, flags=re.IGNORECASE)
    
    # 4. Final check for common cloud provider key prefixes if missed
    # Groq: gsk_...
    redacted = re.sub(r"gsk_[a-zA-Z0-9]{32,}", "[REDACTED_GROQ_KEY]", redacted)
    
    return redacted
