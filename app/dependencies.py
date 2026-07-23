"""FastAPI 依赖注入"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """每个请求获取独立数据库会话"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
