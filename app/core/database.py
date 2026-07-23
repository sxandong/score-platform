"""异步数据库引擎与会话管理"""
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool
from app.config import settings


class Base(DeclarativeBase):
    pass


_engine_kwargs: dict = {"echo": settings.DEBUG}
if not settings.DATABASE_IS_SQLITE:
    _engine_kwargs.update({
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_pre_ping": True,
    })
else:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    _engine_kwargs["poolclass"] = StaticPool

engine: AsyncEngine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)


@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """启用 SQLite 外键约束和 WAL 模式"""
    if settings.DATABASE_IS_SQLITE:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
