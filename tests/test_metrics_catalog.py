from noc.db import DEFAULT_RULES
from noc.metrics_catalog import CATALOG, resource_key


def test_default_rules_reference_catalog_metrics_and_supported_hosts():
    for _, metric, *_ in DEFAULT_RULES:
        assert metric in CATALOG
        assert CATALOG[metric]["applies_to"]
        assert set(CATALOG[metric]["applies_to"]) <= {"local", "agent", "snmp", "ping_http"}


def test_resource_keys_are_stable_for_windows_volumes():
    assert resource_key("disk", "c:\\") == "disk:C:"
    assert resource_key("svc", " Spooler ") == "svc:Spooler"
