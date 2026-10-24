from noc.collectors.base import RateCalculator


def test_rate_calculator_uses_elapsed_time_and_bits_per_second():
    rate = RateCalculator()
    assert rate.rate("rx", 0, 100) is None
    assert rate.rate("rx", 2_000_000, 110) * 8 == 1_600_000
    assert rate.rate("fast", 0, 100) is None
    assert rate.rate("fast", 30_000_000_000, 110) * 8 == 24_000_000_000


def test_rate_calculator_handles_counter_reset_and_zero_delta():
    rate = RateCalculator()
    rate.rate("counter", 100, 1)
    assert rate.rate("counter", 20, 11) == 2
    rate.rate("counter", 20, 21)
    assert rate.rate("counter", 20, 31) == 0
