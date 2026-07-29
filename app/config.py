"""应用配置 (Pydantic BaseSettings, reads .env)"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "成绩管理与分析平台"
    DEBUG: bool = True

    # Database — set DB_TYPE=sqlite for local dev without MySQL
    DB_TYPE: str = "sqlite"   # "mysql" | "sqlite"
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "score123"
    DB_NAME: str = "score_platform"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40

    @property
    def DATABASE_URL(self) -> str:
        if self.DB_TYPE == "sqlite":
            return "sqlite+aiosqlite:///admission_data.db"
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def DATABASE_IS_SQLITE(self) -> bool:
        return self.DB_TYPE == "sqlite"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def CELERY_BROKER_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/1"

    JWT_SECRET: str = "dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def CORS_ORIGINS_LIST(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    RATE_LIMIT_LOGIN: str = "5/minute"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
