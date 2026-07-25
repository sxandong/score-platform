"""Users 模块路由"""
from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd
from io import BytesIO

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


@router.get("/download-template")  # 公开访问
async def download_template():
    """下载教师导入模板"""
    import pandas as pd
    from io import BytesIO
    df = pd.DataFrame(columns=["用户名", "姓名", "密码"])
    df.loc[0] = ["teacher01", "张老师", "123456"]
    df.loc[1] = ["teacher02", "李老师", ""]
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return StreamingResponse(output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=教师导入模板.xlsx"})


@router.post("/batch")
async def batch_import_users(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """Excel批量导入教师账号: 列=用户名,姓名[,密码]"""
    content = await file.read()
    try:
        df = pd.read_excel(BytesIO(content))
    except Exception as e:
        return success_response(data={}, message=f"Excel解析失败: {e}")

    from app.models.user import User, Role, user_roles
    from app.core.security import hash_password
    from sqlalchemy import select as sa_select

    result = await db.execute(sa_select(Role).where(Role.code == "teacher"))
    teacher_role = result.scalar_one_or_none()

    created, skipped = 0, 0
    for _, row in df.iterrows():
        username = str(row.get("用户名", row.get("username", ""))).strip()
        real_name = str(row.get("姓名", row.get("name", row.get("real_name", "")))).strip()
        if not username or not real_name:
            skipped += 1; continue

        # 检查是否已存在
        result = await db.execute(sa_select(User).where(User.username == username))
        if result.scalar_one_or_none():
            skipped += 1; continue

        pwd = str(row.get("密码", row.get("password", "123456"))).strip()
        user = User(username=username, password_hash=hash_password(pwd),
                    real_name=real_name)
        db.add(user)
        await db.flush()
        if teacher_role:
            await db.execute(user_roles.insert().values(
                user_id=user.id, role_id=teacher_role.id))
        created += 1

    await db.flush()
    return success_response(data={"created": created, "skipped": skipped},
        message=f"导入完成: 新增{created}个教师, 跳过{skipped}个")
