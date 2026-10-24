from __future__ import annotations

import hmac
import json
import math
import time

from fastapi import APIRouter, Header, HTTPException, Request

from noc.metrics_catalog import CATALOG
from noc.collectors.tcp_http_collector import collect_probes


router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/push")
async def push_report(request: Request, x_agent_token: str = Header(default="", alias="X-Agent-Token")):
    if not x_agent_token:
        raise HTTPException(401, "X-Agent-Token is required")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON body") from None
    if not isinstance(payload, dict):
        raise HTTPException(400, "Invalid agent payload")
    snapshot = payload.get("snapshot")
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("metrics"), list) or not isinstance(snapshot.get("details", {}), dict):
        raise HTTPException(400, "Invalid agent snapshot")
    if len(snapshot["metrics"]) > 10000:
        raise HTTPException(413, "Agent snapshot has too many metric samples")
    hosts = await request.app.state.db.query("SELECT * FROM hosts WHERE host_type='agent' AND enabled=1")
    host = None
    for row in hosts:
        stored = json.loads(row["config_json"])
        if hmac.compare_digest(str(stored.get("agent_token", "")), x_agent_token):
            host = row
            config = stored
            break
    if host is None or config.get("mode", "push") != "push":
        raise HTTPException(401, "Unknown or disabled agent token")
    now = time.time()
    snapshot["ts"] = now
    snapshot["status"] = "maintenance" if host["status"] == "maintenance" else "up"
    snapshot["status_reason"] = "maintenance mode" if snapshot["status"] == "maintenance" else "agent report received"
    snapshot.setdefault("details", {})
    snapshot.setdefault("os_info", host.get("os_info", ""))
    for metric in snapshot["metrics"]:
        if not isinstance(metric, dict) or metric.get("key") not in CATALOG or not isinstance(metric.get("value"), (int, float, type(None))):
            raise HTTPException(400, "Invalid metric sample")
        if isinstance(metric["value"], (int, float)) and not math.isfinite(metric["value"]):
            raise HTTPException(400, "Metric values must be finite")
        if not isinstance(metric.get("resource_key", ""), str) or len(metric.get("resource_key", "")) > 255:
            raise HTTPException(400, "Invalid metric resource_key")
    boot = snapshot.get("boot_time")
    if boot is not None and (not isinstance(boot, (int, float)) or not math.isfinite(boot)):
        raise HTTPException(400, "Invalid boot_time")
    rebooted = int(boot is not None and host.get("last_boot_time") is not None and abs(float(boot) - float(host["last_boot_time"])) > 2)
    snapshot["metrics"] = [m for m in snapshot["metrics"] if m.get("key") not in ("host.offline", "system.rebooted")]
    snapshot["metrics"].extend([
        {"key": "system.rebooted", "value": rebooted, "unit": "bool", "resource_key": ""},
        {"key": "host.offline", "value": 0, "unit": "bool", "resource_key": ""},
    ])
    probes = await collect_probes(host["hostname"], {**config, "icmp": False}, "agent")
    snapshot["metrics"].extend(probes["metrics"])
    snapshot["details"].update(probes["details"])
    host_for_alert = {**host, "status": snapshot["status"], "name": host["name"]}
    await request.app.state.db.enqueue_snapshot(host["id"], snapshot, snapshot["status"], snapshot["status_reason"], snapshot["os_info"], boot)
    await request.app.state.alert_engine.evaluate(host_for_alert, snapshot)
    await request.app.state.websocket_manager.broadcast({"type": "snapshot", "host_id": host["id"], "snapshot": snapshot})
    return {"ok": True, "host_id": host["id"], "received_at": now}
