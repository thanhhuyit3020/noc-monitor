from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
VERSION = "1.0.1"
DATA_DIR = Path(os.getenv("NOC_DATA_DIR", ROOT / "data"))
STATIC_DIR = Path(__file__).resolve().parent / "static"
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
DB_PATH = DATA_DIR / "noc.db"
HOST = os.getenv("NOC_HOST", "127.0.0.1")
PORT = int(os.getenv("NOC_PORT", "6969"))
SESSION_TTL_SEC = min(86400, max(900, int(os.getenv("NOC_SESSION_TTL_SEC", "28800"))))
COOKIE_SECURE = os.getenv("NOC_COOKIE_SECURE", "0").lower() in {"1", "true", "yes"}
POLL_INTERVAL_SEC = max(5, int(os.getenv("NOC_POLL_INTERVAL_SEC", "15")))
TIMEOUT_FACTOR = max(2, int(os.getenv("NOC_TIMEOUT_FACTOR", "3")))
RAW_RETENTION_DAYS = max(1, int(os.getenv("NOC_RAW_RETENTION_DAYS", "7")))
HOURLY_RETENTION_DAYS = max(30, int(os.getenv("NOC_HOURLY_RETENTION_DAYS", "365")))
MAX_CONCURRENT_POLLS = max(1, int(os.getenv("NOC_MAX_CONCURRENT_POLLS", "32")))
