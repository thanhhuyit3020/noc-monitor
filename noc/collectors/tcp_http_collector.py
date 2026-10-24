from __future__ import annotations

import asyncio
import socket
import ssl
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

import httpx
from cryptography import x509

from noc.collectors.ping_collector import ping
from noc.metrics_catalog import resource_key


async def probe_tcp(host: str, port: int, timeout: float = 3.0) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout)
        writer.close()
        await writer.wait_closed()
        return {"up": True, "response_ms": (time.perf_counter() - started) * 1000}
    except (OSError, TimeoutError):
        return {"up": False, "response_ms": None}


async def _ssl_expiry(url: str, timeout: float = 5.0) -> float | None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return None
    context = ssl._create_unverified_context()
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(parsed.hostname, parsed.port or 443, ssl=context, server_hostname=parsed.hostname), timeout)
        der = writer.get_extra_info("ssl_object").getpeercert(binary_form=True)
        writer.close()
        await writer.wait_closed()
        if not der:
            return None
        cert = x509.load_der_x509_certificate(der)
        return (cert.not_valid_after_utc - datetime.now(timezone.utc)).total_seconds() / 86400
    except (OSError, ssl.SSLError, TimeoutError, ValueError):
        return None


async def probe_http(url: str, expected_status: list[int], body_match: str | None = None, ssl_check: bool = True) -> dict[str, Any]:
    started = time.perf_counter()
    result: dict[str, Any] = {"url": url, "status_code": 0, "response_ms": None, "ok": False, "body_match": None, "ssl_days_remaining": None}
    try:
        async with httpx.AsyncClient(verify=False, timeout=5, follow_redirects=True) as client:
            response = await client.get(url)
        body_matched = body_match in response.text if body_match else None
        result.update(status_code=response.status_code, response_ms=(time.perf_counter() - started) * 1000, ok=response.status_code in expected_status and body_matched is not False, body_match=body_matched)
    except (httpx.HTTPError, ValueError):
        result["response_ms"] = (time.perf_counter() - started) * 1000
    if ssl_check:
        result["ssl_days_remaining"] = await _ssl_expiry(url)
    return result


async def collect_probes(host: str, config: dict[str, Any], host_type: str) -> dict[str, Any]:
    metrics: list[dict[str, Any]] = []
    details: dict[str, Any] = {"ping": None, "ports": [], "http": []}

    def add(key: str, value: float | int | None, unit: str, resource: str = "") -> None:
        metrics.append({"key": key, "value": value, "unit": unit, "resource_key": resource})

    if config.get("icmp", host_type in ("ping_http", "agent", "snmp")):
        details["ping"] = await ping(host)
        for key, unit in (("latency_ms", "ms"), ("jitter_ms", "ms"), ("packet_loss_pct", "%")):
            add(f"ping.{key}", details["ping"][key], unit)
    for port in config.get("tcp_ports", []):
        result = await probe_tcp(host, int(port))
        result["port"] = int(port)
        details["ports"].append(result)
        add("tcp.port_up", int(result["up"]), "bool", resource_key("tcp", str(port)))
    for url in config.get("http_urls", []):
        result = await probe_http(url, config.get("expected_status", [200, 204, 301, 302]), config.get("body_match"), config.get("ssl_check", True))
        details["http"].append(result)
        key = resource_key("http", url)
        add("http.status_code", result["status_code"], "code", key)
        add("http.response_ms", result["response_ms"], "ms", key)
        add("http.check_ok", int(result["ok"]), "bool", key)
        add("ssl.days_remaining", result["ssl_days_remaining"], "days", key)
    return {"metrics": metrics, "details": details}
