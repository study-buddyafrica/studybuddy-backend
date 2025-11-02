import random
from datetime import timedelta
from django.core.cache import cache
from django.utils import timezone
from apps.core import send_email

def generate_verification_code(length: int = 6) -> str:
    """
    Generate a secure numeric verification code of given length.
    Default: 6 digits.
    """
    return str(random.randint(10 ** (length - 1), 10 ** length - 1))

def _get_cache_key(email: str) -> str:
    """Build the Redis key for a user's verification code."""
    return f"verify:{email}"

def _get_rate_limit_key(email: str) -> str:
    """Build the Redis key for rate-limiting per user."""
    return f"verify_limit:{email}"

def create_verification_record(email: str, ttl_seconds: int = 120, rate_limit_seconds: int = 60) -> str:
    """
    Generate and send a verification code, store in Redis with TTL.
    Enforce rate limiting to avoid spamming resend requests.
    """
    if not email:
        raise ValueError("Email address is required to generate a verification record.")

    rate_limit_key = _get_rate_limit_key(email)
    if cache.get(rate_limit_key):
        raise Exception("You must wait before requesting another verification code.")

    code = generate_verification_code()
    cache_key = _get_cache_key(email)

    cache.set(cache_key, code, timeout=ttl_seconds)

    cache.set(rate_limit_key, True, timeout=rate_limit_seconds)

    subject = "Email Verification"
    text_body = f"Your verification code is: {code} (valid for {ttl_seconds // 60} minutes)"
    html_body = f"""
        <div style="font-family: Arial, sans-serif;">
            <h3>Email Verification</h3>
            <p>Your verification code is:</p>
            <h2 style="color:#2E86C1;">{code}</h2>
            <p>This code will expire in {ttl_seconds // 60} minutes.</p>
        </div>
    """

    send_email(
        to_email=email,
        subject=subject,
        text_body=text_body,
        html_body=html_body
    )

    return code

def verify_code(email: str, code: str) -> bool:
    """
    Verify a code against what is stored in Redis.
    Returns True if valid and deletes the record after success.
    """
    if not email or not code:
        return False

    cache_key = _get_cache_key(email)
    stored_code = cache.get(cache_key)

    if stored_code and stored_code == code:
        cache.delete(cache_key)
        return True
    return False
