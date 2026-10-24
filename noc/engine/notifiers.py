from __future__ import annotations

import json
import time
from email.message import EmailMessage
from typing import Any

import aiosmtplib
import httpx


class Notifier:
    def __init__(self, db, websocket_manager) -> None:
        self.db = db
        self.websocket_manager = websocket_manager

    async def incident(self, event: dict[str, Any]) -> None:
        await self.websocket_manager.broadcast({"type": "incident", "incident": event})
        for channel in await self.db.query("SELECT * FROM notification_channels WHERE enabled=1"):
            await self._deliver(channel, event)

    async def _deliver(self, channel: dict, event: dict[str, Any]) -> None:
        config = json.loads(channel["config_json"])
        success, error = True, ""
        try:
            if channel["channel_type"] == "telegram":
                async with httpx.AsyncClient(timeout=8) as client:
                    response = await client.post(
                        f"https://api.telegram.org/bot{config['bot_token']}/sendMessage",
                        json={"chat_id": config["chat_id"], "text": self._message(event)},
                    )
                    response.raise_for_status()
            elif channel["channel_type"] == "webhook":
                url = config["url"]
                host = url.lower().split("/", 3)[2].split(":", 1)[0] if "://" in url else ""
                body = {"content": self._message(event)} if "discord.com" in host or "discordapp.com" in host else {"text": self._message(event)} if "slack.com" in host else event
                async with httpx.AsyncClient(timeout=8) as client:
                    response = await client.post(url, json=body, headers=config.get("headers", {}))
                    response.raise_for_status()
            elif channel["channel_type"] == "smtp":
                message = EmailMessage()
                message["From"] = config["from"]
                message["To"] = config["to"]
                message["Subject"] = f"[{event.get('severity', 'alert').upper()}] {event.get('message', 'NOC incident')}"
                message.set_content(self._message(event))
                port = int(config.get("port", 587))
                await aiosmtplib.send(
                    message, hostname=config["host"], port=port,
                    username=config.get("username") or None, password=config.get("password") or None,
                    start_tls=bool(config.get("start_tls", port == 587)), use_tls=bool(config.get("use_tls", port == 465)), timeout=10,
                )
            elif channel["channel_type"] == "web_audio":
                pass
            else:
                raise ValueError(f"Unsupported notification channel: {channel['channel_type']}")
        except Exception as exc:
            success, error = False, str(exc)[:500]
        await self.db.execute(
            "INSERT INTO notification_logs(incident_id,channel_id,channel_type,sent_at,success,error,payload) VALUES(?,?,?,?,?,?,?)",
            (event.get("id"), channel["id"], channel["channel_type"], time.time(), int(success), error, json.dumps(event, default=str)),
        )

    @staticmethod
    def _message(event: dict[str, Any]) -> str:
        return f"{event.get('severity', 'ALERT').upper()} | {event.get('message', 'NOC incident')} | {event.get('state', 'OPEN')}"

    async def test(self, channel: dict) -> dict[str, Any]:
        event = {"id": "test", "severity": "warning", "state": "TEST", "message": "NOC test notification"}
        if channel["channel_type"] == "web_audio":
            await self.websocket_manager.broadcast({"type": "alarm_test", "incident": event})
            return {"ok": True}
        await self._deliver(channel, event)
        logs = await self.db.query("SELECT success,error FROM notification_logs WHERE channel_id=? ORDER BY id DESC LIMIT 1", (channel["id"],))
        return {"ok": bool(logs and logs[0]["success"]), "error": logs[0]["error"] if logs else ""}
