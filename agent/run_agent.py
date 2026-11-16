#!/usr/bin/env python3
"""Single-file NOC agent. Requires psutil; Push is the default transport."""

from __future__ import annotations

import argparse
import hmac
import json
import os
import platform
import socket
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import URLError
from urllib.request import Request, urlopen

import psutil


class Agent:
    def __init__(self, services: list[str]):
        self.services = services
        self.rates: dict[str, tuple[float, float]] = {}
        self.processes: dict[int, psutil.Process] = {}

    def rate(self, key: str, counter: float, now: float) -> float | None:
        old = self.rates.get(key)
        self.rates[key] = (counter, now)
        if old is None or now <= old[1]:
            return None
        delta = counter - old[0]
        return max(0.0, (counter if delta < 0 else delta) / (now - old[1]))

    def collect(self) -> dict:
        now = time.time()
        metrics, details = [], {"disks": [], "disk_io": [], "networks": [], "services": [], "processes": [], "tcp_states": {}, "event_logs": []}

        def add(key, value, unit="", resource_key=""):
            metrics.append({"key": key, "value": value, "unit": unit, "resource_key": resource_key})

        cpu = psutil.cpu_percent(interval=None)
        cores = psutil.cpu_percent(interval=None, percpu=True)
        add("cpu.total_pct", cpu, "%")
        for index, value in enumerate(cores):
            add("cpu.core_pct", value, "%", f"cpu:{index}")
        details["cpu"] = {"total_pct": cpu, "per_core_pct": cores}
        memory, swap = psutil.virtual_memory(), psutil.swap_memory()
        add("ram.used_pct", memory.percent, "%")
        add("ram.used_bytes", memory.used, "bytes")
        add("ram.total_bytes", memory.total, "bytes")
        add("swap.used_pct", swap.percent, "%")
        details["memory"] = {"total_bytes": memory.total, "used_bytes": memory.used, "available_bytes": memory.available, "used_pct": memory.percent, "swap_total_bytes": swap.total, "swap_used_bytes": swap.used, "swap_used_pct": swap.percent}

        try:
            partitions = psutil.disk_partitions(all=False)
        except (psutil.Error, OSError):
            partitions = []
        for part in partitions:
            try:
                usage = psutil.disk_usage(part.mountpoint)
            except (PermissionError, OSError):
                continue
            name = part.device or part.mountpoint
            key = f"disk:{name.rstrip(chr(92))}"
            details["disks"].append({"resource_key": key, "name": name, "mountpoint": part.mountpoint, "total_bytes": usage.total, "used_bytes": usage.used, "free_bytes": usage.free, "used_pct": usage.percent})
            add("disk.used_pct", usage.percent, "%", key)
            add("disk.used_bytes", usage.used, "bytes", key)
            add("disk.total_bytes", usage.total, "bytes", key)
        try:
            io = psutil.disk_io_counters(perdisk=True) or {}
        except (psutil.Error, OSError):
            io = {}
        for name, counters in io.items():
            if name.lower() == "total":
                continue
            key = f"io:{name}"
            read_bps = self.rate(f"io:{name}:rb", counters.read_bytes, now)
            write_bps = self.rate(f"io:{name}:wb", counters.write_bytes, now)
            read_iops = self.rate(f"io:{name}:rc", counters.read_count, now)
            write_iops = self.rate(f"io:{name}:wc", counters.write_count, now)
            details["disk_io"].append({"resource_key": key, "name": name, "read_bps": read_bps, "write_bps": write_bps, "read_iops": read_iops, "write_iops": write_iops})
            add("disk.read_bps", read_bps, "bytes/s", key)
            add("disk.write_bps", write_bps, "bytes/s", key)
            add("disk.read_iops", read_iops, "IOPS", key)
            add("disk.write_iops", write_iops, "IOPS", key)
        try:
            interfaces = psutil.net_io_counters(pernic=True) or {}
            interface_stats = psutil.net_if_stats()
        except (psutil.Error, OSError):
            interfaces, interface_stats = {}, {}
        for name, counters in interfaces.items():
            key = f"nic:{name.strip()}"
            rx = self.rate(f"net:{name}:rx", counters.bytes_recv, now)
            tx = self.rate(f"net:{name}:tx", counters.bytes_sent, now)
            errin = self.rate(f"net:{name}:errin", counters.errin, now)
            errout = self.rate(f"net:{name}:errout", counters.errout, now)
            dropin = self.rate(f"net:{name}:dropin", counters.dropin, now)
            dropout = self.rate(f"net:{name}:dropout", counters.dropout, now)
            stats = interface_stats.get(name)
            details["networks"].append({"resource_key": key, "name": name, "rx_bps": rx, "tx_bps": tx, "is_up": bool(stats and stats.isup), "speed_mbps": stats.speed if stats else None})
            add("net.rx_bps", None if rx is None else rx * 8, "bps", key)
            add("net.tx_bps", None if tx is None else tx * 8, "bps", key)
            add("net.error_rate", None if errin is None or errout is None else errin + errout, "errors/s", key)
            add("net.drop_rate", None if dropin is None or dropout is None else dropin + dropout, "drops/s", key)
        states = {name: 0 for name in ("ESTABLISHED", "LISTEN", "TIME_WAIT", "CLOSE_WAIT", "SYN_SENT", "SYN_RECV")}
        tcp_available = True
        try:
            for conn in psutil.net_connections(kind="tcp"):
                if conn.status in states:
                    states[conn.status] += 1
        except (psutil.AccessDenied, OSError):
            tcp_available = False
        details["tcp_states"] = states
        add("tcp.established", states["ESTABLISHED"] if tcp_available else None, "connections")

        rows, found = [], {}
        cpu_count = max(1, psutil.cpu_count(logical=True) or 1)
        for proc in psutil.process_iter(["pid", "name", "username", "memory_info"]):
            try:
                pid = proc.info["pid"]
                cached = self.processes.get(pid)
                if cached is None or not cached.is_running():
                    cached = psutil.Process(pid)
                    cached.cpu_percent(interval=None)
                    cpu_pct = 0.0
                else:
                    cpu_pct = cached.cpu_percent(interval=None)
                    if platform.system() != "Windows":
                        cpu_pct /= cpu_count
                info, mem = proc.info, proc.info.get("memory_info")
                rows.append({"pid": pid, "name": info.get("name") or "?", "user": info.get("username"), "cpu_pct": round(cpu_pct, 1), "memory_mb": round((mem.rss if mem else 0) / 1048576, 1)})
                found[pid] = cached
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        self.processes = found
        details["processes"] = {"cpu": sorted(rows, key=lambda row: row["cpu_pct"], reverse=True)[:10], "memory": sorted(rows, key=lambda row: row["memory_mb"], reverse=True)[:10]}

        if platform.system() == "Windows":
            available = {}
            services_available = True
            try:
                available = {s.name(): s for s in psutil.win_service_iter()}
            except (psutil.Error, OSError):
                services_available = False
            for name in self.services if services_available else []:
                try:
                    service_obj = available[name]
                except KeyError:
                    service = {"name": name, "display_name": name, "status": "missing", "start_type": "unknown"}
                else:
                    try:
                        info = service_obj.as_dict()
                        service = {"name": name, "display_name": info.get("display_name"), "status": info.get("status", "unknown"), "start_type": info.get("start_type", "unknown")}
                    except (psutil.Error, OSError):
                        service = {"name": name, "display_name": name, "status": "unknown", "start_type": "unknown"}
                details["services"].append(service)
                add("service.stopped", int(service["status"] in ("stopped", "missing")) if service["status"] != "unknown" else None, "bool", f"svc:{name}")
            details["event_logs"], event_count = self.event_logs(["System", "Application"])
            add("eventlog.crit_err_1h", event_count, "events")
        boot_time = psutil.boot_time()
        uptime = max(0, now - boot_time)
        add("system.uptime_sec", uptime, "seconds")
        return {"ts": now, "status": "up", "status_reason": "agent report received", "os_info": f"{platform.system()} {platform.release()} {platform.machine()}", "boot_time": boot_time, "metrics": metrics, "details": details}

    @staticmethod
    def event_logs(channels: list[str]) -> tuple[list[dict], int | None]:
        try:
            import win32evtlog
        except ImportError:
            return [], None
        cutoff = time.time() - 3600
        events, count = [], 0
        successful = False
        ns = {"e": "http://schemas.microsoft.com/win/2004/08/events/event"}
        for channel in channels:
            handle = None
            try:
                handle = win32evtlog.EvtQuery(channel, win32evtlog.EvtQueryChannelPath | win32evtlog.EvtQueryReverseDirection, "*[System[(Level=1 or Level=2)]]")
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
        return events, count if successful else None


def send(url: str, token: str, payload: dict) -> None:
    request = Request(url, data=json.dumps({"hostname": socket.gethostname(), "snapshot": payload}).encode(), headers={"Content-Type": "application/json", "X-Agent-Token": token}, method="POST")
    with urlopen(request, timeout=10) as response:
        response.read()


def serve(agent: Agent, token: str, host: str, port: int) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/metrics" or not hmac.compare_digest(self.headers.get("X-Agent-Token", ""), token):
                self.send_error(403)
                return
            body = json.dumps(agent.collect()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            return

    ThreadingHTTPServer((host, port), Handler).serve_forever()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NOC monitoring agent")
    parser.add_argument("--token", default=os.environ.get("NOC_AGENT_TOKEN"), help="Token configured on the NOC host record; defaults to NOC_AGENT_TOKEN")
    parser.add_argument("--push-url", default=os.environ.get("NOC_PUSH_URL"), help="NOC /api/agent/push URL; defaults to NOC_PUSH_URL")
    parser.add_argument("--once", action="store_true", help="Collect and push one snapshot")
    parser.add_argument("--interval", type=int, default=int(os.environ.get("NOC_AGENT_INTERVAL_SEC", "15")))
    parser.add_argument("--services", default="EventLog,LanmanServer,Dnscache,Winmgmt,Schedule,W32Time,Spooler")
    parser.add_argument("--pull", action="store_true", help="Serve /metrics for server-initiated Pull")
    parser.add_argument("--listen-host", default="127.0.0.1", help="Pull listener address; defaults to loopback")
    parser.add_argument("--port", type=int, default=9108)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not args.token:
        parser.error("--token or NOC_AGENT_TOKEN is required")
    agent = Agent([name.strip() for name in args.services.split(",") if name.strip()])
    if args.pull:
        serve(agent, args.token, args.listen_host, args.port)
        return
    if not args.push_url:
        parser.error("--push-url is required unless --pull is used")
    while True:
        payload = agent.collect()
        try:
            send(args.push_url, args.token, payload)
            print(f"sent snapshot {time.strftime('%Y-%m-%d %H:%M:%S')}")
        except (OSError, URLError, TimeoutError) as exc:
            print(f"push failed: {exc}")
            if args.once:
                raise SystemExit(1) from exc
        if args.once:
            break
        time.sleep(max(5, args.interval))


if __name__ == "__main__":
    main()
