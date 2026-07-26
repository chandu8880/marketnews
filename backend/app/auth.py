"""Single-user phone + OTP login.

This app has no user database or multi-tenant concept - it's a personal
local app gated to one phone number. OTP delivery runs in "dev mode": no
SMS provider is configured, so the code is returned straight to the
frontend (which shows it on the login screen) instead of being texted.
The expiry/validation logic is real either way, so swapping in a real SMS
provider later only means changing how the code leaves this module, not
how it's generated or checked.
"""
import logging
import random
import re
import secrets
import threading
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("auth")

ALLOWED_PHONE = "9182813062"
OTP_TTL_SECONDS = 120
# Server-side backstop only - the cookie itself is a browser-session cookie
# (no Max-Age), so in practice it disappears when the browser/tab closes.
# This just caps how long a still-open tab's session stays valid.
SESSION_TTL_HOURS = 12

_lock = threading.Lock()
_otps = {}      # phone -> {"code": str, "expires_at": datetime}
_sessions = {}  # token -> {"phone": str, "expires_at": datetime}


def _now():
    return datetime.now(timezone.utc)


def _normalize(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    return digits[-10:]  # last 10 digits, so +91 91828 13062 and 9182813062 match


def request_otp(phone: str):
    normalized = _normalize(phone)
    if normalized != ALLOWED_PHONE:
        return {"ok": False, "error": "This app is only set up for one phone number."}

    code = f"{random.randint(0, 999999):06d}"
    expires_at = _now() + timedelta(seconds=OTP_TTL_SECONDS)
    with _lock:
        _otps[normalized] = {"code": code, "expires_at": expires_at}

    logger.info("OTP generated for %s (dev mode - not sent via real SMS)", normalized)
    return {"ok": True, "dev_otp": code, "expires_in_seconds": OTP_TTL_SECONDS}


def verify_otp(phone: str, code: str):
    normalized = _normalize(phone)
    code = (code or "").strip()

    with _lock:
        entry = _otps.get(normalized)
        if not entry:
            return {"ok": False, "error": "No OTP requested for this number yet."}
        if _now() > entry["expires_at"]:
            del _otps[normalized]
            return {"ok": False, "error": "OTP expired. Request a new one."}
        if entry["code"] != code:
            return {"ok": False, "error": "Incorrect OTP."}

        del _otps[normalized]
        token = secrets.token_urlsafe(32)
        _sessions[token] = {"phone": normalized, "expires_at": _now() + timedelta(hours=SESSION_TTL_HOURS)}

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
        return entry["phone"]


def logout(token: str):
    with _lock:
        _sessions.pop(token, None)
