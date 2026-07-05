import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

logger = logging.getLogger(__name__)


def _send_email(to_email: str, subject: str, html: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_USER
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        logger.info(f"Email sent to {to_email}: {subject}")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        raise RuntimeError(f"Unable to send email: {e}")


def send_verification_email(to_email: str, token: str) -> None:
    verify_url = f"{settings.VERIFICATION_BASE_URL}/verify?token={token}"
    subject = "Verify your Kallee Nepal account"

    html = f"""\
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
  <h2>Welcome to Kallee Nepal!</h2>
  <p>Thank you for registering. Please verify your email address by clicking the link below:</p>
  <p><a href="{verify_url}" style="display: inline-block; padding: 12px 24px; background: #1a1a2e; color: #fff; text-decoration: none; border-radius: 8px;">Verify Email</a></p>
  <p>Or copy and paste this link in your browser:</p>
  <p style="color: #666;">{verify_url}</p>
  <p>If you did not create an account, please ignore this email.</p>
</body>
</html>"""

    _send_email(to_email, subject, html)


def send_password_reset_email(to_email: str, token: str) -> None:
    reset_url = f"{settings.VERIFICATION_BASE_URL}/reset-password?token={token}"
    subject = "Reset your Kallee Nepal password"

    html = f"""\
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
  <h2>Password Reset Request</h2>
  <p>We received a request to reset your password. Click the link below to set a new password:</p>
  <p><a href="{reset_url}" style="display: inline-block; padding: 12px 24px; background: #1a1a2e; color: #fff; text-decoration: none; border-radius: 8px;">Reset Password</a></p>
  <p>Or copy and paste this link in your browser:</p>
  <p style="color: #666;">{reset_url}</p>
  <p>If you did not request this, please ignore this email.</p>
</body>
</html>"""

    _send_email(to_email, subject, html)


def send_order_status_email(to_email: str, subject: str, heading: str, body_lines: list[str]) -> None:
    lines_html = "".join(f"<p>{line}</p>" for line in body_lines)
    html = f"""\
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
  <h2>{heading}</h2>
  {lines_html}
  <p style="color: #999; font-size: 12px;">Kallee Nepal</p>
</body>
</html>"""
    _send_email(to_email, subject, html)
