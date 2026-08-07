"""应用启动入口"""
import logging
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.core.database import engine, Base, async_session_factory
from app.core.exceptions import AppException
from app.core.response import error_response
from app.core.rate_limit import limiter, init_limiter
from app.core.seed import run_all_seeds

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)


async def auto_migrate():
    """自动迁移：检查并添加新字段"""
    from sqlalchemy import text, inspect as sa_inspect
    try:
        async with engine.begin() as conn:
            # 检查 users 表是否有 dingtalk_union_id 字段
            if settings.DATABASE_IS_SQLITE:
                result = await conn.execute(text("PRAGMA table_info(users)"))
                columns = {row[1] for row in result.fetchall()}
            else:
                result = await conn.execute(text("SHOW COLUMNS FROM users"))
                columns = {row[0] for row in result.fetchall()}

            if "dingtalk_union_id" not in columns:
                logger.info("Migrating: adding dingtalk_union_id column to users table")
                if settings.DATABASE_IS_SQLITE:
                    await conn.execute(text(
                        "ALTER TABLE users ADD COLUMN dingtalk_union_id VARCHAR(100) DEFAULT ''"
                    ))
                else:
                    await conn.execute(text(
                        "ALTER TABLE users ADD COLUMN dingtalk_union_id VARCHAR(100) DEFAULT ''"
                    ))
                logger.info("Migration: dingtalk_union_id column added successfully")
    except Exception as e:
        logger.warning(f"Auto migration failed (may be safe to ignore): {e}")


async def init_database():
    """确保数据库表和数据在应用启动前就绪"""
    logger.info("Initializing database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Tables created.")

    # 自动迁移：检查并添加新字段
    await auto_migrate()

    async with async_session_factory() as db:
        await run_all_seeds(db)
    logger.info("Seed data loaded.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_limiter(app)
    await init_database()
    yield
    await engine.dispose()


app = FastAPI(
    title="成绩管理与分析平台",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(
    429,
    lambda request, exc: JSONResponse(
        content={"code": 429, "message": "请求过于频繁，请稍后重试"},
        status_code=429,
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        content={"code": exc.code, "message": exc.message, "data": exc.data},
        status_code=exc.code,
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    import traceback
    detail = traceback.format_exc()
    logger.error(f"[ERROR 500] {request.method} {request.url.path}\n{detail}")
    if settings.DEBUG:
        message = f"服务器内部错误: {str(exc)}"
        data = {"error_type": type(exc).__name__}
    else:
        message = "服务器内部错误"
        data = None
    return JSONResponse(
        content={"code": 500, "message": message, "data": data},
        status_code=500,
    )


@app.get("/")
async def root():
    return RedirectResponse(url="/api/docs")


@app.get("/health")
async def health_check():
    return JSONResponse(content={
        "status": "ok",
        "version": "0.1.0",
        "database": "connected",
        "debug": settings.DEBUG,
    })


# Register module routers
from app.modules.auth.router import router as auth_router
app.include_router(auth_router)

from app.modules.users.router import router as users_router
app.include_router(users_router)

from app.modules.exams.router import router as exams_router
app.include_router(exams_router)

from app.modules.scores.router import router as scores_router
app.include_router(scores_router)

from app.modules.analysis.router import router as analysis_router
app.include_router(analysis_router)

from app.modules.reports.router import router as reports_router
app.include_router(reports_router)

from app.modules.system_router import router as sys_router
app.include_router(sys_router)

from app.modules.base_data_router import router as base_data_router
app.include_router(base_data_router)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
