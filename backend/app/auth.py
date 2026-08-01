"""Single-user email + OTP login - fully stateless (no server-side session
or OTP storage), because Vercel runs this app across multiple isolated
serverless containers with separate memory. An in-memory dict here would
only be visible to whichever container happened to handle a given
request; the next request (even seconds later, and regardless of device)
can land on a different container that never saw it, producing false
"not authenticated" / "incorrect OTP" errors. Both the OTP and the session
token are instead derived cryptographically (HMAC-SHA256) from a shared
AUTH_SECRET, so any container can independently verify either one without
needing to remember anything.

If SMTP_USER/SMTP_APP_PASSWORD or RESEND_API_KEY are configured (see
email_otp.py), the OTP is actually emailed; otherwise it falls back to
"dev mode" - returned straight to the frontend, which shows it on the
login screen instead. A missing/misconfigured/rate-limited mailbox never
locks anyone out of login either way.
"""
import base64
import hashlib
import hmac
import logging
import os
import time

from dotenv import load_dotenv

from .email_otp import send_otp_email

load_dotenv()

logger = logging.getLogger("auth")

ALLOWED_EMAIL = "luciferchandu8880@gmail.com"
OTP_TTL_SECONDS = 120
OTP_WINDOW_SECONDS = 60  # bucket size for the deterministic OTP - see _otp_for_window
SESSION_TTL_HOURS = 12

AUTH_SECRET = os.environ.get("AUTH_SECRET", "").strip()
if not AUTH_SECRET:
    # A FIXED secret shared across every instance is required for stateless
    # verification to work at all - a per-process random fallback would
    # reintroduce the exact bug this module exists to avoid. This fallback
    # is only safe because it's for solo local dev; AUTH_SECRET must be set
    # in the deployed environment (see backend/.env.example).
    AUTH_SECRET = "insecure-local-dev-secret-change-me"
    logger.warning("AUTH_SECRET not set - using an insecure local-dev-only fallback")

_SECRET_BYTES = AUTH_SECRET.encode()


def _normalize(email: str) -> str:
    return (email or "").strip().lower()


def _sign(*parts: str) -> str:
    msg = "|".join(parts).encode()
    return hmac.new(_SECRET_BYTES, msg, hashlib.sha256).hexdigest()


# ---- OTP: deterministic (TOTP-style), so no server-side storage is needed ----

def _otp_for_window(email: str, window: int) -> str:
    digest = _sign(email, str(window))
    num = int(digest[:8], 16) % 1_000_000
    return f"{num:06d}"


def request_otp(email: str):
    normalized = _normalize(email)
    if normalized != ALLOWED_EMAIL:
        return {"ok": False, "error": "This app is only set up for one email address."}

    window = int(time.time() // OTP_WINDOW_SECONDS)
    code = _otp_for_window(normalized, window)

    emailed = send_otp_email(normalized, code)
    logger.info("OTP generated for %s (emailed=%s)", normalized, emailed)

    if emailed:
        return {"ok": True, "dev_otp": None, "expires_in_seconds": OTP_TTL_SECONDS, "emailed": True}
    return {"ok": True, "dev_otp": code, "expires_in_seconds": OTP_TTL_SECONDS, "emailed": False}


def verify_otp(email: str, code: str):
    normalized = _normalize(email)
    code = (code or "").strip()
    if normalized != ALLOWED_EMAIL or not code:
        return {"ok": False, "error": "Incorrect OTP."}

    now_window = int(time.time() // OTP_WINDOW_SECONDS)
    # Current + previous window so a code doesn't die right at a bucket
    # boundary - gives ~60-120s validity, matching OTP_TTL_SECONDS.
    valid = {_otp_for_window(normalized, now_window), _otp_for_window(normalized, now_window - 1)}
    if not any(hmac.compare_digest(code, v) for v in valid):
        return {"ok": False, "error": "Incorrect OTP or it expired. Request a new one."}

    return {"ok": True, "token": _create_session_token(normalized)}


# ---- Session: signed, stateless token - no server-side storage needed ----

def _create_session_token(email: str) -> str:
    expires_at = int(time.time()) + SESSION_TTL_HOURS * 3600
    payload = f"{email}|{expires_at}"
    sig = _sign(payload)
    raw = f"{payload}|{sig}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def validate_session(token: str):
    if not token:
        return None
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        email, expires_at, sig = raw.rsplit("|", 2)
    except Exception:
        return None

    if not hmac.compare_digest(sig, _sign(f"{email}|{expires_at}")):
        return None
    if int(expires_at) < time.time():
        return None
    return email


def logout(token: str):
    # Nothing to erase server-side (there's no server-side session store) -
    # main.py's logout endpoint clears the cookie client-side, which is
    # what actually ends the session in practice.
    pass
