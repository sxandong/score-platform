"""数据库种子数据 — 默认角色、权限、管理员账号、科目"""
import logging
from sqlalchemy import select, update, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User, Role, Permission, user_roles, role_permissions
from app.models.base_data import Subject, Student, Class, Grade
from app.models.audit import RankSnapshot
from app.core.security import hash_password

logger = logging.getLogger(__name__)

ROLE_PERMISSION_MAP = {
    "admin": [
        "user:create", "user:read", "user:update", "user:delete",
        "exam:create", "exam:read", "exam:update", "exam:delete",
        "score:create", "score:read", "score:update", "score:delete", "score:export",
        "analysis:view", "report:export", "system:config",
    ],
    "director": [
        "exam:create", "exam:read", "exam:update", "exam:delete",
        "score:create", "score:read", "score:update", "score:delete", "score:export",
        "analysis:view", "report:export",
    ],
    "teacher": [
        "score:read", "analysis:view", "report:export",
    ],
    "student": ["score:read"],
    "parent": ["score:read"],
}

DEFAULT_SUBJECTS = [
    "语文", "数学", "外语", "物理", "化学",
    "生物", "政治", "历史", "地理", "技术",
]


async def seed_roles_and_permissions(db: AsyncSession) -> None:
    perm_objects: dict[str, Permission] = {}
    all_perms: list[tuple[str, str, str, str]] = []
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

        existing_perm_ids = set()
        rp_result = await db.execute(
            select(role_permissions.c.permission_id).where(
                role_permissions.c.role_id == role.id
            )
        )
        for (perm_id,) in rp_result.all():
            existing_perm_ids.add(perm_id)

        for pc in perm_codes:
            perm = perm_objects[pc]
            if perm.id not in existing_perm_ids:
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


async def _ensure_column(db: AsyncSession, table_name: str, column_name: str, column_sql: str):
    """安全地确保列存在 (跨数据库兼容)"""
    try:
        await db.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}"))
        await db.flush()
    except Exception:
        pass


async def seed_subjects(db: AsyncSession) -> None:
    from datetime import datetime

    # 迁移: 英语 → 外语 (仅 SQLite 下使用, MySQL 兼容)
    if settings.DATABASE_IS_SQLITE:
        try:
            await db.execute(text(
                "DELETE FROM subjects WHERE name='英语' AND EXISTS "
                "(SELECT 1 FROM subjects s2 WHERE s2.name='外语')"))
            await db.execute(text(
                "UPDATE subjects SET name='外语' WHERE name='英语' "
                "AND NOT EXISTS (SELECT 1 FROM subjects s2 WHERE s2.name='外语')"))
        except Exception:
            pass

    # 修复11位学籍号 → 12位 (补0)
    try:
        if settings.DATABASE_IS_SQLITE:
            await db.execute(text(
                "UPDATE students SET student_no = '0' || student_no WHERE length(student_no)=11"))
        else:
            await db.execute(text(
                "UPDATE students SET student_no = CONCAT('0', student_no) "
                "WHERE CHAR_LENGTH(student_no)=11"))
    except Exception:
        pass

    # 确保列存在
    await _ensure_column(db, "students", "electives", "electives VARCHAR(50) DEFAULT ''")
    await _ensure_column(db, "students", "enrollment_year", "enrollment_year INTEGER DEFAULT 2026")
    await _ensure_column(db, "exams", "enrollment_year", "enrollment_year INTEGER DEFAULT 2026")

    # 清理教师多余权限 + 添加 report:export
    teacher_role_result = await db.execute(select(Role).where(Role.code == "teacher"))
    teacher_role = teacher_role_result.scalar_one_or_none()
    if teacher_role:
        # 移除 teacher 不应有的权限
        perm_result = await db.execute(
            select(Permission).where(
                Permission.code.in_(["exam:read", "score:create", "score:delete"])
            )
        )
        for perm in perm_result.scalars().all():
            await db.execute(
                delete(role_permissions).where(
                    (role_permissions.c.role_id == teacher_role.id)
                    & (role_permissions.c.permission_id == perm.id)
                )
            )
        # 确保教师有 report:export
        export_perm_result = await db.execute(
            select(Permission).where(Permission.code == "report:export")
        )
        export_perm = export_perm_result.scalar_one_or_none()
        if export_perm:
            existing = await db.execute(
                select(role_permissions).where(
                    (role_permissions.c.role_id == teacher_role.id)
                    & (role_permissions.c.permission_id == export_perm.id)
                )
            )
            if existing.first() is None:
                await db.execute(
                    role_permissions.insert().values(
                        role_id=teacher_role.id, permission_id=export_perm.id
                    )
                )

    # 确保 score_cutoffs 表存在
    try:
        if settings.DATABASE_IS_SQLITE:
            await db.execute(text("""
                CREATE TABLE IF NOT EXISTS score_cutoffs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exam_id INTEGER NOT NULL,
                    cutoff_type VARCHAR(20) NOT NULL,
                    score REAL NOT NULL,
                    total_students INTEGER DEFAULT 0,
                    UNIQUE(exam_id, cutoff_type)
                )
            """))
        else:
            await db.execute(text("""
                CREATE TABLE IF NOT EXISTS score_cutoffs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    exam_id INT NOT NULL,
                    cutoff_type VARCHAR(20) NOT NULL,
                    score REAL NOT NULL,
                    total_students INT DEFAULT 0,
                    UNIQUE KEY uniq_exam_cutoff (exam_id, cutoff_type)
                )
            """))
    except Exception:
        pass

    for i, name in enumerate(DEFAULT_SUBJECTS):
        result = await db.execute(select(Subject).where(Subject.name == name))
        if result.scalar_one_or_none() is None:
            db.add(Subject(name=name, sort_order=i + 1))
    await db.flush()


async def seed_grades(db: AsyncSession) -> None:
    for name in ["高一", "高二", "高三"]:
        result = await db.execute(select(Grade).where(Grade.name == name))
        if result.scalar_one_or_none() is None:
            db.add(Grade(name=name))
    await db.flush()


async def seed_semesters(db: AsyncSession) -> None:
    from app.models.base_data import Semester
    from datetime import date
    semesters = [
        ("2026-2027学年第一学期", date(2026, 9, 1), date(2027, 1, 31), True),
        ("2026-2027学年第二学期", date(2027, 2, 1), date(2027, 7, 15), False),
    ]
    for name, start, end, current in semesters:
        result = await db.execute(select(Semester).where(Semester.name == name))
        if result.scalar_one_or_none() is None:
            db.add(Semester(name=name, start_date=start, end_date=end, is_current=current))
    await db.flush()


async def seed_demo_classes_and_students(db: AsyncSession) -> None:
    from datetime import date

    # 检查是否已有班级数据
    result = await db.execute(select(Class).limit(1))
    if result.scalar_one_or_none() is not None:
        return

    # 年级 ID
    grade_1 = await db.execute(select(Grade).where(Grade.name == "高一"))
    grade_2 = await db.execute(select(Grade).where(Grade.name == "高二"))
    grade_3 = await db.execute(select(Grade).where(Grade.name == "高三"))

    classes_data = [
        ("高一(1)班", grade_1.scalar_one().id),
        ("高一(2)班", grade_1.scalar_one().id),
        ("高二(1)班", grade_2.scalar_one().id),
        ("高三(1)班", grade_3.scalar_one().id),
    ]
    class_objects = {}
    for name, grade_id in classes_data:
        c = Class(name=name, grade_id=grade_id)
        db.add(c)
        await db.flush()
        class_objects[name] = c

    # 为高一(1)班创建30个学生
    for i in range(1, 31):
        sno = f"2026{str(i).zfill(4)}"
        db.add(Student(
            student_no=sno,
            name=f"学生{i:02d}",
            class_id=class_objects["高一(1)班"].id,
            enrollment_year=2026,
        ))
    await db.flush()


async def run_all_seeds(db: AsyncSession) -> None:
    logger.info("Starting seed data initialization...")
    await seed_roles_and_permissions(db)
    await seed_admin_user(db)
    await seed_subjects(db)
    await seed_grades(db)
    await seed_semesters(db)
    await seed_demo_classes_and_students(db)
    await db.commit()
    logger.info("Seed data initialization completed.")