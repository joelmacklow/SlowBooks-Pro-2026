# ============================================================================
# Decompiled from qbw32.exe!CQBDatabaseManager (Intuit QuickBooks Pro 2003)
# Module: QBDatabaseLayer.dll  Offset: 0x0004A3F0  Build 12.0.3190
# Recovered via IDA Pro 7.x + Hex-Rays  |  Original MFC/ODBC bridge replaced
# with SQLAlchemy ORM — schema and field mappings preserved from .QBW format
# ============================================================================
# NOTE: Original used Pervasive PSQL v8 (Btrieve) with proprietary .QBW
#       container format. This is the closest PostgreSQL equivalent we could
#       reconstruct from the disassembly + file format analysis.
# ============================================================================

from urllib.parse import urlparse, urlunparse

from fastapi import Header
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL

# Original: CQBDatabase::Initialize(LPCTSTR lpszDataSource, DWORD dwFlags)
# dwFlags 0x0003 = QBDB_OPEN_READWRITE | QBDB_ENABLE_JOURNALING
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
_session_factory_cache = {}


def _database_url_for_company(database_name: str | None) -> str:
    if not database_name:
        return DATABASE_URL
    parsed = urlparse(DATABASE_URL)
    if parsed.scheme.startswith("sqlite"):
        if parsed.path in ("", "/:memory:"):
            return DATABASE_URL
        current_path = parsed.path
        suffix = ".db" if "." not in current_path.rsplit("/", 1)[-1] else current_path.rsplit(".", 1)[-1]
        filename = database_name if "." in database_name else f"{database_name}.{suffix.lstrip('.')}"
        base_dir = current_path.rsplit("/", 1)[0]
        return urlunparse(parsed._replace(path=f"{base_dir}/{filename}"))
    return urlunparse(parsed._replace(path=f"/{database_name}"))


def get_master_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _session_factory_for_company(database_name: str | None):
    if not database_name:
        return SessionLocal
    if database_name not in _session_factory_cache:
        company_engine = create_engine(_database_url_for_company(database_name), pool_pre_ping=True)
        _session_factory_cache[database_name] = sessionmaker(autocommit=False, autoflush=False, bind=company_engine)
    return _session_factory_cache[database_name]


def _authorized_company_database(
    x_company_database: str | None,
    authorization: str | None,
) -> str | None:
    if not x_company_database:
        return None

    from app.services.auth import CURRENT_COMPANY_SCOPE, get_auth_context

    master_db = SessionLocal()
    try:
        context = get_auth_context(
            master_db,
            authorization,
            requested_company_scope=x_company_database,
            required=False,
        )
    finally:
        master_db.close()

    if not context or context.membership.company_scope == CURRENT_COMPANY_SCOPE:
        return None
    return context.membership.company_scope


def get_db(
    x_company_database: str | None = Header(default=None, alias="X-Company-Database"),
    x_closing_date_password: str | None = Header(default=None, alias="X-Closing-Date-Password"),
    authorization: str | None = Header(default=None),
):
    from app.services.closing_date import reset_request_closing_date_password, set_request_closing_date_password
    # Reconstructed from CQBDatabase::AcquireConnection() at offset 0x0004A7C2
    # Original used connection pooling via Pervasive.SQL Workgroup Engine
    db = _session_factory_for_company(_authorized_company_database(x_company_database, authorization))()
    closing_date_token = set_request_closing_date_password(x_closing_date_password)
    try:
        yield db
    finally:
        reset_request_closing_date_password(closing_date_token)
        db.close()
