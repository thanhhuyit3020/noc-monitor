from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from noc import config
from noc.collectors.agent_collector import pull_agent
from noc.collectors.local_collector import LocalCollector
from noc.collectors.snmp_collector import SNMPCollector
from noc.collectors.tcp_http_collector import collect_probes


class Scheduler:
    def __init__(self, db, alert_engine, websocket_manager) -> None:
        self.db = db
        self.alert_engine = alert_engine
        self.websocket_manager = websocket_manager
        self.local_collector = LocalCollector()
        self.snmp_collector = SNMPCollector()
        self.task: asyncio.Task | None = None
        self._last_poll: dict[str, float] = {}
        self._failures: dict[str, int] = {}
        self._host_locks: dict[str, asyncio.Lock] = {}
        self._semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_POLLS)

    def start(self) -> None:
        self.task = asyncio.create_task(self.run(), name="noc-scheduler")

    async def close(self) -> None:
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        self.snmp_collector.close()

    async def run(self) -> None:
        while True:
            now = time.time()
            hosts = await self.db.query("SELECT * FROM hosts WHERE enabled=1")
            due = []
            for host in hosts:
                if host["host_type"] == "agent" and json.loads(host["config_json"]).get("mode", "push") == "push":
                    await self._check_push_stale(host, now)
                    continue
                if now - self._last_poll.get(host["id"], 0) >= host["poll_interval_sec"]:
                    self._last_poll[host["id"]] = now
                    due.append(asyncio.create_task(self.poll(host["id"])))
            if due:
                await asyncio.gather(*due, return_exceptions=True)
            await asyncio.sleep(1)

    async def poll_now(self, host_id: str) -> dict[str, Any]:
        return await self.poll(host_id)

    async def poll(self, host_id: str) -> dict[str, Any]:
        lock = self._host_locks.setdefault(host_id, asyncio.Lock())
        async with lock:
            return await self._poll_locked(host_id)

    async def _poll_locked(self, host_id: str) -> dict[str, Any]:
        async with self._semaphore:
            hosts = await self.db.query("SELECT * FROM hosts WHERE id=?", (host_id,))
            if not hosts:
                raise KeyError("host not found")
            host = hosts[0]
            raw_config = json.loads(host["config_json"])
            maintenance = host["status"] == "maintenance"
            snapshot: dict[str, Any] = {"ts": time.time(), "status": "unknown", "status_reason": "", "os_info": host.get("os_info", ""), "boot_time": None, "metrics": [], "details": {}}
            try:
                if host["host_type"] == "local":
                    snapshot = await self.local_collector.collect(raw_config)
                    probes = await collect_probes(host["hostname"], {**raw_config, "icmp": False}, "local")
                    snapshot["metrics"].extend(probes["metrics"])
                    snapshot["details"].update(probes["details"])
                elif host["host_type"] == "ping_http":
                    probes = await collect_probes(host["hostname"], raw_config, "ping_http")
                    snapshot = self._probe_snapshot(probes)
                    outcomes = []
                    if probes["details"]["ping"] is not None:
                        outcomes.append(probes["details"]["ping"]["up"])
                    outcomes.extend(port["up"] for port in probes["details"]["ports"])
                    outcomes.extend(probe["ok"] for probe in probes["details"]["http"])
                    if not outcomes:
                        raise ValueError("Configure at least one ICMP, TCP or HTTP probe")
                    if not any(outcomes):
                        raise ConnectionError("All configured probes failed")
                elif host["host_type"] == "snmp":
                    snapshot = await self.snmp_collector.collect(host["hostname"], raw_config)
                    probes = await collect_probes(host["hostname"], {"icmp": True}, "snmp")
                    snapshot["metrics"].extend(probes["metrics"])
                    snapshot["details"].update(probes["details"])
                    if not snapshot["details"]["identity"].get("sys_name") and not snapshot["details"]["identity"].get("sys_descr"):
                        raise ConnectionError("No SNMP response")
                else:
                    if raw_config.get("mode", "push") == "pull":
                        snapshot = await pull_agent(host["hostname"], raw_config)
                        if not isinstance(snapshot, dict) or not isinstance(snapshot.get("metrics"), list):
                            raise ValueError("Agent returned an invalid snapshot")
                    else:
                        raise RuntimeError("Push agent is waiting for a report")
                    probes = await collect_probes(host["hostname"], {**raw_config, "icmp": False}, "agent")
                    snapshot.setdefault("details", {}).update(probes["details"])
                    snapshot.setdefault("metrics", []).extend(probes["metrics"])
                snapshot.setdefault("ts", time.time())
                snapshot.setdefault("metrics", [])
                snapshot.setdefault("details", {})
                snapshot["status"] = "up"
                snapshot["status_reason"] = "poll succeeded"
                self._failures[host_id] = 0
            except Exception as exc:
                failures = self._failures.get(host_id, 0) + 1
                self._failures[host_id] = failures
                snapshot.update(ts=time.time(), status="down" if failures >= 3 else "stale", status_reason=str(exc)[:300])
            if maintenance:
                snapshot["status"] = "maintenance"
                snapshot["status_reason"] = "maintenance mode"
            self._annotate_state(host, snapshot)
            await self.db.enqueue_snapshot(host_id, snapshot, snapshot["status"], snapshot["status_reason"], snapshot.get("os_info", ""), snapshot.get("boot_time"))
            await self.alert_engine.evaluate({**host, "status": snapshot["status"]}, snapshot)
            await self.websocket_manager.broadcast({"type": "snapshot", "host_id": host_id, "snapshot": snapshot})
            return snapshot

    @staticmethod
    def _probe_snapshot(probes: dict) -> dict[str, Any]:
        return {"ts": time.time(), "status": "up", "status_reason": "probe completed", "os_info": "", "boot_time": None, "metrics": probes["metrics"], "details": probes["details"]}

    @staticmethod
    def _set_metric(snapshot: dict, key: str, value: int, unit: str = "bool") -> None:
        snapshot["metrics"] = [m for m in snapshot.get("metrics", []) if m.get("key") != key]
        snapshot["metrics"].append({"key": key, "value": value, "unit": unit, "resource_key": ""})

    def _annotate_state(self, host: dict, snapshot: dict) -> None:
        old_boot = host.get("last_boot_time")
        boot = snapshot.get("boot_time")
        if boot is not None:
            self._set_metric(snapshot, "system.rebooted", int(old_boot is not None and abs(float(boot) - float(old_boot)) > 2), "bool")
        self._set_metric(snapshot, "host.offline", int(snapshot["status"] == "down"), "bool")

    async def _check_push_stale(self, host: dict, now: float) -> None:
        if host["status"] == "maintenance":
            return
        last_seen = host.get("last_seen_at") or host.get("created_at")
        age = now - float(last_seen or now)
        threshold = config.TIMEOUT_FACTOR * host["poll_interval_sec"]
        if age <= threshold:
            return
        status = "down" if age > threshold * 2 else "stale"
        if host["status"] == status:
            return
        reason = f"agent has not reported for {int(age)} seconds"
        await self.db.execute("UPDATE hosts SET status=?,status_reason=?,updated_at=? WHERE id=?", (status, reason, now, host["id"]))
        rows = await self.db.query("SELECT payload_json FROM host_snapshots WHERE host_id=?", (host["id"],))
        if rows:
            snapshot = json.loads(rows[0]["payload_json"])
        else:
            snapshot = {"metrics": [], "details": {}, "os_info": host.get("os_info", ""), "boot_time": host.get("last_boot_time")}
        snapshot.update(ts=now, status=status, status_reason=reason)
        snapshot["metrics"] = []
        self._set_metric(snapshot, "host.offline", int(status == "down"), "bool")
        await self.db.enqueue_snapshot(host["id"], snapshot, status, reason, host.get("os_info", ""), None)
        await self.alert_engine.evaluate({**host, "status": status}, snapshot)
        await self.websocket_manager.broadcast({"type": "host_status", "host_id": host["id"], "status": status, "status_reason": reason})
