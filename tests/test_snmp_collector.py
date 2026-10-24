from noc.collectors.snmp_collector import PROFILE_CPU_OIDS, SNMPCollector


def test_counter_rates_cover_counter64_and_32_bit_wrap():
    collector = SNMPCollector()
    assert collector._rate("large", 0, 100) is None
    assert collector._rate("large", 30_000_000_000, 110) * 8 == 24_000_000_000
    collector._rate("old", (1 << 32) - 5, 100, 32)
    assert collector._rate("old", 5, 102, 32) == 5
    collector.close()


def test_network_profiles_have_vendor_cpu_oid_templates():
    assert all(profile in PROFILE_CPU_OIDS for profile in ("cisco", "mikrotik", "fortinet", "huawei", "hpe_aruba"))
