"""应用启动入口"""
from contextlib import asynccontextmanager
import asyncio
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.database import engine, Base, async_session_factory
from app.core.exceptions import AppException
from app.core.seed import run_all_seeds


async def init_database():
    """确保数据库表和数据在应用启动前就绪"""
    print("Initializing database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created.")
    async with async_session_factory() as db:
        await run_all_seeds(db)
    print("Seed data loaded.")


@asynccontextmanager
async def lifespan(app: FastAPI):
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        content={"code": exc.code, "message": exc.message, "data": exc.data},
        status_code=200,
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    import traceback
    detail = traceback.format_exc()
    print(f"\n[ERROR 500] {request.method} {request.url.path}")
    print(detail)
    return JSONResponse(
        content={
            "code": 500,
            "message": f"服务器内部错误: {str(exc)}",
            "data": {"error_type": type(exc).__name__},
        },
        status_code=200,
    )


@app.get("/")
async def root():
    return RedirectResponse(url="/api/docs")


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

from app.modules.base_data_router import router as base_data_router
app.include_router(base_data_router)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
