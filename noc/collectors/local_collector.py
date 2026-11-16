from __future__ import annotations

import asyncio
import platform
import time
from datetime import datetime
import xml.etree.ElementTree as ET
from collections import Counter
from typing import Any

import psutil

from noc.collectors.base import RateCalculator
from noc.metrics_catalog import resource_key


DEFAULT_SERVICES = ["EventLog", "LanmanServer", "Dnscache", "Winmgmt", "Schedule", "W32Time", "Spooler"]
TCP_STATES = ["ESTABLISHED", "LISTEN", "TIME_WAIT", "CLOSE_WAIT", "SYN_SENT", "SYN_RECV"]


class LocalCollector:
    def __init__(self) -> None:
        self.rate_calculator = RateCalculator()
        self.processes: dict[int, psutil.Process] = {}
        self.process_cpu_ready: set[int] = set()

    def _rate(self, key: str, counter: float, now: float) -> float | None:
        return self.rate_calculator.rate(key, counter, now)

    async def collect(self, config: dict[str, Any] | None = None) -> dict[str, Any]:
        return await asyncio.to_thread(self._collect, config or {})

    def _collect(self, config: dict[str, Any]) -> dict[str, Any]:
        now = time.time()
        metrics: list[dict[str, Any]] = []
        details: dict[str, Any] = {"disks": [], "disk_io": [], "networks": [], "services": [], "processes": [], "tcp_states": {}, "event_logs": []}

        def add(key: str, value: float | int | None, unit: str, resource: str = "") -> None:
            metrics.append({"key": key, "value": value, "unit": unit, "resource_key": resource})

        cpu_total = psutil.cpu_percent(interval=None)
        cores = psutil.cpu_percent(interval=None, percpu=True)
        add("cpu.total_pct", cpu_total, "%")
        details["cpu"] = {"total_pct": cpu_total, "per_core_pct": cores}
        for index, value in enumerate(cores):
            add("cpu.core_pct", value, "%", f"cpu:{index}")

        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        add("ram.used_pct", memory.percent, "%")
        add("ram.used_bytes", memory.used, "bytes")
        add("ram.total_bytes", memory.total, "bytes")
        add("swap.used_pct", swap.percent, "%")
        details["memory"] = {"total_bytes": memory.total, "used_bytes": memory.used, "available_bytes": memory.available, "used_pct": memory.percent, "swap_total_bytes": swap.total, "swap_used_bytes": swap.used, "swap_used_pct": swap.percent}

        try:
            for partition in psutil.disk_partitions(all=False):
                if not partition.mountpoint:
                    continue
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                except (PermissionError, OSError):
                    continue
                key = resource_key("disk", partition.device or partition.mountpoint)
                item = {"resource_key": key, "name": partition.device or partition.mountpoint, "mountpoint": partition.mountpoint, "fstype": partition.fstype, "total_bytes": usage.total, "used_bytes": usage.used, "free_bytes": usage.free, "used_pct": usage.percent}
                details["disks"].append(item)
                add("disk.used_pct", usage.percent, "%", key)
                add("disk.used_bytes", usage.used, "bytes", key)
                add("disk.total_bytes", usage.total, "bytes", key)
        except (PermissionError, OSError):
            pass

        try:
            io_counters = psutil.disk_io_counters(perdisk=True)
            if io_counters:
                for device, counters in io_counters.items():
                    if device.lower() == "total":
                        continue
                    key = resource_key("io", device)
                    read_bps = self._rate(f"disk:{device}:read_bytes", counters.read_bytes, now)
                    write_bps = self._rate(f"disk:{device}:write_bytes", counters.write_bytes, now)
                    read_iops = self._rate(f"disk:{device}:read_count", counters.read_count, now)
                    write_iops = self._rate(f"disk:{device}:write_count", counters.write_count, now)
                    item = {"resource_key": key, "name": device, "read_bps": read_bps, "write_bps": write_bps, "read_iops": read_iops, "write_iops": write_iops}
                    details["disk_io"].append(item)
                    add("disk.read_bps", read_bps, "bytes/s", key)
                    add("disk.write_bps", write_bps, "bytes/s", key)
                    add("disk.read_iops", read_iops, "IOPS", key)
                    add("disk.write_iops", write_iops, "IOPS", key)
        except (AttributeError, PermissionError, OSError):
            pass

        try:
            for name, counters in (psutil.net_io_counters(pernic=True) or {}).items():
                key = resource_key("nic", name)
                rx_bps = self._rate(f"net:{name}:rx", counters.bytes_recv, now)
                tx_bps = self._rate(f"net:{name}:tx", counters.bytes_sent, now)
                error_in = self._rate(f"net:{name}:errin", counters.errin, now)
                error_out = self._rate(f"net:{name}:errout", counters.errout, now)
                drop_in = self._rate(f"net:{name}:dropin", counters.dropin, now)
                drop_out = self._rate(f"net:{name}:dropout", counters.dropout, now)
                stats = psutil.net_if_stats().get(name)
                item = {"resource_key": key, "name": name, "rx_bps": rx_bps, "tx_bps": tx_bps, "is_up": bool(stats.isup) if stats else None, "speed_mbps": stats.speed if stats else None, "errin_per_sec": error_in, "errout_per_sec": error_out, "dropin_per_sec": drop_in, "dropout_per_sec": drop_out}
                details["networks"].append(item)
                add("net.if_up", int(stats.isup) if stats else None, "bool", key)
                add("net.rx_bps", None if rx_bps is None else rx_bps * 8, "bps", key)
                add("net.tx_bps", None if tx_bps is None else tx_bps * 8, "bps", key)
                add("net.error_rate", None if error_in is None or error_out is None else error_in + error_out, "errors/s", key)
                add("net.drop_rate", None if drop_in is None or drop_out is None else drop_in + drop_out, "drops/s", key)
        except (PermissionError, OSError):
            pass

        tcp_counts: Counter[str] = Counter()
        tcp_available = True
        try:
            for conn in psutil.net_connections(kind="tcp"):
                tcp_counts[str(conn.status).upper()] += 1
        except (psutil.AccessDenied, PermissionError, OSError):
            tcp_available = False
        details["tcp_states"] = {state: tcp_counts.get(state, 0) for state in TCP_STATES}
        add("tcp.established", tcp_counts.get("ESTABLISHED", 0) if tcp_available else None, "connections")

        self._collect_processes(details)
        services = config.get("windows_services") or DEFAULT_SERVICES
        service_rows = self._collect_services(services)
        details["services"] = service_rows or []
        for service in service_rows or []:
            status = service["status"]
            add("service.stopped", int(status in ("stopped", "missing")) if status != "unknown" else None, "bool", resource_key("svc", service["name"]))

        details["event_logs"], event_count = self._collect_event_logs(config.get("eventlog_channels") or ["System", "Application"])
        add("eventlog.crit_err_1h", event_count, "events")
        boot_time = psutil.boot_time()
        add("system.uptime_sec", max(0, now - boot_time), "seconds")
        return {"ts": now, "status": "up", "status_reason": "collector succeeded", "os_info": f"{platform.system()} {platform.release()} {platform.machine()}", "boot_time": boot_time, "metrics": metrics, "details": details}

    def _collect_processes(self, details: dict[str, Any]) -> None:
        found: dict[int, psutil.Process] = {}
        rows: list[dict[str, Any]] = []
        cpu_count = max(1, psutil.cpu_count(logical=True) or 1)
        for proc in psutil.process_iter(["pid", "name", "username", "memory_info"]):
            try:
                pid = proc.info["pid"]
                cached = self.processes.get(pid)
                if cached is None or not cached.is_running():
                    cached = psutil.Process(pid)
                    cached.cpu_percent(interval=None)
                    self.process_cpu_ready.add(pid)
                    raw_cpu = 0.0
                else:
                    raw_cpu = cached.cpu_percent(interval=None) if pid in self.process_cpu_ready else 0.0
                    self.process_cpu_ready.add(pid)
                if platform.system() != "Windows":
                    raw_cpu /= cpu_count
                info = proc.info
                mem = info.get("memory_info")
                rows.append({"pid": pid, "name": info.get("name") or "?", "user": info.get("username"), "cpu_pct": round(raw_cpu, 1), "memory_mb": round((mem.rss if mem else 0) / 1048576, 1)})
                found[pid] = cached
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, OSError):
                continue
        self.processes = found
        details["processes"] = {"cpu": sorted(rows, key=lambda row: row["cpu_pct"], reverse=True)[:10], "memory": sorted(rows, key=lambda row: row["memory_mb"], reverse=True)[:10]}

    @staticmethod
    def _collect_services(names: list[str]) -> list[dict[str, Any]] | None:
        if platform.system() != "Windows":
            return None
        services: list[dict[str, Any]] = []
        try:
            for service in psutil.win_service_iter():
                try:
                    name = service.name()
                except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
                    continue
                if name not in names:
                    continue
                try:
                    info = service.as_dict()
                    services.append({"name": name, "display_name": info.get("display_name"), "status": info.get("status", "unknown"), "start_type": info.get("start_type", "unknown"), "username": info.get("username")})
                except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
                    services.append({"name": name, "display_name": name, "status": "unknown", "start_type": "unknown"})
        except (AttributeError, psutil.Error, OSError):
            return None
        present = {service["name"] for service in services}
        services.extend({"name": name, "display_name": name, "status": "missing", "start_type": "unknown"} for name in names if name not in present)
        return services

    @staticmethod
    def _collect_event_logs(channels: list[str]) -> tuple[list[dict[str, Any]], int | None]:
        if platform.system() != "Windows":
            return [], None
        try:
            import win32evtlog
        except ImportError:
            return [], None
        events: list[dict[str, Any]] = []
        count = 0
        successful = False
        cutoff = time.time() - 3600
        ns = {"e": "http://schemas.microsoft.com/win/2004/08/events/event"}
        for channel in channels:
            handle = None
            try:
                query = "*[System[(Level=1 or Level=2)]]"
                handle = win32evtlog.EvtQuery(channel, win32evtlog.EvtQueryChannelPath | win32evtlog.EvtQueryReverseDirection, query)
                successful = True
                while count < 10000:
                    batch = win32evtlog.EvtNext(handle, 100)
                    if not batch:
                        break
                    stop = False
                    for event in batch:
                        root = ET.fromstring(win32evtlog.EvtRender(event, win32evtlog.EvtRenderEventXml))
                        system = root.find("e:System", ns)
                        if system is None:
                            continue
                        time_node = system.find("e:TimeCreated", ns)
                        event_time = time_node.attrib.get("SystemTime") if time_node is not None else None
                        timestamp = datetime.fromisoformat(event_time.replace("Z", "+00:00")).timestamp() if event_time else None
                        if timestamp is not None and timestamp < cutoff:
                            stop = True
                            break
                        count += 1
                        if len(events) < 10:
                            provider = system.find("e:Provider", ns)
                            events.append({
                                "channel": channel, "level": int(system.findtext("e:Level", default="0", namespaces=ns)),
                                "event_id": int(system.findtext("e:EventID", default="0", namespaces=ns)),
                                "source": provider.attrib.get("Name", "") if provider is not None else "",
                                "time": event_time or "", "timestamp": timestamp,
                                "message": " ".join(node.text or "" for node in root.findall(".//e:EventData/e:Data", ns))[:500],
                            })
                    if stop:
                        break
            except Exception:
                continue
            finally:
                if handle is not None:
                    try:
                        win32evtlog.EvtClose(handle)
                    except Exception:
                        pass
        return events[:10], count if successful else None
