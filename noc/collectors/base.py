from __future__ import annotations

import time


class RateCalculator:
    """Convert cumulative counters to per-second rates using actual elapsed time."""

    def __init__(self) -> None:
        self._previous: dict[str, tuple[float, float]] = {}

    def rate(self, key: str, counter: float, timestamp: float | None = None) -> float | None:
        now = time.time() if timestamp is None else timestamp
        previous = self._previous.get(key)
        self._previous[key] = (counter, now)
        if previous is None:
            return None
        old_counter, old_time = previous
        elapsed = now - old_time
        if elapsed <= 0:
            return None
        delta = counter - old_counter
        if delta < 0:
            delta = counter
        return max(0.0, delta / elapsed)
