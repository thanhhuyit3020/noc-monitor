from __future__ import annotations

import json
import time
import uuid
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request

from noc.api.routes_hosts import SECRET_KEYS, mask_config, _merge_secrets


router = APIRouter(prefix="/api/channels", tags=["notification channels"])
CHANNEL_TYPES = {"web_audio", "telegram", "webhook", "smtp"}


@router.get("")
async def list_channels(request: Request):
    rows = await request.app.state.db.query("SELECT * FROM notification_channels ORDER BY name COLLATE NOCASE")
    return [{**{key: value for key, value in row.items() if key != "config_json"}, "enabled": bool(row["enabled"]), "config": mask_config(json.loads(row["config_json"]))} for row in rows]


@router.put("/{channel_id}")
async def save_channel(channel_id: str, body: dict, request: Request):
    channel_type = body.get("channel_type")
    if channel_type not in CHANNEL_TYPES:
        raise HTTPException(400, "Unsupported notification channel")
    if not isinstance(body.get("enabled", True), bool) or not isinstance(body.get("name", channel_type.title()), str):
        raise HTTPException(400, "Invalid channel name or enabled flag")
    config = body.get("config", {})
    if config is None:
        config = {}
    if not isinstance(config, dict):
        raise HTTPException(400, "Channel config must be an object")
    requirements = {
        "telegram": ("bot_token", "chat_id"),
        "webhook": ("url",),
        "smtp": ("host", "from", "to"),
        "web_audio": (),
    }[channel_type]
    for key in requirements:
        stored = await request.app.state.db.query("SELECT config_json FROM notification_channels WHERE id=?", (channel_id,))
        old_config = json.loads(stored[0]["config_json"]) if stored else {}
        if key in SECRET_KEYS and config.get(key) in (None, "", "********") and old_config.get(key):
            config[key] = old_config[key]
        if not isinstance(config.get(key), str) or not config[key]:
            raise HTTPException(400, f"{key} is required")
    if channel_type == "webhook":
        parsed = urlsplit(config["url"])
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise HTTPException(400, "Webhook URL must use HTTP or HTTPS")
        if not isinstance(config.get("headers", {}), dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in config.get("headers", {}).items()):
            raise HTTPException(400, "Webhook headers must be an object")
    if channel_type == "smtp":
        try:
            if not 1 <= int(config.get("port", 587)) <= 65535:
                raise ValueError
        except (TypeError, ValueError):
            raise HTTPException(400, "SMTP port is out of range") from None
        if any(key in config and not isinstance(config[key], bool) for key in ("start_tls", "use_tls")):
            raise HTTPException(400, "SMTP TLS flags must be boolean")
    existing = await request.app.state.db.query("SELECT * FROM notification_channels WHERE id=?", (channel_id,))
    now = time.time()
    if existing:
        config = _merge_secrets(config, json.loads(existing[0]["config_json"]))
        await request.app.state.db.execute(
            "UPDATE notification_channels SET name=?,channel_type=?,enabled=?,config_json=?,updated_at=? WHERE id=?",
            (body.get("name") or channel_type.title(), channel_type, int(bool(body.get("enabled", True))), json.dumps(config), now, channel_id),
        )
    else:
        channel_id = channel_id if channel_id != "new" else str(uuid.uuid4())
        await request.app.state.db.execute(
            "INSERT INTO notification_channels(id,name,channel_type,enabled,config_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
            (channel_id, body.get("name") or channel_type.title(), channel_type, int(bool(body.get("enabled", True))), json.dumps(config), now, now),
        )
    row = (await request.app.state.db.query("SELECT * FROM notification_channels WHERE id=?", (channel_id,)))[0]
    return {**{key: value for key, value in row.items() if key != "config_json"}, "enabled": bool(row["enabled"]), "config": mask_config(json.loads(row["config_json"]))}


@router.delete("/{channel_id}", status_code=204)
async def delete_channel(channel_id: str, request: Request):
    if not await request.app.state.db.execute("DELETE FROM notification_channels WHERE id=?", (channel_id,)):
        raise HTTPException(404, "Channel not found")


@router.post("/{channel_id}/test")
async def test_channel(channel_id: str, request: Request):
    rows = await request.app.state.db.query("SELECT * FROM notification_channels WHERE id=?", (channel_id,))
    if not rows:
        raise HTTPException(404, "Channel not found")
    return await request.app.state.notifier.test(rows[0])
