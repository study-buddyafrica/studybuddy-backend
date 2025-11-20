from apps.core.utils.send_email import send_email

def send_password_reset_code(email: str, code: str):
    subject = "Reset Your StudyBuddy Password"
    text_body = f"Your password reset code is {code}. It expires in 5 minutes."
    html_body = f"<p>Your password reset code is <strong>{code}</strong>. It expires in 10 minutes.</p>"

    send_email(
        to_email=email,
        subject=subject,
        context={"code": code, "email": email},
        text_body=text_body,
        html_body=html_body,
    )
