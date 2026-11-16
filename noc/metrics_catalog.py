from __future__ import annotations


CATALOG = {
    "host.offline": {"unit": "bool", "resource_scoped": False, "applies_to": ["local", "agent", "snmp", "ping_http"]},
    "cpu.total_pct": {"unit": "%", "resource_scoped": False, "applies_to": ["local", "agent", "snmp"]},
    "cpu.core_pct": {"unit": "%", "resource_scoped": True, "applies_to": ["local", "agent", "snmp"]},
    "ram.used_pct": {"unit": "%", "resource_scoped": False, "applies_to": ["local", "agent", "snmp"]},
    "ram.used_bytes": {"unit": "bytes", "resource_scoped": False, "applies_to": ["local", "agent", "snmp"]},
    "ram.total_bytes": {"unit": "bytes", "resource_scoped": False, "applies_to": ["local", "agent", "snmp"]},
    "swap.used_pct": {"unit": "%", "resource_scoped": False, "applies_to": ["local", "agent", "snmp"]},
    "disk.used_pct": {"unit": "%", "resource_scoped": True, "applies_to": ["local", "agent", "snmp"]},
    "disk.used_bytes": {"unit": "bytes", "resource_scoped": True, "applies_to": ["local", "agent", "snmp"]},
    "disk.total_bytes": {"unit": "bytes", "resource_scoped": True, "applies_to": ["local", "agent", "snmp"]},
    "disk.read_bps": {"unit": "bytes/s", "resource_scoped": True, "applies_to": ["local", "agent"]},
    "disk.write_bps": {"unit": "bytes/s", "resource_scoped": True, "applies_to": ["local", "agent"]},
    "disk.read_iops": {"unit": "IOPS", "resource_scoped": True, "applies_to": ["local", "agent"]},
    "disk.write_iops": {"unit": "IOPS", "resource_scoped": True, "applies_to": ["local", "agent"]},
    "net.rx_bps": {"unit": "bps", "resource_scoped": True, "applies_to": ["local", "agent", "snmp"]},
    "net.tx_bps": {"unit": "bps", "resource_scoped": True, "applies_to": ["local", "agent", "snmp"]},
    "net.if_up": {"unit": "bool", "resource_scoped": True, "applies_to": ["local", "agent", "snmp"]},
    "net.error_rate": {"unit": "errors/s", "resource_scoped": True, "applies_to": ["local", "agent", "snmp"]},
    "net.drop_rate": {"unit": "drops/s", "resource_scoped": True, "applies_to": ["local", "agent", "snmp"]},
    "ping.latency_ms": {"unit": "ms", "resource_scoped": False, "applies_to": ["agent", "snmp", "ping_http"]},
    "ping.jitter_ms": {"unit": "ms", "resource_scoped": False, "applies_to": ["agent", "snmp", "ping_http"]},
    "ping.packet_loss_pct": {"unit": "%", "resource_scoped": False, "applies_to": ["agent", "snmp", "ping_http"]},
    "service.stopped": {"unit": "bool", "resource_scoped": True, "applies_to": ["local", "agent"]},
    "eventlog.crit_err_1h": {"unit": "events", "resource_scoped": False, "applies_to": ["local", "agent"]},
    "tcp.port_up": {"unit": "bool", "resource_scoped": True, "applies_to": ["local", "agent", "ping_http"]},
    "http.status_code": {"unit": "code", "resource_scoped": True, "applies_to": ["local", "agent", "ping_http"]},
    "http.response_ms": {"unit": "ms", "resource_scoped": True, "applies_to": ["local", "agent", "ping_http"]},
    "http.check_ok": {"unit": "bool", "resource_scoped": True, "applies_to": ["local", "agent", "ping_http"]},
    "ssl.days_remaining": {"unit": "days", "resource_scoped": True, "applies_to": ["local", "agent", "ping_http"]},
    "system.rebooted": {"unit": "bool", "resource_scoped": False, "applies_to": ["local", "agent", "snmp"]},
    "tcp.established": {"unit": "connections", "resource_scoped": False, "applies_to": ["local", "agent", "snmp"]},
    "system.uptime_sec": {"unit": "seconds", "resource_scoped": False, "applies_to": ["local", "agent", "snmp"]},
}


def resource_key(kind: str, name: str) -> str:
    value = name.strip().rstrip("\\")
    if kind == "disk" and len(value) >= 2 and value[1] == ":":
        value = value[0].upper() + ":"
    return f"{kind}:{value}"


def validate_metric_key(key: str) -> bool:
    return key in CATALOG
