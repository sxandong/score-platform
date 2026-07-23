"""Auth 模块路由"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.core.security import get_current_user
from app.core.response import success_response
from app.modules.auth.schemas import LoginRequest, RefreshRequest
from app.modules.auth.service import login_service, refresh_token_service

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await login_service(db, req.username, req.password)
    return success_response(data=result, message="登录成功")


@router.post("/refresh")
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    result = await refresh_token_service(db, req.refresh_token)
    return success_response(data=result, message="令牌已刷新")


@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    permission_codes: list[str] = []
    for role in current_user.roles:
        permission_codes.extend(role.permission_codes)

    return success_response(data={
        "id": current_user.id,
        "username": current_user.username,
        "real_name": current_user.real_name,
        "roles": current_user.role_codes,
        "permissions": sorted(set(permission_codes)),
    })
