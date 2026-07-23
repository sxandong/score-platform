"""数据库种子数据 — 默认角色、权限、管理员账号、科目"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, Role, Permission, user_roles, role_permissions
from app.models.base_data import Subject
from app.core.security import hash_password

ROLE_PERMISSION_MAP = {
    "admin": [
        "user:create", "user:read", "user:update", "user:delete",
        "exam:create", "exam:read", "exam:update", "exam:delete",
        "score:create", "score:read", "score:update", "score:delete", "score:export",
        "analysis:view", "report:export", "system:config",
    ],
    "director": [
        "exam:read", "score:read", "score:update",
        "analysis:view", "report:export",
    ],
    "teacher": [
        "exam:read", "score:create", "score:read", "score:update", "score:export",
        "analysis:view",
    ],
    "student": ["score:read"],
    "parent": ["score:read"],
}

DEFAULT_SUBJECTS = [
    "语文", "数学", "英语", "物理", "化学",
    "生物", "政治", "历史", "地理", "技术",
]


async def seed_roles_and_permissions(db: AsyncSession) -> None:
    perm_objects: dict[str, Permission] = {}
    all_perms: list[tuple[str, str, str]] = []
    for perm_codes in ROLE_PERMISSION_MAP.values():
        for pc in perm_codes:
            all_perms.append((pc, pc, pc.split(":")[0], pc.split(":")[1]))

    seen: set[str] = set()
    for name, code, resource, action in all_perms:
        if code in seen:
            continue
        seen.add(code)
        result = await db.execute(select(Permission).where(Permission.code == code))
        existing = result.scalar_one_or_none()
        if existing:
            perm_objects[code] = existing
        else:
            perm = Permission(name=name, code=code, resource=resource, action=action)
            db.add(perm)
            perm_objects[code] = perm
    await db.flush()

    for role_code, perm_codes in ROLE_PERMISSION_MAP.items():
        result = await db.execute(select(Role).where(Role.code == role_code))
        role = result.scalar_one_or_none()
        if role is None:
            role_names = {
                "admin": "管理员", "director": "教学主管", "teacher": "教师",
                "student": "学生", "parent": "家长",
            }
            role = Role(name=role_names[role_code], code=role_code)
            db.add(role)
            await db.flush()

        for pc in perm_codes:
            perm = perm_objects[pc]
            result = await db.execute(
                select(role_permissions).where(
                    role_permissions.c.role_id == role.id,
                    role_permissions.c.permission_id == perm.id,
                )
            )
            if result.first() is None:
                await db.execute(
                    role_permissions.insert().values(
                        role_id=role.id, permission_id=perm.id
                    )
                )
    await db.flush()


async def seed_admin_user(db: AsyncSession) -> None:
    result = await db.execute(select(User).where(User.username == "admin"))
    if result.scalar_one_or_none() is not None:
        return

    result = await db.execute(select(Role).where(Role.code == "admin"))
    admin_role = result.scalar_one_or_none()
    if admin_role is None:
        return

    admin = User(
        username="admin",
        password_hash=hash_password("admin123"),
        real_name="系统管理员",
    )
    db.add(admin)
    await db.flush()
    await db.execute(user_roles.insert().values(user_id=admin.id, role_id=admin_role.id))
    await db.flush()


async def seed_subjects(db: AsyncSession) -> None:
    for i, name in enumerate(DEFAULT_SUBJECTS):
        result = await db.execute(select(Subject).where(Subject.name == name))
        if result.scalar_one_or_none() is None:
            db.add(Subject(name=name, sort_order=i + 1))
    await db.flush()


async def run_all_seeds(db: AsyncSession) -> None:
    await seed_roles_and_permissions(db)
    await seed_admin_user(db)
    await seed_subjects(db)
    await db.commit()
