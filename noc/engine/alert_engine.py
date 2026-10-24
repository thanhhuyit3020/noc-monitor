from __future__ import annotations

import json
import operator
import time
import uuid
from typing import Any

from noc.metrics_catalog import CATALOG


OPERATORS = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le, "==": operator.eq, "!=": operator.ne}


class AlertEngine:
    def __init__(self, db, notifier) -> None:
        self.db = db
        self.notifier = notifier
        self.streaks: dict[tuple[str, str, str, str], int] = {}

    async def evaluate(self, host: dict[str, Any], snapshot: dict[str, Any]) -> None:
        if host.get("status") == "maintenance":
            return
        samples_by_key: dict[str, list[dict]] = {}
        for sample in snapshot.get("metrics", []):
            if sample.get("value") is not None:
                samples_by_key.setdefault(sample["key"], []).append(sample)
        rules = await self.db.query("SELECT * FROM alert_rules WHERE enabled=1")
        for rule in rules:
            key = rule["metric_key"]
            if key not in CATALOG:
                continue
            allowed = json.loads(rule["applies_to_json"])
            if allowed and host["host_type"] not in allowed:
                continue
            if host["host_type"] not in CATALOG[key]["applies_to"]:
                continue
            for sample in samples_by_key.get(key, []):
                resource = sample.get("resource_key", "")
                value = sample["value"]
                severity = self._severity(rule, value)
                prefix = (host["id"], rule["id"], resource)
                for token in [token for token in self.streaks if token[:3] == prefix and token[3] != (severity or "clear")]:
                    self.streaks.pop(token, None)
                token = (*prefix, severity or "clear")
                count = self.streaks.get(token, 0) + 1 if severity else 0
                self.streaks[token] = count
                if severity and count >= rule["consecutive_polls"]:
                    await self._open_or_update(host, rule, resource, severity, value)
                else:
                    await self._resolve_if_clear(host["id"], rule["id"], resource)

    @staticmethod
    def _severity(rule: dict, value: float) -> str | None:
        compare = OPERATORS[rule["operator"]]
        if rule["critical"] is not None and compare(value, rule["critical"]):
            return "critical"
        if rule["warning"] is not None and compare(value, rule["warning"]):
            return "warning"
        return None

    async def _open_or_update(self, host: dict, rule: dict, resource: str, severity: str, value: float) -> None:
        existing = await self.db.query("SELECT * FROM incidents WHERE host_id=? AND rule_id=? AND resource_key=? AND state IN ('OPEN','ACKNOWLEDGED') ORDER BY opened_at DESC LIMIT 1", (host["id"], rule["id"], resource))
        message = f"{rule['name']}: {value:g} {CATALOG[rule['metric_key']]['unit']} {rule['operator']} threshold on {host['name']}" + (f" ({resource})" if resource else "")
        now = time.time()
        if existing:
            current = existing[0]
            was_escalated = current["severity"] != severity and severity == "critical"
            should_resend = now - float(current.get("last_notified_at") or 0) >= rule["cooldown_sec"]
            notify = was_escalated or should_resend
            await self.db.execute("UPDATE incidents SET severity=?,message=?,updated_at=?,last_notified_at=CASE WHEN ? THEN ? ELSE last_notified_at END WHERE id=?", (severity, message, now, int(notify), now, current["id"]))
            if notify:
                event = {**current, "severity": severity, "message": message, "updated_at": now}
                await self.notifier.incident(event)
            return
        incident_id = str(uuid.uuid4())
        await self.db.execute(
            "INSERT INTO incidents(id,host_id,rule_id,resource_key,severity,state,message,opened_at,updated_at,last_notified_at) VALUES(?,?,?,?,?,'OPEN',?,?,?,?)",
            (incident_id, host["id"], rule["id"], resource, severity, message, now, now, now),
        )
        await self.notifier.incident({"id": incident_id, "host_id": host["id"], "host_name": host["name"], "rule_id": rule["id"], "resource_key": resource, "severity": severity, "state": "OPEN", "message": message, "opened_at": now})

    async def _resolve_if_clear(self, host_id: str, rule_id: str, resource: str) -> None:
        active = await self.db.query("SELECT * FROM incidents WHERE host_id=? AND rule_id=? AND resource_key=? AND state IN ('OPEN','ACKNOWLEDGED') ORDER BY opened_at DESC LIMIT 1", (host_id, rule_id, resource))
        if not active:
            return
        now = time.time()
        row = active[0]
        await self.db.execute("UPDATE incidents SET state='RESOLVED',updated_at=?,resolved_at=? WHERE id=?", (now, now, row["id"]))
        await self.notifier.websocket_manager.broadcast({"type": "incident_resolved", "id": row["id"], "host_id": host_id, "resource_key": resource, "resolved_at": now})
