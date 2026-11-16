from __future__ import annotations

import json
import hmac
import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response

from noc.models import HostInput


router = APIRouter(prefix="/api/hosts", tags=["hosts"])
SECRET_KEYS = {"community", "priv_key", "auth_key", "smtp_password", "password", "bot_token", "agent_token", "authorization", "x-api-key", "api_key", "x-auth-token", "cookie", "url"}


def mask_config(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: "********" if key.lower() in SECRET_KEYS and item else mask_config(item) for key, item in value.items()}
    if isinstance(value, list):
        return [mask_config(item) for item in value]
    return value


def _host(row: dict) -> dict:
    return {
        **{key: value for key, value in row.items() if key not in {"config_json", "tags_json"}},
        "enabled": bool(row["enabled"]),
        "config": mask_config(json.loads(row["config_json"])),
        "tags": json.loads(row["tags_json"]),
    }


def _merge_secrets(new: Any, old: Any) -> Any:
    if isinstance(new, dict):
        old = old if isinstance(old, dict) else {}
        return {key: old.get(key) if key.lower() in SECRET_KEYS and (value == "********" or not value) and old.get(key) else _merge_secrets(value, old.get(key)) for key, value in new.items()}
    if isinstance(new, list):
        return new
    return new


async def _token_in_use(db, token: str, except_id: str | None = None) -> bool:
    rows = await db.query("SELECT id,config_json FROM hosts WHERE host_type='agent'")
    return any(row["id"] != except_id and hmac.compare_digest(str(json.loads(row["config_json"]).get("agent_token", "")), token) for row in rows)


@router.get("")
async def list_hosts(request: Request):
    rows = await request.app.state.db.query("SELECT * FROM hosts ORDER BY name COLLATE NOCASE")
    return [_host(row) for row in rows]


@router.post("", status_code=201)
async def create_host(body: HostInput, request: Request):
    if body.host_type == "local":
        raise HTTPException(422, "Local monitoring is reserved for the NOC Server host")
    if body.host_type == "agent" and await _token_in_use(request.app.state.db, body.config["agent_token"]):
        raise HTTPException(409, "Agent token is already assigned to another host")
    now = time.time()
    host_id = str(uuid.uuid4())
    await request.app.state.db.execute(
        "INSERT INTO hosts(id,name,hostname,host_type,poll_interval_sec,enabled,config_json,tags_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (host_id, body.name, body.hostname, body.host_type, body.poll_interval_sec, int(body.enabled), json.dumps(body.config), json.dumps(body.tags), now, now),
    )
    rows = await request.app.state.db.query("SELECT * FROM hosts WHERE id=?", (host_id,))
    await request.app.state.websocket_manager.broadcast({"type": "hosts_changed"})
    return _host(rows[0])


@router.put("/{host_id}")
async def update_host(host_id: str, body: HostInput, request: Request):
    rows = await request.app.state.db.query("SELECT * FROM hosts WHERE id=?", (host_id,))
    if not rows:
        raise HTTPException(404, "Host not found")
    old = rows[0]
    if (host_id == "local") != (body.host_type == "local"):
        raise HTTPException(422, "Local monitoring is reserved for the NOC Server host")
    config = _merge_secrets(body.config, json.loads(old["config_json"]))
    if body.host_type == "agent" and await _token_in_use(request.app.state.db, config["agent_token"], host_id):
        raise HTTPException(409, "Agent token is already assigned to another host")
    await request.app.state.db.execute(
        "UPDATE hosts SET name=?,hostname=?,host_type=?,poll_interval_sec=?,enabled=?,config_json=?,tags_json=?,updated_at=? WHERE id=?",
        (body.name, body.hostname, body.host_type, body.poll_interval_sec, int(body.enabled), json.dumps(config), json.dumps(body.tags), time.time(), host_id),
    )
    updated = (await request.app.state.db.query("SELECT * FROM hosts WHERE id=?", (host_id,)))[0]
    await request.app.state.websocket_manager.broadcast({"type": "hosts_changed"})
    return _host(updated)


@router.delete("/{host_id}", status_code=204)
async def delete_host(host_id: str, request: Request):
    if host_id == "local":
        raise HTTPException(409, "The local NOC Server host cannot be deleted")
    await request.app.state.db.queue.join()
    count = await request.app.state.db.execute("DELETE FROM hosts WHERE id=?", (host_id,))
    if not count:
        raise HTTPException(404, "Host not found")
    await request.app.state.websocket_manager.broadcast({"type": "hosts_changed"})
    return Response(status_code=204)


@router.post("/{host_id}/poll")
async def poll_host(host_id: str, request: Request):
    rows = await request.app.state.db.query("SELECT host_type,config_json FROM hosts WHERE id=?", (host_id,))
    if not rows:
        raise HTTPException(404, "Host not found")
    if rows[0]["host_type"] == "agent" and json.loads(rows[0]["config_json"]).get("mode", "push") == "push":
        raise HTTPException(409, "Push agents report on their own polling interval")
    try:
        return await request.app.state.scheduler.poll_now(host_id)
    except KeyError:
        raise HTTPException(404, "Host not found") from None


@router.post("/{host_id}/maintenance")
async def set_maintenance(host_id: str, body: dict[str, bool], request: Request):
    rows = await request.app.state.db.query("SELECT id FROM hosts WHERE id=?", (host_id,))
    if not rows:
        raise HTTPException(404, "Host not found")
    enabled = bool(body.get("enabled"))
    status = "maintenance" if enabled else "unknown"
    reason = "maintenance mode" if enabled else "maintenance ended; awaiting next poll"
    await request.app.state.db.execute("UPDATE hosts SET status=?,status_reason=?,updated_at=? WHERE id=?", (status, reason, time.time(), host_id))
    await request.app.state.websocket_manager.broadcast({"type": "host_status", "host_id": host_id, "status": status, "status_reason": reason})
    return {"host_id": host_id, "status": status}


@router.post("/{host_id}/test-snmp")
async def test_snmp(host_id: str, request: Request):
    rows = await request.app.state.db.query("SELECT * FROM hosts WHERE id=? AND host_type='snmp'", (host_id,))
    if not rows:
        raise HTTPException(404, "SNMP host not found")
    host = rows[0]
    try:
        result = await request.app.state.scheduler.snmp_collector.collect(host["hostname"], json.loads(host["config_json"]))
        identity = result["details"]["identity"]
        if not identity.get("sys_name") and not identity.get("sys_descr"):
            raise HTTPException(502, "No SNMP response from this host")
        return identity
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(502, f"SNMP probe failed: {exc}") from exc
