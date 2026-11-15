"""SQLAlchemy engine, session factory, and declarative Base.

The engine implementation lives in ``app.core.db`` so existing Sprint 0
callers keep working. Later models should subclass ``Base`` and use
``get_db_session`` for FastAPI injection.

Future migrations may add Camera, Zone, Person, Vehicle, Detection,
SafetyEvent, PPEViolation, RestrictedZoneViolation, ProximityViolation,
and Alert. Those tables are not defined in Sprint 1 beyond the existing
identity foundation (User, AuditLog, and related tables).
"""

from app.core.db import (
    check_database,
    configure_database,
    get_db_session,
    get_engine,
    session_scope,
)
from app.models.base import Base

__all__ = [
    "Base",
    "check_database",
    "configure_database",
    "get_db_session",
    "get_engine",
    "session_scope",
]
