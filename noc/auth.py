from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time

from noc import config


SESSION_COOKIE = "noc_session"
CSRF_COOKIE = "noc_csrf"
PASSWORD_ITERATIONS = 600_000
ROLE_LEVEL = {"viewer": 1, "operator": 2, "admin": 3, "global_admin": 4}


def password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, rounds, salt, expected = encoded.split("$", 3)
        iterations = int(rounds)
        if scheme != "pbkdf2_sha256" or not 100_000 <= iterations <= 1_000_000:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), base64.urlsafe_b64decode(salt), iterations)
        return hmac.compare_digest(base64.urlsafe_b64encode(actual).decode(), expected)
    except (ValueError, TypeError):
        return False


def dummy_password_check(password: str) -> None:
    hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), b"noc-monitor-dummy-salt", PASSWORD_ITERATIONS)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def user_for_session(db, token: str | None) -> dict | None:
    if not token:
        return None
    rows = await db.query(
        "SELECT u.id,u.username,u.role,u.is_active,s.csrf_hash,s.expires_at,s.token_hash "
        "FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=?",
        (token_hash(token),),
    )
    if not rows:
        return None
    session = rows[0]
    if not session["is_active"] or session["expires_at"] <= time.time():
        await db.execute("DELETE FROM sessions WHERE token_hash=?", (session["token_hash"],))
        return None
    return session


def role_at_least(role: str, required: str) -> bool:
    return ROLE_LEVEL.get(role, 0) >= ROLE_LEVEL[required]


def minimum_role(path: str, method: str) -> str:
    if method in {"GET", "HEAD", "OPTIONS"}:
        if path.startswith("/api/auth/users"):
            return "admin"
        return "viewer"
    if path.startswith("/api/auth/users"):
        return "admin"
    if path in {"/api/auth/logout", "/api/auth/change-password"}:
        return "viewer"
    if path.startswith("/api/hosts/") and path.endswith(("/poll", "/maintenance", "/test-snmp")):
        return "operator"
    if path.startswith("/api/incidents/") and path.endswith(("/ack", "/resolve")):
        return "operator"
    return "admin"


def new_session_tokens() -> tuple[str, str]:
    return secrets.token_urlsafe(32), secrets.token_urlsafe(32)


def set_session_cookies(response, session_token: str, csrf_token: str) -> None:
    cookie_options = {
        "max_age": config.SESSION_TTL_SEC,
        "httponly": True,
        "secure": config.COOKIE_SECURE,
        "samesite": "strict",
        "path": "/",
    }
    response.set_cookie(SESSION_COOKIE, session_token, **cookie_options)
    response.set_cookie(CSRF_COOKIE, csrf_token, **{**cookie_options, "httponly": False})


def clear_session_cookies(response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/", secure=config.COOKIE_SECURE, httponly=True, samesite="strict")
    response.delete_cookie(CSRF_COOKIE, path="/", secure=config.COOKIE_SECURE, httponly=False, samesite="strict")
