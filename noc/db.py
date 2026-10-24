from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from noc import config
from noc.metrics_catalog import CATALOG


DEFAULT_RULES = [
    ("Host Offline", "host.offline", ">", 0, 0, 1),
    ("CPU High", "cpu.total_pct", ">", 80, 95, 2),
    ("RAM High", "ram.used_pct", ">", 85, 95, 2),
    ("Disk Space Low", "disk.used_pct", ">", 85, 95, 2),
    ("Ping Latency High", "ping.latency_ms", ">", 150, 500, 2),
    ("Packet Loss", "ping.packet_loss_pct", ">", 5, 20, 2),
    ("Windows Service Stopped", "service.stopped", ">", 0, 0, 1),
    ("SSL Certificate Expiring", "ssl.days_remaining", "<", 30, 7, 1),
    ("Unexpected Reboot", "system.rebooted", ">", 0, 0, 1),
]


class Database:
    def __init__(self, path: Path = config.DB_PATH) -> None:
        self.path = path
        self.connection: aiosqlite.Connection | None = None
        self.queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue(maxsize=10000)
        self.writer_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    async def open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = await aiosqlite.connect(self.path)
        self.connection.row_factory = aiosqlite.Row
        await self.connection.execute("PRAGMA journal_mode=WAL")
        await self.connection.execute("PRAGMA synchronous=NORMAL")
        await self.connection.execute("PRAGMA foreign_keys=ON")
        await self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS hosts (
          id TEXT PRIMARY KEY, name TEXT NOT NULL, hostname TEXT NOT NULL, host_type TEXT NOT NULL,
          poll_interval_sec INTEGER NOT NULL DEFAULT 15, enabled INTEGER NOT NULL DEFAULT 1,
          status TEXT NOT NULL DEFAULT 'unknown', status_reason TEXT NOT NULL DEFAULT '', os_info TEXT NOT NULL DEFAULT '',
          last_seen_at REAL, last_boot_time REAL, config_json TEXT NOT NULL DEFAULT '{}', tags_json TEXT NOT NULL DEFAULT '[]',
          created_at REAL NOT NULL, updated_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS host_snapshots (
          host_id TEXT PRIMARY KEY REFERENCES hosts(id) ON DELETE CASCADE, ts REAL NOT NULL,
          cpu_pct REAL, ram_pct REAL, disk_pct REAL, latency_ms REAL, payload_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS metrics_raw (
          id INTEGER PRIMARY KEY AUTOINCREMENT, host_id TEXT NOT NULL REFERENCES hosts(id) ON DELETE CASCADE,
          ts REAL NOT NULL, metric_key TEXT NOT NULL, value REAL, unit TEXT NOT NULL DEFAULT '', resource_key TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_metrics_host_time ON metrics_raw(host_id, ts DESC);
        CREATE INDEX IF NOT EXISTS idx_metrics_lookup ON metrics_raw(host_id, metric_key, resource_key, ts DESC);
        CREATE TABLE IF NOT EXISTS metrics_hourly (
          host_id TEXT NOT NULL REFERENCES hosts(id) ON DELETE CASCADE, hour_ts INTEGER NOT NULL,
          metric_key TEXT NOT NULL, resource_key TEXT NOT NULL DEFAULT '', sample_count INTEGER NOT NULL,
          sum_value REAL NOT NULL, avg_value REAL NOT NULL, max_value REAL NOT NULL,
          PRIMARY KEY(host_id, hour_ts, metric_key, resource_key)
        );
        CREATE TABLE IF NOT EXISTS alert_rules (
          id TEXT PRIMARY KEY, name TEXT NOT NULL, metric_key TEXT NOT NULL, operator TEXT NOT NULL,
          warning REAL, critical REAL, consecutive_polls INTEGER NOT NULL DEFAULT 1, cooldown_sec INTEGER NOT NULL DEFAULT 300,
          enabled INTEGER NOT NULL DEFAULT 1, applies_to_json TEXT NOT NULL DEFAULT '[]', created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS incidents (
          id TEXT PRIMARY KEY, host_id TEXT NOT NULL REFERENCES hosts(id) ON DELETE CASCADE,
          rule_id TEXT NOT NULL REFERENCES alert_rules(id) ON DELETE CASCADE, resource_key TEXT NOT NULL DEFAULT '',
          severity TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'OPEN', message TEXT NOT NULL,
          opened_at REAL NOT NULL, updated_at REAL NOT NULL, acknowledged_at REAL, resolved_at REAL,
          last_notified_at REAL, UNIQUE(host_id, rule_id, resource_key, state)
        );
        CREATE INDEX IF NOT EXISTS idx_incidents_state ON incidents(state, severity, updated_at DESC);
        CREATE TABLE IF NOT EXISTS notification_channels (
          id TEXT PRIMARY KEY, name TEXT NOT NULL, channel_type TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
          config_json TEXT NOT NULL DEFAULT '{}', created_at REAL NOT NULL, updated_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS notification_logs (
          id INTEGER PRIMARY KEY AUTOINCREMENT, incident_id TEXT, channel_id TEXT, channel_type TEXT NOT NULL,
          sent_at REAL NOT NULL, success INTEGER NOT NULL, error TEXT NOT NULL DEFAULT '', payload TEXT NOT NULL DEFAULT ''
        );
        """)
        now = time.time()
        cursor = await self.connection.execute("SELECT count(*) FROM hosts")
        if (await cursor.fetchone())[0] == 0:
            config_json = json.dumps({"windows_services": ["EventLog", "LanmanServer", "Dnscache", "Winmgmt", "Schedule", "W32Time", "Spooler"], "tcp_ports": [], "http_urls": [], "eventlog_channels": ["System", "Application"]})
            await self.connection.execute(
                "INSERT INTO hosts(id,name,hostname,host_type,poll_interval_sec,config_json,tags_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                ("local", "NOC Server (Local)", "127.0.0.1", "local", config.POLL_INTERVAL_SEC, config_json, "[]", now, now),
            )
        cursor = await self.connection.execute("SELECT count(*) FROM alert_rules")
        if (await cursor.fetchone())[0] == 0:
            for rule in DEFAULT_RULES:
                name, metric, op, warning, critical, consecutive = rule
                metric_profiles = CATALOG[metric]["applies_to"]
                await self.connection.execute(
                    "INSERT INTO alert_rules(id,name,metric_key,operator,warning,critical,consecutive_polls,cooldown_sec,enabled,applies_to_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (name.lower().replace(" ", "-"), name, metric, op, warning, critical, consecutive, 300, 1, json.dumps(metric_profiles), now),
                )
        await self.connection.commit()
        self.writer_task = asyncio.create_task(self._writer(), name="noc-db-writer")

    async def close(self) -> None:
        if self.writer_task:
            await self.queue.join()
            self.writer_task.cancel()
            try:
                await self.writer_task
            except asyncio.CancelledError:
                pass
        if self.connection:
            await self.connection.close()
            self.connection = None

    async def query(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        assert self.connection is not None
        async with self._lock:
            cursor = await self.connection.execute(sql, params)
            rows = await cursor.fetchall()
            await cursor.close()
        return [dict(row) for row in rows]

    async def execute(self, sql: str, params: tuple = ()) -> int:
        assert self.connection is not None
        async with self._lock:
            cursor = await self.connection.execute(sql, params)
            await self.connection.commit()
            count = cursor.rowcount
            await cursor.close()
        return count

    async def enqueue_snapshot(self, host_id: str, snapshot: dict[str, Any], status: str, reason: str, os_info: str, boot_time: float | None) -> None:
        await self.queue.put({"host_id": host_id, "snapshot": snapshot, "status": status, "reason": reason, "os_info": os_info, "boot_time": boot_time})

    async def _writer(self) -> None:
        assert self.connection is not None
        next_cleanup = time.time() + 3600
        while True:
            first = await self.queue.get()
            if first is None:
                self.queue.task_done()
                break
            batch = [first]
            deadline = asyncio.get_running_loop().time() + 0.25
            while len(batch) < 500:
                timeout = deadline - asyncio.get_running_loop().time()
                if timeout <= 0:
                    break
                try:
                    item = await asyncio.wait_for(self.queue.get(), timeout)
                except TimeoutError:
                    break
                if item is None:
                    self.queue.task_done()
                    continue
                batch.append(item)
            now = time.time()
            while True:
                try:
                    async with self._lock:
                        await self.connection.execute("BEGIN")
                        for item in batch:
                            snap = item["snapshot"]
                            metrics = snap.get("metrics", [])
                            get_value = lambda key: next((m.get("value") for m in metrics if m.get("key") == key and not m.get("resource_key")), None)
                            await self.connection.execute(
                                "UPDATE hosts SET status=CASE WHEN status='maintenance' THEN status ELSE ? END,status_reason=?,os_info=COALESCE(NULLIF(?,''),os_info),last_seen_at=CASE WHEN ? IN ('up','maintenance') THEN ? ELSE last_seen_at END,last_boot_time=COALESCE(?,last_boot_time),updated_at=? WHERE id=?",
                                (item["status"], item["reason"], item["os_info"], item["status"], snap.get("ts", now), item["boot_time"], now, item["host_id"]),
                            )
                            await self.connection.execute(
                                "INSERT INTO host_snapshots(host_id,ts,cpu_pct,ram_pct,disk_pct,latency_ms,payload_json) VALUES(?,?,?,?,?,?,?) ON CONFLICT(host_id) DO UPDATE SET ts=excluded.ts,cpu_pct=excluded.cpu_pct,ram_pct=excluded.ram_pct,disk_pct=excluded.disk_pct,latency_ms=excluded.latency_ms,payload_json=excluded.payload_json",
                                (item["host_id"], snap.get("ts", now), get_value("cpu.total_pct"), get_value("ram.used_pct"), max((m.get("value") or 0 for m in metrics if m.get("key") == "disk.used_pct"), default=None), get_value("ping.latency_ms"), json.dumps(snap, default=str)),
                            )
                            raw = [(item["host_id"], snap.get("ts", now), m["key"], m.get("value"), m.get("unit", ""), m.get("resource_key", "")) for m in metrics if m.get("value") is not None]
                            await self.connection.executemany("INSERT INTO metrics_raw(host_id,ts,metric_key,value,unit,resource_key) VALUES(?,?,?,?,?,?)", raw)
                            hour_ts = int(snap.get("ts", now) // 3600 * 3600)
                            for row in raw:
                                _, _, metric_key, value, _, resource = row
                                await self.connection.execute("INSERT INTO metrics_hourly(host_id,hour_ts,metric_key,resource_key,sample_count,sum_value,avg_value,max_value) VALUES(?,?,?,?,1,?,?,?) ON CONFLICT(host_id,hour_ts,metric_key,resource_key) DO UPDATE SET sample_count=sample_count+1,sum_value=sum_value+excluded.sum_value,avg_value=(sum_value+excluded.sum_value)/(sample_count+1),max_value=max(max_value,excluded.max_value)", (item["host_id"], hour_ts, metric_key, resource, value, value, value))
                        await self.connection.commit()
                    break
                except Exception as exc:
                    await self.connection.rollback()
                    print(f"NOC DB writer retrying batch ({len(batch)} snapshots): {exc}")
                    await asyncio.sleep(1)
            for item in batch:
                self.queue.task_done()
            if time.time() >= next_cleanup:
                cutoff_raw = time.time() - config.RAW_RETENTION_DAYS * 86400
                cutoff_hourly = time.time() - config.HOURLY_RETENTION_DAYS * 86400
                async with self._lock:
                    await self.connection.execute("DELETE FROM metrics_raw WHERE ts < ?", (cutoff_raw,))
                    await self.connection.execute("DELETE FROM metrics_hourly WHERE hour_ts < ?", (cutoff_hourly,))
                    await self.connection.commit()
                next_cleanup = time.time() + 3600
        cutoff_raw = time.time() - config.RAW_RETENTION_DAYS * 86400
        cutoff_hourly = time.time() - config.HOURLY_RETENTION_DAYS * 86400
        async with self._lock:
            await self.connection.execute("DELETE FROM metrics_raw WHERE ts < ?", (cutoff_raw,))
            await self.connection.execute("DELETE FROM metrics_hourly WHERE hour_ts < ?", (cutoff_hourly,))
            await self.connection.commit()
