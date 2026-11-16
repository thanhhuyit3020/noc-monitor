from __future__ import annotations

import asyncio
import time
import uuid
from collections import defaultdict, deque

import aiosqlite
from fastapi import APIRouter, HTTPException, Request, Response

from noc.auth import (
    CSRF_COOKIE,
    ROLE_LEVEL,
    SESSION_COOKIE,
    clear_session_cookies,
    dummy_password_check,
    new_session_tokens,
    password_hash,
    role_at_least,
    set_session_cookies,
    token_hash,
    user_for_session,
    verify_password,
)
from noc.auth_models import LoginInput, PasswordChange, UserCreate, UserUpdate
from noc import config


router = APIRouter(prefix="/api/auth", tags=["authentication"])
_attempts: dict[str, deque[float]] = defaultdict(deque)
_attempts_lock = asyncio.Lock()
_user_admin_lock = asyncio.Lock()
LOGIN_WINDOW_SEC = 60
LOGIN_MAX_FAILURES = 8


def _safe_user(row: dict) -> dict:
    return {"id": row["id"], "username": row["username"], "role": row["role"], "is_active": bool(row["is_active"]), "created_at": row["created_at"]}


async def _check_login_limit(client: str) -> None:
    now = time.time()
    async with _attempts_lock:
        attempts = _attempts[client]
        while attempts and now - attempts[0] > LOGIN_WINDOW_SEC:
            attempts.popleft()
        if len(attempts) >= LOGIN_MAX_FAILURES:
            raise HTTPException(429, "Too many failed sign-in attempts. Try again in one minute.")


async def _record_failed_login(client: str) -> None:
    async with _attempts_lock:
        _attempts[client].append(time.time())
        if len(_attempts) > 4096:
            _attempts.pop(next(iter(_attempts)))


async def _clear_failed_logins(client: str) -> None:
    async with _attempts_lock:
        _attempts.pop(client, None)


def _check_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    expected = str(request.base_url).rstrip("/")
    if origin and origin.rstrip("/") != expected:
        raise HTTPException(403, "Cross-origin request rejected")


@router.get("/status")
async def auth_status(request: Request):
    users = await request.app.state.db.query("SELECT 1 FROM users LIMIT 1")
    return {"bootstrap_required": not users}


@router.post("/login")
async def login(body: LoginInput, request: Request, response: Response):
    _check_origin(request)
    client = request.client.host if request.client else "unknown"
    await _check_login_limit(client)
    rows = await request.app.state.db.query("SELECT * FROM users WHERE username=? COLLATE NOCASE", (body.username,))
    user = rows[0] if rows else None
    if user is None:
        await asyncio.to_thread(dummy_password_check, body.password)
    password_valid = await asyncio.to_thread(verify_password, body.password, user["password_hash"]) if user else False
    valid = bool(user and user["is_active"] and password_valid)
    if not valid:
        await _record_failed_login(client)
        raise HTTPException(401, "Invalid username or password")

    await _clear_failed_logins(client)
    db = request.app.state.db
    now = time.time()
    await db.execute("DELETE FROM sessions WHERE expires_at<=?", (now,))
    session_token, csrf_token = new_session_tokens()
    await db.execute(
        "INSERT INTO sessions(token_hash,user_id,csrf_hash,created_at,expires_at) VALUES(?,?,?,?,?)",
        (token_hash(session_token), user["id"], token_hash(csrf_token), now, now + config.SESSION_TTL_SEC),
    )
    set_session_cookies(response, session_token, csrf_token)
    return {"id": user["id"], "username": user["username"], "role": user["role"]}


@router.get("/me")
async def current_user(request: Request):
    user = request.state.auth_user
    return {"id": user["id"], "username": user["username"], "role": user["role"]}


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response):
    session_token = request.cookies.get(SESSION_COOKIE)
    await request.app.state.db.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash(session_token),))
    clear_session_cookies(response)
    response.status_code = 204
    return response


@router.post("/change-password")
async def change_password(body: PasswordChange, request: Request):
    user = request.state.auth_user
    rows = await request.app.state.db.query("SELECT password_hash FROM users WHERE id=?", (user["id"],))
    if not rows or not await asyncio.to_thread(verify_password, body.current_password, rows[0]["password_hash"]):
        raise HTTPException(400, "Current password is incorrect")
    hashed = await asyncio.to_thread(password_hash, body.new_password)
    current_hash = token_hash(request.cookies[SESSION_COOKIE])
    await request.app.state.db.execute("UPDATE users SET password_hash=?,updated_at=? WHERE id=?", (hashed, time.time(), user["id"]))
    await request.app.state.db.execute("DELETE FROM sessions WHERE user_id=? AND token_hash<>?", (user["id"], current_hash))
    return {"ok": True}


@router.get("/users")
async def list_users(request: Request):
    actor = request.state.auth_user
    if not role_at_least(actor["role"], "admin"):
        raise HTTPException(403, "Admin access is required")
    rows = await request.app.state.db.query("SELECT id,username,role,is_active,created_at FROM users ORDER BY username COLLATE NOCASE")
    if actor["role"] == "global_admin":
        return [_safe_user(row) for row in rows]
    return [_safe_user(row) for row in rows if ROLE_LEVEL[row["role"]] < ROLE_LEVEL[actor["role"]]]


@router.post("/users", status_code=201)
async def create_user(body: UserCreate, request: Request):
    actor = request.state.auth_user
    if actor["role"] != "global_admin" and ROLE_LEVEL[body.role] >= ROLE_LEVEL[actor["role"]]:
        raise HTTPException(403, "You can only create users with lower access levels")
    db = request.app.state.db
    if await db.query("SELECT id FROM users WHERE username=? COLLATE NOCASE", (body.username,)):
        raise HTTPException(409, "Username is already in use")
    user_id = str(uuid.uuid4())
    now = time.time()
    hashed = await asyncio.to_thread(password_hash, body.password)
    try:
        await db.execute(
            "INSERT INTO users(id,username,password_hash,role,is_active,created_at,updated_at) VALUES(?,?,?,?,1,?,?)",
            (user_id, body.username, hashed, body.role, now, now),
        )
    except aiosqlite.IntegrityError:
        raise HTTPException(409, "Username is already in use") from None
    return _safe_user((await db.query("SELECT id,username,role,is_active,created_at FROM users WHERE id=?", (user_id,)))[0])


@router.put("/users/{user_id}")
async def update_user(user_id: str, body: UserUpdate, request: Request):
    actor = request.state.auth_user
    db = request.app.state.db
    async with _user_admin_lock:
        rows = await db.query("SELECT id,username,role,is_active,created_at FROM users WHERE id=?", (user_id,))
        if not rows:
            raise HTTPException(404, "User not found")
        user = rows[0]
        if user_id == actor["id"]:
            raise HTTPException(409, "Manage your own password from your account settings")
        if actor["role"] != "global_admin" and ROLE_LEVEL[user["role"]] >= ROLE_LEVEL[actor["role"]]:
            raise HTTPException(403, "You cannot manage an equal or higher access level")
        new_role = body.role or user["role"]
        if actor["role"] != "global_admin" and ROLE_LEVEL[new_role] >= ROLE_LEVEL[actor["role"]]:
            raise HTTPException(403, "You cannot assign an equal or higher access level")
        new_active = user["is_active"] if body.is_active is None else body.is_active
        if user["role"] == "global_admin" and (new_role != "global_admin" or not new_active) and user["is_active"]:
            active_globals = await db.query("SELECT count(*) AS total FROM users WHERE role='global_admin' AND is_active=1")
            if active_globals[0]["total"] <= 1:
                raise HTTPException(409, "At least one active Global Admin must remain")
        values = {
            "username": body.username if body.username is not None else user["username"],
            "role": new_role,
            "is_active": int(new_active),
            "password_hash": await asyncio.to_thread(password_hash, body.password) if body.password else None,
        }
        try:
            await db.execute(
                "UPDATE users SET username=?,role=?,is_active=?,password_hash=COALESCE(?,password_hash),updated_at=? WHERE id=?",
                (values["username"], values["role"], values["is_active"], values["password_hash"], time.time(), user_id),
            )
        except aiosqlite.IntegrityError:
            raise HTTPException(409, "Username is already in use") from None
        if values["role"] != user["role"] or not values["is_active"] or values["password_hash"]:
            await db.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
    updated = await db.query("SELECT id,username,role,is_active,created_at FROM users WHERE id=?", (user_id,))
    return _safe_user(updated[0])
