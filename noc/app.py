from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from noc import config
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


app = FastAPI(title="NOC Monitor", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")
app.include_router(hosts_router)
app.include_router(metrics_router)
app.include_router(alerts_router)
app.include_router(channels_router)
app.include_router(agent_router)


@app.get("/")
async def index():
    return FileResponse(config.STATIC_DIR / "index.html")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/catalog")
async def catalog():
    from noc.metrics_catalog import CATALOG
    return CATALOG


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    manager: WebSocketManager = websocket.app.state.websocket_manager
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
