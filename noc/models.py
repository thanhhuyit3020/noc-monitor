from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, model_validator


HostType = Literal["local", "agent", "snmp", "ping_http"]
Port = Annotated[int, Field(ge=1, le=65535)]
HttpStatus = Annotated[int, Field(ge=100, le=599)]


class LocalConfig(BaseModel):
    windows_services: list[str] = Field(default_factory=lambda: [
        "EventLog", "LanmanServer", "Dnscache", "Winmgmt", "Schedule", "W32Time", "Spooler"
    ])
    tcp_ports: list[Port] = Field(default_factory=list)
    http_urls: list[str] = Field(default_factory=list)
    eventlog_channels: list[str] = Field(default_factory=lambda: ["System", "Application"])


class AgentConfig(BaseModel):
    mode: Literal["push", "pull"] = "push"
    pull_url: str | None = None
    port: int = Field(default=9108, ge=1, le=65535)
    agent_token: str = Field(min_length=1, max_length=256)
    windows_services: list[str] = Field(default_factory=list)
    tcp_ports: list[Port] = Field(default_factory=list)
    http_urls: list[str] = Field(default_factory=list)


class SNMPv3Config(BaseModel):
    user: str = ""
    auth_proto: Literal["MD5", "SHA", "SHA224", "SHA256", "SHA384", "SHA512"] = "SHA"
    auth_key: str = ""
    priv_proto: Literal["DES", "AES", "AES192", "AES256"] = "AES"
    priv_key: str = ""


class SNMPConfig(BaseModel):
    version: Literal["1", "2c", "3"] = "2c"
    port: int = Field(default=161, ge=1, le=65535)
    community: str = "public"
    v3: SNMPv3Config = Field(default_factory=SNMPv3Config)
    oid_profile: Literal[
        "windows_snmp", "linux_snmpd", "netgear_generic", "mikrotik", "cisco", "fortinet", "huawei", "hpe_aruba"
    ] = "netgear_generic"
    cpu_vendor_oid: str = ""
    if_exclude: list[str] = Field(default_factory=lambda: ["lo"])
    walk_timeout_sec: float = Field(default=2.0, ge=0.2, le=30)


class PingHTTPConfig(BaseModel):
    icmp: bool = True
    tcp_ports: list[Port] = Field(default_factory=list)
    http_urls: list[str] = Field(default_factory=list)
    expected_status: list[HttpStatus] = Field(default_factory=lambda: [200, 204, 301, 302])
    body_match: str | None = None
    ssl_check: bool = True
    ssl_warn_days: int = Field(default=30, ge=0)
    ssl_crit_days: int = Field(default=7, ge=0)


CONFIG_MODELS = {
    "local": LocalConfig,
    "agent": AgentConfig,
    "snmp": SNMPConfig,
    "ping_http": PingHTTPConfig,
}


class HostInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    hostname: str = Field(min_length=1, max_length=255)
    host_type: HostType
    poll_interval_sec: int = Field(default=15, ge=5, le=86400)
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_config(self):
        config_model = CONFIG_MODELS[self.host_type]
        self.config = config_model.model_validate(self.config).model_dump(mode="json")
        if self.host_type == "ping_http" and not (
            self.config["icmp"] or self.config["tcp_ports"] or self.config["http_urls"]
        ):
            raise ValueError("Configure ICMP, at least one TCP port, or at least one HTTP URL")
        if self.host_type == "agent" and self.config["mode"] == "pull" and not self.config.get("pull_url") and not self.hostname:
            raise ValueError("Pull mode requires a hostname or pull URL")
        return self


class RuleInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    metric_key: str
    operator: Literal[">", ">=", "<", "<=", "==", "!="] = ">"
    warning: float | None = None
    critical: float | None = None
    consecutive_polls: int = Field(default=1, ge=1, le=20)
    cooldown_sec: int = Field(default=300, ge=0)
    enabled: bool = True
    applies_to: list[HostType] = Field(default_factory=list)


class MetricSample(BaseModel):
    key: str
    value: float | int | None
    unit: str = ""
    resource_key: str = ""


class Snapshot(BaseModel):
    ts: float
    status: Literal["up", "down", "stale", "maintenance", "unknown"] = "up"
    status_reason: str = ""
    os_info: str = ""
    boot_time: float | None = None
    metrics: list[MetricSample] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
