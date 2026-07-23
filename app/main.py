"""应用启动入口"""
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.database import engine, Base, async_session_factory
from app.core.exceptions import AppException
from app.core.seed import run_all_seeds


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session_factory() as db:
        await run_all_seeds(db)
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


# Register module routers
from app.modules.auth.router import router as auth_router
app.include_router(auth_router)

from app.modules.users.router import router as users_router
app.include_router(users_router)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
