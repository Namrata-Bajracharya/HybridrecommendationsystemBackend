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


def send_invoice_email(
    to_email: str,
    order_number: str,
    contact_name: str,
    contact_phone: str,
    shipping_address: str | None,
    items: list[dict],
    subtotal: float,
    shipping_cost: float,
    tax: float,
    discount: float,
    total: float,
) -> None:
    subject = f"Invoice — Order #{order_number} — Kallee Nepal"
    rows = "".join(
        f"""<tr>
          <td style="padding:8px;border-bottom:1px solid #ddd;">{i['name']}</td>
          <td style="padding:8px;border-bottom:1px solid #ddd;text-align:center;">{i['quantity']}</td>
          <td style="padding:8px;border-bottom:1px solid #ddd;text-align:right;">${i['unit_price']:.2f}</td>
          <td style="padding:8px;border-bottom:1px solid #ddd;text-align:right;">${i['total']:.2f}</td>
        </tr>"""
        for i in items
    )
    html = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto; padding: 20px;">
  <div style="text-align:center;margin-bottom:30px;">
    <h1 style="color:#1a1a2e;margin:0;">KALLEE NEPAL</h1>
    <p style="color:#666;margin:4px 0;">Invoice</p>
  </div>
  <table style="width:100%;margin-bottom:20px;">
    <tr>
      <td style="width:50%;">
        <strong>Bill To:</strong><br>
        {contact_name}<br>
        {contact_phone}<br>
        {shipping_address or ''}
      </td>
      <td style="width:50%;text-align:right;">
        <strong>Order #:</strong> {order_number}<br>
      </td>
    </tr>
  </table>
  <table style="width:100%;border-collapse:collapse;margin-bottom:20px;">
    <thead>
      <tr style="background:#1a1a2e;color:#fff;">
        <th style="padding:10px;text-align:left;">Item</th>
        <th style="padding:10px;text-align:center;">Qty</th>
        <th style="padding:10px;text-align:right;">Price</th>
        <th style="padding:10px;text-align:right;">Total</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>
  <table style="width:100%;max-width:300px;margin-left:auto;">
    <tr><td style="padding:4px;">Subtotal</td><td style="padding:4px;text-align:right;">${subtotal:.2f}</td></tr>
    <tr><td style="padding:4px;">Shipping</td><td style="padding:4px;text-align:right;">${shipping_cost:.2f}</td></tr>
    <tr><td style="padding:4px;">Tax</td><td style="padding:4px;text-align:right;">${tax:.2f}</td></tr>"""
    if discount:
        html += f"""<tr><td style="padding:4px;">Discount</td><td style="padding:4px;text-align:right;">-${discount:.2f}</td></tr>"""
    html += f"""\
    <tr style="font-weight:bold;font-size:16px;">
      <td style="padding:6px;border-top:2px solid #1a1a2e;">Total</td>
      <td style="padding:6px;border-top:2px solid #1a1a2e;text-align:right;">${total:.2f}</td>
    </tr>
  </table>
  <p style="color:#999;font-size:12px;text-align:center;margin-top:30px;">Thank you for shopping with Kallee Nepal!</p>
</body>
</html>"""
    _send_email(to_email, subject, html)
