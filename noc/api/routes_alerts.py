from __future__ import annotations

import json
import time
import uuid

from fastapi import APIRouter, HTTPException, Request

from noc.metrics_catalog import CATALOG
from noc.models import RuleInput


router = APIRouter(prefix="/api", tags=["alerts"])


def _rule(row: dict) -> dict:
    return {**row, "enabled": bool(row["enabled"]), "applies_to": json.loads(row["applies_to_json"])}


@router.get("/rules")
async def list_rules(request: Request):
    return [_rule(row) for row in await request.app.state.db.query("SELECT * FROM alert_rules ORDER BY name COLLATE NOCASE")]


@router.post("/rules", status_code=201)
async def create_rule(body: RuleInput, request: Request):
    if body.metric_key not in CATALOG:
        raise HTTPException(400, "Unknown metric_key")
    rule_id = str(uuid.uuid4())
    applies = body.applies_to or CATALOG[body.metric_key]["applies_to"]
    now = time.time()
    await request.app.state.db.execute(
        "INSERT INTO alert_rules(id,name,metric_key,operator,warning,critical,consecutive_polls,cooldown_sec,enabled,applies_to_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (rule_id, body.name, body.metric_key, body.operator, body.warning, body.critical, body.consecutive_polls, body.cooldown_sec, int(body.enabled), json.dumps(applies), now),
    )
    return _rule((await request.app.state.db.query("SELECT * FROM alert_rules WHERE id=?", (rule_id,)))[0])


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, body: RuleInput, request: Request):
    if body.metric_key not in CATALOG:
        raise HTTPException(400, "Unknown metric_key")
    exists = await request.app.state.db.query("SELECT id FROM alert_rules WHERE id=?", (rule_id,))
    if not exists:
        raise HTTPException(404, "Rule not found")
    applies = body.applies_to or CATALOG[body.metric_key]["applies_to"]
    await request.app.state.db.execute(
        "UPDATE alert_rules SET name=?,metric_key=?,operator=?,warning=?,critical=?,consecutive_polls=?,cooldown_sec=?,enabled=?,applies_to_json=? WHERE id=?",
        (body.name, body.metric_key, body.operator, body.warning, body.critical, body.consecutive_polls, body.cooldown_sec, int(body.enabled), json.dumps(applies), rule_id),
    )
    return _rule((await request.app.state.db.query("SELECT * FROM alert_rules WHERE id=?", (rule_id,)))[0])


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(rule_id: str, request: Request):
    if not await request.app.state.db.execute("UPDATE alert_rules SET enabled=0 WHERE id=? AND enabled=1", (rule_id,)):
        raise HTTPException(404, "Rule not found")


@router.get("/incidents")
async def list_incidents(request: Request, state: str | None = None):
    sql = "SELECT i.*,h.name AS host_name,r.name AS rule_name FROM incidents i JOIN hosts h ON h.id=i.host_id JOIN alert_rules r ON r.id=i.rule_id"
    params: tuple = ()
    if state:
        sql += " WHERE i.state=?"
        params = (state.upper(),)
    sql += " ORDER BY CASE i.state WHEN 'OPEN' THEN 0 WHEN 'ACKNOWLEDGED' THEN 1 ELSE 2 END,i.updated_at DESC LIMIT 1000"
    return await request.app.state.db.query(sql, params)


@router.post("/incidents/{incident_id}/ack")
async def acknowledge_incident(incident_id: str, request: Request):
    now = time.time()
    count = await request.app.state.db.execute("UPDATE incidents SET state='ACKNOWLEDGED',acknowledged_at=?,updated_at=? WHERE id=? AND state='OPEN'", (now, now, incident_id))
    if not count:
        rows = await request.app.state.db.query("SELECT id,state FROM incidents WHERE id=?", (incident_id,))
        if not rows:
            raise HTTPException(404, "Incident not found")
        if rows[0]["state"] != "ACKNOWLEDGED":
            raise HTTPException(409, "Incident is already resolved")
    await request.app.state.websocket_manager.broadcast({"type": "incident_acknowledged", "id": incident_id, "acknowledged_at": now})
    return {"id": incident_id, "state": "ACKNOWLEDGED"}


@router.post("/incidents/{incident_id}/resolve")
async def resolve_incident(incident_id: str, request: Request):
    now = time.time()
    count = await request.app.state.db.execute("UPDATE incidents SET state='RESOLVED',resolved_at=?,updated_at=? WHERE id=? AND state IN ('OPEN','ACKNOWLEDGED')", (now, now, incident_id))
    if not count:
        rows = await request.app.state.db.query("SELECT id,state FROM incidents WHERE id=?", (incident_id,))
        if not rows:
            raise HTTPException(404, "Incident not found")
    await request.app.state.websocket_manager.broadcast({"type": "incident_resolved", "id": incident_id, "resolved_at": now})
    return {"id": incident_id, "state": "RESOLVED"}


@router.get("/notifications")
async def notification_logs(request: Request):
    return await request.app.state.db.query("SELECT * FROM notification_logs ORDER BY id DESC LIMIT 300")
