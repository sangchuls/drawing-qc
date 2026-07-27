"""Verifies the short-lived upload token issued by the Next.js app
(apps/web/lib/auth.ts). Must stay in sync with that implementation:
token = base64url(json({"exp": ...})) + "." + base64url(HMAC-SHA256(body)).
"""
import base64
import hashlib
import hmac
import json
import os
import time


def _b64url_decode(s: str) -> bytes:
    padded = s + "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(padded.encode())


def verify_upload_token(token: str) -> bool:
    secret = os.environ.get("UPLOAD_TOKEN_SECRET")
    if not secret:
        raise RuntimeError("UPLOAD_TOKEN_SECRET env var is not set")

    try:
        body_b64, sig_b64 = token.split(".")
    except ValueError:
        return False

    expected_sig = hmac.new(secret.encode(), body_b64.encode(), hashlib.sha256).digest()
    given_sig = _b64url_decode(sig_b64)
    if not hmac.compare_digest(expected_sig, given_sig):
        return False

    try:
        payload = json.loads(_b64url_decode(body_b64))
    except Exception:
        return False

    return time.time() <= payload.get("exp", 0)
