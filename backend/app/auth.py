"""Single-user email + OTP login.

This app has no user database or multi-tenant concept - it's a personal
local app gated to one email address. If SMTP_USER/SMTP_APP_PASSWORD are
configured (see email_otp.py), the code is actually emailed; otherwise it
falls back to "dev mode" - returned straight to the frontend, which shows
it on the login screen instead. The expiry/validation logic is identical
either way, so a missing/misconfigured/rate-limited mailbox never locks
anyone out of login.
"""
import logging
import random
import secrets
import threading
from datetime import datetime, timedelta, timezone

from .email_otp import send_otp_email

logger = logging.getLogger("auth")

ALLOWED_EMAIL = "luciferchandu8880@gmail.com"
OTP_TTL_SECONDS = 120
# Server-side backstop only - the cookie itself is a browser-session cookie
# (no Max-Age), so in practice it disappears when the browser/tab closes.
# This just caps how long a still-open tab's session stays valid.
SESSION_TTL_HOURS = 12

_lock = threading.Lock()
_otps = {}      # email -> {"code": str, "expires_at": datetime}
_sessions = {}  # token -> {"email": str, "expires_at": datetime}


def _now():
    return datetime.now(timezone.utc)


def _normalize(email: str) -> str:
    return (email or "").strip().lower()


def request_otp(email: str):
    normalized = _normalize(email)
    if normalized != ALLOWED_EMAIL:
        return {"ok": False, "error": "This app is only set up for one email address."}

    code = f"{random.randint(0, 999999):06d}"
    expires_at = _now() + timedelta(seconds=OTP_TTL_SECONDS)
    with _lock:
        _otps[normalized] = {"code": code, "expires_at": expires_at}

    emailed = send_otp_email(normalized, code)
    logger.info("OTP generated for %s (emailed=%s)", normalized, emailed)

    if emailed:
        return {"ok": True, "dev_otp": None, "expires_in_seconds": OTP_TTL_SECONDS, "emailed": True}
    return {"ok": True, "dev_otp": code, "expires_in_seconds": OTP_TTL_SECONDS, "emailed": False}


def verify_otp(email: str, code: str):
    normalized = _normalize(email)
    code = (code or "").strip()

    with _lock:
        entry = _otps.get(normalized)
        if not entry:
            return {"ok": False, "error": "No OTP requested for this email yet."}
        if _now() > entry["expires_at"]:
            del _otps[normalized]
            return {"ok": False, "error": "OTP expired. Request a new one."}
        if entry["code"] != code:
            return {"ok": False, "error": "Incorrect OTP."}

        del _otps[normalized]
        token = secrets.token_urlsafe(32)
        _sessions[token] = {"email": normalized, "expires_at": _now() + timedelta(hours=SESSION_TTL_HOURS)}

    return {"ok": True, "token": token}


def validate_session(token: str):
    if not token:
        return None
    with _lock:
        entry = _sessions.get(token)
        if not entry:
            return None
        if _now() > entry["expires_at"]:
            del _sessions[token]
            return None
        return entry["email"]


def logout(token: str):
    with _lock:
        _sessions.pop(token, None)
