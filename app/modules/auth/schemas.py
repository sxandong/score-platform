"""Auth 模块 Pydantic schemas"""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class RefreshRequest(BaseModel):
    refresh_token: str
