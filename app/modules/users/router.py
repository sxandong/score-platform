"""Users 模块路由"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.core.security import require_role
from app.core.response import success_response, paginated_response
from app.modules.users.schemas import UserCreate, UserUpdate
from app.modules.users import service

router = APIRouter(prefix="/api/users", tags=["用户管理"])


def _user_to_dict(user) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "phone": user.phone or "",
        "email": user.email or "",
        "status": user.status,
        "roles": user.role_codes,
        "created_at": user.created_at.isoformat() if user.created_at else "",
    }


@router.get("")
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    users, total = await service.list_users_service(db, page, per_page)
    return paginated_response(
        items=[_user_to_dict(u) for u in users],
        total=total, page=page, per_page=per_page,
    )


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    user = await service.get_user_service(db, user_id)
    return success_response(data=_user_to_dict(user))


@router.post("")
async def create_user(
    req: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    user = await service.create_user_service(db, req)
    return success_response(data=_user_to_dict(user), message="用户创建成功")


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    req: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    user = await service.update_user_service(db, user_id, req)
    return success_response(data=_user_to_dict(user), message="用户更新成功")
