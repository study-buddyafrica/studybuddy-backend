import random
from datetime import timedelta
from django.utils import timezone
from apps.core.utils.send_email import send_email
from apps.core.utils.redis_client import r

def generate_verification_code(length=6):
    """Generate a 6 digit random verification code"""
    return str(random.randint(10**(length-1), 10**length-1))

def create_verification_record(email):
    """ 
    Generate a code, store in redis that expires in 2 minutes
    and send to the user's email.
    """
    code = generate_verification_code()
    key = f"verify:{email}"
    ttl = 120 

    # store code with TTL - Django/redis-py uses seconds directly
    r.setex(key, ttl, code)  # Changed from timedelta(seconds=ttl) to just ttl

    # send email
    subject = "Email Verification"
    text_body = f"Your verification code is: {code} (valid for 2 minutes)"
    html_body = f"<h3> Verification code:</h3><h2>{code}</h2><p>Expires in 2 minutes.</p>"

    send_email(
        to_email=email,
        subject=subject, 
        text_body=text_body,
        html_body=html_body
    )

    return code