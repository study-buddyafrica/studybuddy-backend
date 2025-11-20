from apps.core.utils.send_email import send_email  
 
def send_verification_email_to_address(email: str, code: str):
    subject = "Verify Your StudyBuddy Email"
    text_body = f"Your verification code is {code}. It expires in 2 minutes."
    html_body = f"<p>Your verification code is <strong>{code}</strong>. It expires in 2 minutes.</p>"

    send_email(
        to_email=email,
        subject=subject,
        context={"code": code, "email": email},
        text_body=text_body,
        html_body=html_body,
    )


