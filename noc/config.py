from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("NOC_DATA_DIR", ROOT / "data"))
STATIC_DIR = Path(__file__).resolve().parent / "static"
DB_PATH = DATA_DIR / "noc.db"
HOST = os.getenv("NOC_HOST", "0.0.0.0")
PORT = int(os.getenv("NOC_PORT", "8080"))
POLL_INTERVAL_SEC = max(5, int(os.getenv("NOC_POLL_INTERVAL_SEC", "15")))
TIMEOUT_FACTOR = max(2, int(os.getenv("NOC_TIMEOUT_FACTOR", "3")))
RAW_RETENTION_DAYS = max(1, int(os.getenv("NOC_RAW_RETENTION_DAYS", "7")))
HOURLY_RETENTION_DAYS = max(30, int(os.getenv("NOC_HOURLY_RETENTION_DAYS", "365")))
MAX_CONCURRENT_POLLS = max(1, int(os.getenv("NOC_MAX_CONCURRENT_POLLS", "32")))
