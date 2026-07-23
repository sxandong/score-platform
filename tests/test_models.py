"""模型导入测试"""
import pytest


def test_all_models_import():
    from app.models import (
        User, Role, Permission,
        Grade, Class, Student, Subject, Semester, Course,
        Exam, ExamSubject, Score, ScoreDetail, AuditLog, RankSnapshot,
    )
    assert User.__tablename__ == "users"
    assert Role.__tablename__ == "roles"
    assert Exam.__tablename__ == "exams"
    assert Score.__tablename__ == "scores"
    assert AuditLog.__tablename__ == "audit_logs"
    assert RankSnapshot.__tablename__ == "rank_snapshots"
    assert Grade.__tablename__ == "grades"
    assert Class.__tablename__ == "classes"
    assert Student.__tablename__ == "students"
    assert Subject.__tablename__ == "subjects"
    assert Semester.__tablename__ == "semesters"
    assert Course.__tablename__ == "courses"
    assert ExamSubject.__tablename__ == "exam_subjects"
    assert ScoreDetail.__tablename__ == "score_details"


def test_security_helpers():
    from app.core.security import hash_password, verify_password
    from app.core.security import create_access_token, create_refresh_token, verify_token

    pw = hash_password("mypassword")
    assert verify_password("mypassword", pw)
    assert not verify_password("wrong", pw)

    token = create_access_token(1, ["admin", "teacher"])
    payload = verify_token(token)
    assert payload is not None
    assert payload["sub"] == "1"
    assert payload["roles"] == ["admin", "teacher"]
    assert payload["type"] == "access"

    refresh = create_refresh_token(1)
    rp = verify_token(refresh)
    assert rp is not None
    assert rp["type"] == "refresh"


def test_exception_hierarchy():
    from app.core.exceptions import (
        AppException, NotFoundException, ForbiddenException,
        UnauthorizedException, ValidationException,
    )
    e = NotFoundException("test")
    assert e.code == 404
    assert isinstance(e, AppException)

    e2 = ForbiddenException()
    assert e2.code == 403

    e3 = UnauthorizedException()
    assert e3.code == 401

    e4 = ValidationException("bad", {"field": "error"})
    assert e4.code == 400
    assert e4.data == {"field": "error"}
