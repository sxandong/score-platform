"""模型包 — 导入所有模型以便 Alembic 和 SQLAlchemy 发现"""
from app.models.user import User, Role, Permission, user_roles, role_permissions
from app.models.base_data import Grade, Class, Student, Subject, Semester, Course
from app.models.exam import Exam, ExamSubject, Score, ScoreDetail
from app.models.audit import AuditLog, RankSnapshot

__all__ = [
    "User", "Role", "Permission", "user_roles", "role_permissions",
    "Grade", "Class", "Student", "Subject", "Semester", "Course",
    "Exam", "ExamSubject", "Score", "ScoreDetail",
    "AuditLog", "RankSnapshot",
]
