"""Auth 模块业务逻辑"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import (
    verify_password, create_access_token, create_refresh_token, verify_token
)
from app.core.exceptions import UnauthorizedException
from app.models.user import User, Role


async def login_service(
    db: AsyncSession, username: str, password: str
) -> dict:
    result = await db.execute(
        select(User).options(
            selectinload(User.roles).selectinload(Role.permissions)
        ).where(User.username == username)
    )
    user = result.scalar_one_or_none()

    if user is None or user.status != "active":
        raise UnauthorizedException("用户名或密码错误")
    if not verify_password(password, user.password_hash):
        raise UnauthorizedException("用户名或密码错误")

    role_codes = user.role_codes
    permission_codes: list[str] = []
    for role in user.roles:
        permission_codes.extend(role.permission_codes)
    permission_codes = sorted(set(permission_codes))

    return {
        "access_token": create_access_token(user.id, role_codes),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "roles": role_codes,
            "permissions": permission_codes,
        },
    }


async def refresh_token_service(
    db: AsyncSession, refresh_token: str
) -> dict:
    payload = verify_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise UnauthorizedException("刷新令牌无效或已过期")

    user_id = int(payload["sub"])
    result = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None or user.status != "active":
        raise UnauthorizedException("用户不存在或已禁用")

    return {
        "access_token": create_access_token(user.id, user.role_codes),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
    }
