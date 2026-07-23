"""JWT 认证 + RBAC 鉴权"""
from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.dependencies import get_db
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.models.user import User, Role

security_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: int, role_codes: list[str]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "roles": role_codes, "type": "access", "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "type": "refresh", "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise UnauthorizedException("请提供认证令牌")

    payload = verify_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise UnauthorizedException("令牌无效或已过期")

    user_id = int(payload["sub"])
    result = await db.execute(
        select(User).options(
            selectinload(User.roles).selectinload(Role.permissions)
        ).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None or user.status != "active":
        raise UnauthorizedException("用户不存在或已禁用")
    return user


def require_role(*roles: str):
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        user_role_codes = {r.code for r in current_user.roles}
        if not user_role_codes.intersection(roles):
            raise ForbiddenException(f"需要以下角色之一: {', '.join(roles)}")
        return current_user
    return checker


def require_permission(permission_code: str):
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        for role in current_user.roles:
            if permission_code in role.permission_codes:
                return current_user
        raise ForbiddenException(f"缺少权限: {permission_code}")
    return checker


async def get_teacher_class_ids(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> set[int] | None:
    user_role_codes = {r.code for r in current_user.roles}
    if "admin" in user_role_codes or "director" in user_role_codes:
        return None

    from app.models.base_data import Course
    result = await db.execute(
        select(Course.class_id).where(Course.teacher_id == current_user.id)
    )
    return {row[0] for row in result.all()}
