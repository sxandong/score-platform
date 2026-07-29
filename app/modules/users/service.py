"""Users 模块业务逻辑"""
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User, Role, user_roles
from app.core.security import hash_password, verify_password
from app.core.exceptions import NotFoundException, ValidationException


async def list_users_service(
    db: AsyncSession, page: int = 1, per_page: int = 20,
    keyword: str | None = None, role: str | None = None, status: str | None = None,
) -> tuple[list[User], int]:
    query = select(User).options(selectinload(User.roles))

    if keyword:
        kw = f"%{keyword}%"
        query = query.where(or_(
            User.username.ilike(kw),
            User.real_name.ilike(kw),
            User.phone.ilike(kw),
            User.email.ilike(kw),
        ))

    if status:
        query = query.where(User.status == status)

    if role:
        query = query.join(user_roles, User.id == user_roles.c.user_id)\
            .join(Role, Role.id == user_roles.c.role_id)\
            .where(Role.code == role)

    query = query.order_by(User.id.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    result = await db.execute(query)
    users = result.scalars().all()

    return list(users), total


async def get_user_service(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundException("用户不存在")
    return user


async def create_user_service(db: AsyncSession, data) -> User:
    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        real_name=data.real_name,
        phone=data.phone,
        email=data.email,
        must_change_password=True,
    )
    db.add(user)
    await db.flush()

    if data.role_codes:
        result = await db.execute(select(Role).where(Role.code.in_(data.role_codes)))
        for role in result.scalars().all():
            await db.execute(user_roles.insert().values(user_id=user.id, role_id=role.id))

    await db.flush()
    result = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user.id))
    return result.scalar_one()


async def update_user_service(db: AsyncSession, user_id: int, data) -> User:
    user = await get_user_service(db, user_id)

    if data.real_name is not None:
        user.real_name = data.real_name
    if data.phone is not None:
        user.phone = data.phone
    if data.email is not None:
        user.email = data.email
    if data.status is not None:
        user.status = data.status

    if data.role_codes is not None:
        await db.execute(user_roles.delete().where(user_roles.c.user_id == user_id))
        if data.role_codes:
            result = await db.execute(select(Role).where(Role.code.in_(data.role_codes)))
            for role in result.scalars().all():
                await db.execute(user_roles.insert().values(user_id=user.id, role_id=role.id))

    await db.flush()
    result = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user_id))
    return result.scalar_one()


async def reset_password_service(db: AsyncSession, user_id: int) -> None:
    user = await get_user_service(db, user_id)
    user.password_hash = hash_password("123456")
    user.must_change_password = True
    await db.flush()


async def batch_reset_password_service(db: AsyncSession, user_ids: list[int]) -> int:
    hashed = hash_password("123456")
    result = await db.execute(
        select(User).where(User.id.in_(user_ids))
    )
    users = result.scalars().all()
    count = 0
    for user in users:
        user.password_hash = hashed
        user.must_change_password = True
        count += 1
    await db.flush()
    return count


async def change_password_service(
    db: AsyncSession, user_id: int, old_password: str, new_password: str
) -> None:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundException("用户不存在")
    if not verify_password(old_password, user.password_hash):
        raise ValidationException("原密码错误")
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    await db.flush()


async def delete_user_service(db: AsyncSession, user_id: int) -> None:
    user = await get_user_service(db, user_id)
    if user.username == "admin":
        raise ValidationException("不能删除管理员账号")
    user.roles = []
    await db.delete(user)
    await db.commit()


async def batch_delete_users_service(db: AsyncSession, user_ids: list[int]) -> int:
    result = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.id.in_(user_ids))
    )
    users = result.scalars().all()
    count = 0
    for user in users:
        if user.username == "admin":
            continue
        user.roles = []
        await db.delete(user)
        count += 1
    await db.commit()
    return count
