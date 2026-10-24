from __future__ import annotations

import time
from typing import Any

import pysnmp.hlapi.v3arch.asyncio as hlapi

from noc.collectors.snmp_ber import SNMPBerClient
from noc.metrics_catalog import resource_key


PROFILE_CPU_OIDS = {
    "cisco": "1.3.6.1.4.1.9.9.109.1.1.1.1.8",
    "mikrotik": "1.3.6.1.4.1.14988.1.1.1.1.2",
    "fortinet": "1.3.6.1.4.1.12356.101.4.1.1",
    "huawei": "1.3.6.1.4.1.2011.5.25.31.1.1.1.1.5",
    "hpe_aruba": "1.3.6.1.4.1.11.2.14.1.1.2.1.1.5.9",
}

AUTH_PROTOCOLS = {
    "MD5": "usmHMACMD5AuthProtocol", "SHA": "usmHMACSHAAuthProtocol", "SHA224": "usmHMAC128SHA224AuthProtocol",
    "SHA256": "usmHMAC192SHA256AuthProtocol", "SHA384": "usmHMAC256SHA384AuthProtocol", "SHA512": "usmHMAC384SHA512AuthProtocol",
}
PRIV_PROTOCOLS = {"DES": "usmDESPrivProtocol", "AES": "usmAesCfb128Protocol", "AES192": "usmAesCfb192Protocol", "AES256": "usmAesCfb256Protocol"}


class SNMPCollector:
    def __init__(self) -> None:
        self.engine = hlapi.SnmpEngine()
        self.counters: dict[str, tuple[float, float]] = {}

    def close(self) -> None:
        self.engine.close_dispatcher()

    @staticmethod
    def _auth(config: dict):
        if config["version"] != "3":
            return hlapi.CommunityData(config.get("community", "public"), mpModel=0 if config["version"] == "1" else 1)
        v3 = config.get("v3", {})
        return hlapi.UsmUserData(
            v3.get("user", ""), v3.get("auth_key") or None, v3.get("priv_key") or None,
            authProtocol=getattr(hlapi, AUTH_PROTOCOLS[v3.get("auth_proto", "SHA")]) if v3.get("auth_key") else hlapi.usmNoAuthProtocol,
            privProtocol=getattr(hlapi, PRIV_PROTOCOLS[v3.get("priv_proto", "AES")]) if v3.get("priv_key") else hlapi.usmNoPrivProtocol,
        )

    @staticmethod
    async def _target(hostname: str, config: dict):
        return await hlapi.UdpTransportTarget.create((hostname, config.get("port", 161)), timeout=config.get("walk_timeout_sec", 2), retries=1)

    async def _get(self, auth, target, oid: str) -> Any | None:
        if isinstance(auth, SNMPBerClient):
            return await auth.get(oid)
        error, status, _, var_binds = await hlapi.get_cmd(self.engine, auth, target, hlapi.ContextData(), hlapi.ObjectType(hlapi.ObjectIdentity(oid)), lookupMib=False)
        if error or status or not var_binds:
            return None
        value = var_binds[0][1]
        try:
            return int(value)
        except (TypeError, ValueError):
            return value.prettyPrint()

    async def _walk(self, auth, target, oid: str) -> dict[tuple[int, ...], Any]:
        if isinstance(auth, SNMPBerClient):
            return await auth.walk(oid)
        result: dict[tuple[int, ...], Any] = {}
        base = tuple(int(part) for part in oid.split("."))
        if getattr(auth, "message_processing_model", 1) == 0:
            current = hlapi.ObjectType(hlapi.ObjectIdentity(oid))
            for _ in range(5000):
                error, status, _, var_binds = await hlapi.next_cmd(self.engine, auth, target, hlapi.ContextData(), current, lexicographicMode=False, lookupMib=False)
                if error or status or not var_binds:
                    break
                name, value = var_binds[0]
                full = tuple(int(part) for part in name.prettyPrint().strip(".").split("."))
                if full[:len(base)] != base or len(full) == len(base):
                    break
                try:
                    result[full[len(base):]] = int(value)
                except (TypeError, ValueError):
                    result[full[len(base):]] = value.prettyPrint()
                current = hlapi.ObjectType(name)
            return result
        async for error, status, _, var_binds in hlapi.bulk_walk_cmd(self.engine, auth, target, hlapi.ContextData(), 0, 20, hlapi.ObjectType(hlapi.ObjectIdentity(oid)), lexicographicMode=False, lookupMib=False):
            if error or status:
                break
            for name, value in var_binds:
                full = tuple(int(part) for part in name.prettyPrint().strip(".").split("."))
                if full[:len(base)] != base or len(full) == len(base):
                    continue
                try:
                    result[full[len(base):]] = int(value)
                except (TypeError, ValueError):
                    result[full[len(base):]] = value.prettyPrint()
        return result

    def _rate(self, key: str, value: int, now: float, bits: int = 64) -> float | None:
        previous = self.counters.get(key)
        self.counters[key] = (value, now)
        if previous is None or now <= previous[1]:
            return None
        delta = value - previous[0]
        if delta < 0:
            delta = value if bits == 64 else (1 << bits) - previous[0] + value
        return max(0.0, delta / (now - previous[1]))

    async def collect(self, hostname: str, config: dict) -> dict[str, Any]:
        import asyncio
        now = time.time()
        version = str(config.get("version", "2c"))
        if version in ("1", "2c"):
            auth = SNMPBerClient(hostname, version, config.get("community", "public"), config.get("port", 161), config.get("walk_timeout_sec", 2), retries=1)
            target = None
        else:
            auth = self._auth(config)
            target = await self._target(hostname, config)
        metrics: list[dict[str, Any]] = []
        details: dict[str, Any] = {"interfaces": [], "storage": [], "identity": {}, "processes": {"cpu": [], "memory": []}}

        def add(key: str, value: float | int | None, unit: str, resource: str = "") -> None:
            metrics.append({"key": key, "value": value, "unit": unit, "resource_key": resource})

        sys_name, sys_descr, uptime = await asyncio.gather(
            self._get(auth, target, "1.3.6.1.2.1.1.5.0"),
            self._get(auth, target, "1.3.6.1.2.1.1.1.0"),
            self._get(auth, target, "1.3.6.1.2.1.1.3.0"),
        )
        details["identity"] = {"sys_name": sys_name, "sys_descr": sys_descr, "sys_uptime_ticks": uptime}
        if not sys_name and not sys_descr and uptime is None:
            raise ConnectionError("No SNMP response")
        if isinstance(uptime, int):
            uptime_sec = uptime / 100
            add("system.uptime_sec", uptime_sec, "seconds")
            boot_time = now - uptime_sec
        else:
            boot_time = None

        cpu_count = 1
        if config.get("oid_profile") == "linux_snmpd":
            cpu_rows = await self._walk(auth, target, "1.3.6.1.2.1.25.3.3.1.2")
            cpu_values = [v for v in cpu_rows.values() if isinstance(v, int)]
            if cpu_values:
                cpu_count = len(cpu_values)
                for index, value in enumerate(cpu_values):
                    add("cpu.core_pct", value, "%", f"cpu:{index}")
                add("cpu.total_pct", sum(cpu_values) / len(cpu_values), "%")

        if config.get("oid_profile") in ("windows_snmp", "linux_snmpd"):
            bases = {"descr": "1.3.6.1.2.1.25.2.3.1.3", "type": "1.3.6.1.2.1.25.2.3.1.2", "units": "1.3.6.1.2.1.25.2.3.1.4", "size": "1.3.6.1.2.1.25.2.3.1.5", "used": "1.3.6.1.2.1.25.2.3.1.6"}
            tables = await asyncio.gather(*(self._walk(auth, target, oid) for oid in bases.values()))
            columns = dict(zip(bases, tables))
            for index, descr in columns["descr"].items():
                storage_type = str(columns["type"].get(index, ""))
                units, size, used = (columns[key].get(index, 0) for key in ("units", "size", "used"))
                total_bytes, used_bytes = int(units) * int(size), int(units) * int(used)
                name = str(descr).strip()
                details["storage"].append({"name": name, "type_oid": storage_type, "total_bytes": total_bytes, "used_bytes": used_bytes})
                kind = {"1.3.6.1.2.1.25.2.1.2": "ram", "1.3.6.1.2.1.25.2.1.3": "swap", "1.3.6.1.2.1.25.2.1.4": "disk"}.get(storage_type)
                if kind == "ram" and total_bytes:
                    add("ram.used_bytes", used_bytes, "bytes")
                    add("ram.total_bytes", total_bytes, "bytes")
                    add("ram.used_pct", 100 * used_bytes / total_bytes, "%")
                elif kind == "swap" and total_bytes:
                    add("swap.used_pct", 100 * used_bytes / total_bytes, "%")
                elif kind == "disk" and total_bytes:
                    key = resource_key("disk", name)
                    add("disk.used_pct", 100 * used_bytes / total_bytes, "%", key)
                    add("disk.used_bytes", used_bytes, "bytes", key)
                    add("disk.total_bytes", total_bytes, "bytes", key)

            process_names, process_cpu, process_memory = await asyncio.gather(
                self._walk(auth, target, "1.3.6.1.2.1.25.4.2.1.2"),
                self._walk(auth, target, "1.3.6.1.2.1.25.5.1.1.1"),
                self._walk(auth, target, "1.3.6.1.2.1.25.5.1.1.2"),
            )
            processes = []
            for index, name in process_names.items():
                cpu_ticks = process_cpu.get(index)
                memory_kb = process_memory.get(index)
                cpu_pct = self._rate(f"{hostname}:process:{name}", cpu_ticks, now, 32) / max(1, cpu_count) if isinstance(cpu_ticks, int) else 0.0
                processes.append({"pid": index[-1], "name": str(name).strip(), "user": None, "cpu_pct": round(cpu_pct, 1), "memory_mb": round(int(memory_kb or 0) / 1024, 1)})
            details["processes"] = {"cpu": sorted(processes, key=lambda row: row["cpu_pct"], reverse=True)[:10], "memory": sorted(processes, key=lambda row: row["memory_mb"], reverse=True)[:10]}

        if config.get("oid_profile") == "mikrotik":
            base = "1.3.6.1.4.1.14988.1.1.1"
            used_bytes, total_bytes = await asyncio.gather(self._get(auth, target, base + ".3.0"), self._get(auth, target, base + ".4.0"))
            if used_bytes is None:
                used_bytes = await self._get(auth, target, base + ".3")
            if total_bytes is None:
                total_bytes = await self._get(auth, target, base + ".4")
            if isinstance(used_bytes, int) and isinstance(total_bytes, int) and total_bytes > 0:
                add("ram.used_bytes", used_bytes, "bytes")
                add("ram.total_bytes", total_bytes, "bytes")
                add("ram.used_pct", 100 * used_bytes / total_bytes, "%")

        columns = {
            "name": "1.3.6.1.2.1.31.1.1.1.1", "in64": "1.3.6.1.2.1.31.1.1.1.6", "out64": "1.3.6.1.2.1.31.1.1.1.10",
            "speed": "1.3.6.1.2.1.31.1.1.1.15", "status": "1.3.6.1.2.1.2.2.1.8", "errin": "1.3.6.1.2.1.2.2.1.14", "errout": "1.3.6.1.2.1.2.2.1.20",
            "dropin": "1.3.6.1.2.1.2.2.1.13", "dropout": "1.3.6.1.2.1.2.2.1.19",
        }
        tables = await asyncio.gather(*(self._walk(auth, target, oid) for oid in columns.values()))
        interface_data = dict(zip(columns, tables))
        counter_bits = 64
        if not interface_data["in64"]:
            old_in, old_out = await asyncio.gather(self._walk(auth, target, "1.3.6.1.2.1.2.2.1.10"), self._walk(auth, target, "1.3.6.1.2.1.2.2.1.16"))
            interface_data["in64"], interface_data["out64"] = old_in, old_out
            counter_bits = 32
        if not interface_data["name"]:
            interface_data["name"] = await self._walk(auth, target, "1.3.6.1.2.1.2.2.1.2")
        if not interface_data["speed"]:
            interface_data["speed"] = {key: value / 1_000_000 for key, value in (await self._walk(auth, target, "1.3.6.1.2.1.2.2.1.5")).items() if isinstance(value, int)}
        excluded = set(config.get("if_exclude", []))
        for index, name in interface_data["name"].items():
            interface_name = str(name).strip()
            if interface_name in excluded or interface_data["status"].get(index) == 2:
                continue
            key = resource_key("nic", interface_name)
            rx = interface_data["in64"].get(index)
            tx = interface_data["out64"].get(index)
            rx_bytes_sec = self._rate(f"{hostname}:{interface_name}:rx", rx, now, counter_bits) if isinstance(rx, int) else None
            tx_bytes_sec = self._rate(f"{hostname}:{interface_name}:tx", tx, now, counter_bits) if isinstance(tx, int) else None
            error_rates = [self._rate(f"{hostname}:{interface_name}:{field}", interface_data[field][index], now, 32) if isinstance(interface_data[field].get(index), int) else None for field in ("errin", "errout")]
            drop_rates = [self._rate(f"{hostname}:{interface_name}:{field}", interface_data[field][index], now, 32) if isinstance(interface_data[field].get(index), int) else None for field in ("dropin", "dropout")]
            errors = sum(error_rates) if all(rate is not None for rate in error_rates) else None
            drops = sum(drop_rates) if all(rate is not None for rate in drop_rates) else None
            details["interfaces"].append({"name": interface_name, "status": interface_data["status"].get(index), "speed_mbps": interface_data["speed"].get(index), "rx_bps": rx_bytes_sec, "tx_bps": tx_bytes_sec, "errors_per_sec": errors, "drops_per_sec": drops})
            add("net.rx_bps", None if rx_bytes_sec is None else rx_bytes_sec * 8, "bps", key)
            add("net.tx_bps", None if tx_bytes_sec is None else tx_bytes_sec * 8, "bps", key)
            add("net.error_rate", errors, "errors/s", key)
            add("net.drop_rate", drops, "drops/s", key)

        add("tcp.established", await self._get(auth, target, "1.3.6.1.2.1.6.9.0"), "connections")
        vendor_oid = config.get("cpu_vendor_oid") or PROFILE_CPU_OIDS.get(config.get("oid_profile"))
        if vendor_oid:
            vendor_cpu = await self._get(auth, target, vendor_oid)
            if vendor_cpu is None:
                rows = await self._walk(auth, target, vendor_oid)
                values = [value for value in rows.values() if isinstance(value, int)]
                vendor_cpu = sum(values) / len(values) if values else None
            if isinstance(vendor_cpu, int):
                add("cpu.total_pct", vendor_cpu, "%")
            elif isinstance(vendor_cpu, float):
                add("cpu.total_pct", vendor_cpu, "%")
        return {"ts": now, "status": "up", "status_reason": "SNMP response received", "os_info": str(sys_descr or "SNMP device"), "boot_time": boot_time, "metrics": metrics, "details": details}
