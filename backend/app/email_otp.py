"""Sends OTP codes via email. Tries Resend first (RESEND_API_KEY), then
falls back to Gmail SMTP (SMTP_USER/SMTP_APP_PASSWORD) if that's configured
instead. If neither is set, send_otp_email() returns False and the caller
falls back to "dev mode" (showing the code on the login screen instead of
emailing it) - same opt-in-with-graceful-fallback pattern as the Groq LLM
sentiment upgrade elsewhere in this app, so a missing/invalid/rate-limited
email account never locks anyone out of login.
"""
import logging
import os
import smtplib
from email.mime.text import MIMEText

import resend
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("email_otp")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "").strip()
RESEND_FROM = os.environ.get("RESEND_FROM", "MarketPulse <onboarding@resend.dev>").strip()

SMTP_USER = os.environ.get("SMTP_USER", "").strip()
SMTP_APP_PASSWORD = os.environ.get("SMTP_APP_PASSWORD", "").strip()
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587") or "587")

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY


def is_configured() -> bool:
    return bool(RESEND_API_KEY or (SMTP_USER and SMTP_APP_PASSWORD))


def _otp_html(code: str) -> str:
    return (
        f"<p>Your MarketPulse login code is <strong>{code}</strong>.</p>"
        f"<p>It expires in 2 minutes. If you didn't request this, you can ignore this email.</p>"
    )


def _send_via_resend(to_email: str, code: str) -> bool:
    try:
        resend.Emails.send({
            "from": RESEND_FROM,
            "to": to_email,
            "subject": f"{code} is your MarketPulse login code",
            "html": _otp_html(code),
        })
        return True
    except Exception:
        logger.exception("Resend send failed for %s", to_email)
        return False


def _send_via_smtp(to_email: str, code: str) -> bool:
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
        logger.exception("SMTP send failed for %s", to_email)
        return False


def send_otp_email(to_email: str, code: str) -> bool:
    if RESEND_API_KEY:
        return _send_via_resend(to_email, code)
    if SMTP_USER and SMTP_APP_PASSWORD:
        return _send_via_smtp(to_email, code)
    return False
