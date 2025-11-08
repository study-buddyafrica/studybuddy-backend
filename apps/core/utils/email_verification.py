import random
from apps.core.models import EmailVerificationCode
from apps.core.utils.send_email import send_email  

def send_verification_email(user):
    """Generate a 6-digit code, save it, and send it using your email utility."""
    code = str(random.randint(100000, 999999))

    EmailVerificationCode.objects.create(user=user, code=code)

    subject = "Verify Your StudyBuddy Email"
    context = {"user": user, "code": code}

    send_email(
        to_email=user.email,
        subject=subject,
        context=context,
       text_body = f"Your verification code is **{code}** (expires in 2 minutes)."
    )
    
    return code
