from __future__ import annotations

import asyncio
import ctypes
import platform
import re
import socket
import statistics
import subprocess
import time
from typing import Any


class _IPOptionInformation(ctypes.Structure):
    _fields_ = [("ttl", ctypes.c_ubyte), ("tos", ctypes.c_ubyte), ("flags", ctypes.c_ubyte), ("options_size", ctypes.c_ubyte), ("options_data", ctypes.c_void_p)]


class _ICMPEchoReply(ctypes.Structure):
    _fields_ = [("address", ctypes.c_uint32), ("status", ctypes.c_uint32), ("round_trip_time", ctypes.c_uint32), ("data_size", ctypes.c_ushort), ("reserved", ctypes.c_ushort), ("data", ctypes.c_void_p), ("options", _IPOptionInformation)]


def _windows_echo(host: str, timeout_ms: int) -> tuple[bool, float | None, int]:
    address = socket.gethostbyname(host)
    api = ctypes.WinDLL("iphlpapi.dll")
    api.IcmpCreateFile.restype = ctypes.c_void_p
    api.IcmpSendEcho.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_ushort, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32]
    api.IcmpSendEcho.restype = ctypes.c_uint32
    api.IcmpCloseHandle.argtypes = [ctypes.c_void_p]
    handle = api.IcmpCreateFile()
    if handle in (None, ctypes.c_void_p(-1).value):
        return False, None, -1
    payload = ctypes.create_string_buffer(b"NOC")
    reply = ctypes.create_string_buffer(ctypes.sizeof(_ICMPEchoReply) + len(payload) + 8)
    try:
        count = api.IcmpSendEcho(handle, int.from_bytes(socket.inet_aton(address), "little"), payload, len(payload) - 1, None, reply, ctypes.sizeof(reply), timeout_ms)
        if not count:
            return False, None, 11010
        result = ctypes.cast(reply, ctypes.POINTER(_ICMPEchoReply)).contents
        return result.status in (0, 11013), float(result.round_trip_time), int(result.status)
    finally:
        api.IcmpCloseHandle(handle)


def _fallback_echo(host: str, timeout_ms: int) -> tuple[bool, float | None, int]:
    flag = "-n" if platform.system() == "Windows" else "-c"
    timeout_flag = "-w" if platform.system() == "Windows" else "-W"
    timeout_value = str(timeout_ms if platform.system() == "Windows" else max(1, timeout_ms // 1000))
    started = time.perf_counter()
    try:
        result = subprocess.run(["ping", flag, "1", timeout_flag, timeout_value, host], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout_ms / 1000 + 2)
        match = re.search(r"(?:time|thời gian)[=<]\s*([\d,.]+)\s*ms", result.stdout + result.stderr, re.I)
        if result.returncode == 0:
            return True, float(match.group(1).replace(",", ".")) if match else (time.perf_counter() - started) * 1000, 0
        return False, None, result.returncode
    except (OSError, subprocess.TimeoutExpired):
        return False, None, -1


def _ping_once(host: str, timeout_ms: int) -> tuple[bool, float | None, int]:
    if platform.system() == "Windows":
        try:
            return _windows_echo(host, timeout_ms)
        except (OSError, ctypes.ArgumentError):
            return _fallback_echo(host, timeout_ms)
    return _fallback_echo(host, timeout_ms)


async def ping(host: str, count: int = 4, timeout_ms: int = 1200) -> dict[str, Any]:
    results = await asyncio.to_thread(lambda: [_ping_once(host, timeout_ms) for _ in range(count)])
    latencies = [result[1] for result in results if result[0] and result[1] is not None]
    return {
        "up": bool(latencies),
        "latency_ms": sum(latencies) / len(latencies) if latencies else None,
        "min_ms": min(latencies) if latencies else None,
        "max_ms": max(latencies) if latencies else None,
        "jitter_ms": statistics.fmean(abs(right - left) for left, right in zip(latencies, latencies[1:])) if len(latencies) > 1 else (0.0 if latencies else None),
        "packet_loss_pct": 100.0 * (count - len(latencies)) / count,
        "statuses": [status for _, _, status in results],
    }
