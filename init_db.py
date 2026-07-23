"""数据库初始化脚本 — 在启动 uvicorn 之前运行一次"""
import asyncio
from app.core.database import engine, Base, async_session_factory
from app.core.seed import run_all_seeds


async def main():
    print("Creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully.")

    print("Loading seed data...")
    async with async_session_factory() as db:
        await run_all_seeds(db)
    print("Seed data loaded successfully.")

    print("\nDatabase initialized. Default admin: admin / admin123")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
