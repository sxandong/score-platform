"""Users 模块 Pydantic schemas"""
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    real_name: str = Field(..., min_length=1, max_length=50)
    phone: str = ""
    email: str = ""
    role_codes: list[str] = []


class UserUpdate(BaseModel):
    real_name: str | None = None
    phone: str | None = None
    email: str | None = None
    status: str | None = None
    role_codes: list[str] | None = None
