"""Exams 模块路由"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.core.security import get_current_user, require_role
from app.core.response import success_response, paginated_response
from app.modules.exams.schemas import ExamCreate, ExamUpdate
from app.modules.exams import service

router = APIRouter(prefix="/api/exams", tags=["考试管理"])


@router.get("")
async def list_exams(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    grade_id: int | None = None,
    semester_id: int | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director", "teacher")),
):
    exams, total = await service.list_exams(
        db, page, per_page, grade_id, semester_id, status
    )
    return paginated_response(
        items=[service._exam_to_dict(e) for e in exams],
        total=total, page=page, per_page=per_page,
    )


@router.get("/{exam_id}")
async def get_exam(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director", "teacher")),
):
    exam = await service.get_exam(db, exam_id)
    return success_response(data=service._exam_to_dict(exam))


@router.post("")
async def create_exam(
    req: ExamCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director", "teacher")),
):
    exam = await service.create_exam(db, req, current_user.id)
    return success_response(data=service._exam_to_dict(exam), message="考试创建成功")


@router.put("/{exam_id}")
async def update_exam(
    exam_id: int,
    req: ExamUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director", "teacher")),
):
    exam = await service.update_exam(db, exam_id, req)
    return success_response(data=service._exam_to_dict(exam), message="考试更新成功")


@router.delete("/{exam_id}")
async def delete_exam(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    await service.delete_exam(db, exam_id)
    return success_response(message="考试已删除")


@router.put("/{exam_id}/lock")
async def lock_exam(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    from app.modules.exams.schemas import ExamUpdate
    exam = await service.update_exam(db, exam_id, ExamUpdate(status="locked"))
    return success_response(data=service._exam_to_dict(exam), message="考试已锁定")
