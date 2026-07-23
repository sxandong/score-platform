"""Users 模块业务逻辑"""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User, Role, user_roles
from app.core.security import hash_password
from app.core.exceptions import NotFoundException


async def list_users_service(db: AsyncSession, page: int = 1, per_page: int = 20) -> tuple[list[User], int]:
    offset = (page - 1) * per_page
    result = await db.execute(
        select(User).options(selectinload(User.roles))
        .order_by(User.id.desc()).offset(offset).limit(per_page)
    )
    users = result.scalars().all()

    result = await db.execute(select(func.count(User.id)))
    total = result.scalar_one()

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
    )
    db.add(user)
    await db.flush()

    if data.role_codes:
        result = await db.execute(select(Role).where(Role.code.in_(data.role_codes)))
        for role in result.scalars().all():
            await db.execute(user_roles.insert().values(user_id=user.id, role_id=role.id))

    await db.flush()
    return user


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
    return user
