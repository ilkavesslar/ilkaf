from __future__ import annotations

import os

os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["API_CORS_ORIGINS"] = "http://localhost:5173"
