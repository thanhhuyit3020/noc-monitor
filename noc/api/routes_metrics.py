from __future__ import annotations

import json
import time

from fastapi import APIRouter, HTTPException, Query, Request

from noc.metrics_catalog import CATALOG


router = APIRouter(prefix="/api", tags=["metrics"])
RANGES = {"1h": 3600, "6h": 21600, "24h": 86400, "7d": 604800, "30d": 2592000}


@router.get("/snapshots")
async def snapshots(request: Request):
    rows = await request.app.state.db.query(
        "SELECT h.id,h.name,h.hostname,h.host_type,h.status,h.status_reason,h.enabled,h.os_info,h.last_seen_at,h.poll_interval_sec,s.ts,s.cpu_pct,s.ram_pct,s.disk_pct,s.latency_ms,s.payload_json FROM hosts h LEFT JOIN host_snapshots s ON s.host_id=h.id ORDER BY h.name COLLATE NOCASE"
    )
    result = []
    for row in rows:
        item = {key: value for key, value in row.items() if key != "payload_json"}
        item["enabled"] = bool(item["enabled"])
        item["snapshot"] = json.loads(row["payload_json"]) if row["payload_json"] else None
        result.append(item)
    return result


@router.get("/metrics/{host_id}")
async def metric_history(host_id: str, request: Request, range: str = Query("1h"), metric_key: str | None = None):
    if range not in RANGES:
        raise HTTPException(400, "Range must be one of: " + ", ".join(RANGES))
    host = await request.app.state.db.query("SELECT id FROM hosts WHERE id=?", (host_id,))
    if not host:
        raise HTTPException(404, "Host not found")
    if metric_key is not None and metric_key not in CATALOG:
        raise HTTPException(400, "Unknown metric_key")
    cutoff = time.time() - RANGES[range]
    if RANGES[range] <= 7 * 86400:
        where_metric = " AND metric_key=?" if metric_key else ""
        params = (host_id, cutoff, metric_key) if metric_key else (host_id, cutoff)
        rows = await request.app.state.db.query(
            "SELECT * FROM (SELECT ts,metric_key,value,unit,resource_key FROM metrics_raw WHERE host_id=? AND ts>=?" + where_metric + " ORDER BY ts DESC LIMIT 20000) ORDER BY ts ASC",
            params,
        )
        return {"host_id": host_id, "range": range, "resolution": "raw", "points": rows}
    where_metric = " AND metric_key=?" if metric_key else ""
    params = (host_id, int(cutoff // 3600 * 3600), metric_key) if metric_key else (host_id, int(cutoff // 3600 * 3600))
    rows = await request.app.state.db.query(
        "SELECT hour_ts AS ts,metric_key,avg_value AS value,max_value,resource_key FROM metrics_hourly WHERE host_id=? AND hour_ts>=?" + where_metric + " ORDER BY hour_ts ASC",
        params,
    )
    return {"host_id": host_id, "range": range, "resolution": "hourly", "points": rows}
