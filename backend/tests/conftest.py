"""pytest configuration — loaded automatically by pytest."""

import os
from pathlib import Path

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/14")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/15")
os.environ.setdefault("RUNNER_IMAGE", "sha256:" + "a" * 64)

_VERSION_FILE = Path(__file__).resolve().parents[2] / ".klee-version"
_KLEE_VERSION = _VERSION_FILE.read_text().strip()
os.environ.setdefault("KLEE_VERSION", _KLEE_VERSION)
