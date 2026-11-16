from __future__ import annotations

from contextlib import asynccontextmanager

import hmac

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from noc import config
from noc.auth import CSRF_COOKIE, SESSION_COOKIE, minimum_role, role_at_least, token_hash, user_for_session
from noc.api.routes_auth import router as auth_router
from noc.api.routes_agent import router as agent_router
from noc.api.routes_alerts import router as alerts_router
from noc.api.routes_channels import router as channels_router
from noc.api.routes_hosts import router as hosts_router
from noc.api.routes_metrics import router as metrics_router
from noc.api.ws_manager import WebSocketManager
from noc.db import Database
from noc.engine.alert_engine import AlertEngine
from noc.engine.notifiers import Notifier
from noc.engine.scheduler import Scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = Database()
    await db.open()
    ws = WebSocketManager()
    notifier = Notifier(db, ws)
    alerts = AlertEngine(db, notifier)
    scheduler = Scheduler(db, alerts, ws)
    app.state.db = db
    app.state.websocket_manager = ws
    app.state.notifier = notifier
    app.state.alert_engine = alerts
    app.state.scheduler = scheduler
    scheduler.start()
    try:
        yield
    finally:
        await scheduler.close()
        await db.close()


app = FastAPI(title="NOC Monitor", version=config.VERSION, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")
app.include_router(auth_router)
app.include_router(hosts_router)
app.include_router(metrics_router)
app.include_router(alerts_router)
app.include_router(channels_router)
app.include_router(agent_router)


@app.middleware("http")
async def protect_api(request: Request, call_next):
    path = request.url.path
    public = {"/api/health", "/api/auth/status", "/api/auth/login", "/api/agent/push"}
    if path.startswith("/api/") and path not in public:
        db = getattr(request.app.state, "db", None)
        user = await user_for_session(db, request.cookies.get(SESSION_COOKIE)) if db else None
        if user is None:
            return JSONResponse({"detail": "Authentication required"}, status_code=401)
        request.state.auth_user = user
        required = minimum_role(path, request.method)
        if not role_at_least(user["role"], required):
            return JSONResponse({"detail": f"{required.title()} access is required"}, status_code=403)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
                return JSONResponse({"detail": "Cross-origin request rejected"}, status_code=403)
            csrf_cookie = request.cookies.get(CSRF_COOKIE, "")
            csrf_header = request.headers.get("x-csrf-token", "")
            if not csrf_cookie or not hmac.compare_digest(csrf_cookie.encode("utf-8"), csrf_header.encode("utf-8")) or not hmac.compare_digest(token_hash(csrf_cookie), user["csrf_hash"]):
                return JSONResponse({"detail": "CSRF validation failed"}, status_code=403)
    return await call_next(request)


@app.get("/")
async def index(request: Request):
    user = await user_for_session(request.app.state.db, request.cookies.get(SESSION_COOKIE))
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return FileResponse(config.TEMPLATE_DIR / "dashboard.html")


@app.get("/login")
async def login_page(request: Request):
    user = await user_for_session(request.app.state.db, request.cookies.get(SESSION_COOKIE))
    if user is not None:
        return RedirectResponse("/", status_code=303)
    return FileResponse(config.TEMPLATE_DIR / "login.html")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/catalog")
async def catalog():
    from noc.metrics_catalog import CATALOG
    return CATALOG


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    user = await user_for_session(websocket.app.state.db, websocket.cookies.get(SESSION_COOKIE))
    if user is None:
        await websocket.close(code=4401)
        return
    manager: WebSocketManager = websocket.app.state.websocket_manager
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
