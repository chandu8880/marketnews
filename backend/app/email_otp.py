"""Sends OTP codes via email (SMTP - Gmail by default) when SMTP_USER and
SMTP_APP_PASSWORD are configured. Otherwise send_otp_email() returns False
and the caller falls back to dev-mode (showing the code on the login
screen instead of emailing it) - same opt-in-with-graceful-fallback
pattern as the Groq LLM sentiment upgrade elsewhere in this app, so a
missing/invalid/rate-limited SMTP account never locks anyone out of login.
"""
import logging
import os
import smtplib
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("email_otp")

SMTP_USER = os.environ.get("SMTP_USER", "").strip()
SMTP_APP_PASSWORD = os.environ.get("SMTP_APP_PASSWORD", "").strip()
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587") or "587")


def is_configured() -> bool:
    return bool(SMTP_USER and SMTP_APP_PASSWORD)


def send_otp_email(to_email: str, code: str) -> bool:
    if not is_configured():
        return False
    try:
        msg = MIMEText(
            f"Your MarketPulse login code is {code}.\n\nIt expires in 2 minutes. "
            f"If you didn't request this, you can ignore this email."
        )
        msg["Subject"] = f"{code} is your MarketPulse login code"
        msg["From"] = SMTP_USER
        msg["To"] = to_email

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_APP_PASSWORD)
            server.sendmail(SMTP_USER, [to_email], msg.as_string())
        return True
    except Exception:
        logger.exception("Failed to send OTP email to %s", to_email)
        return False
