"""Scores 模块路由"""
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.core.security import (
    get_current_user, require_role, get_teacher_class_ids
)
from app.core.response import success_response, paginated_response
from app.modules.exams.schemas import ScoresBatchCreate
from app.modules.scores import service

router = APIRouter(prefix="/api/scores", tags=["成绩管理"])


@router.post("")
async def create_scores(
    req: ScoresBatchCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director", "teacher")),
    allowed_classes=Depends(get_teacher_class_ids),
):
    result = await service.create_scores(
        db, req.exam_id,
        [s.model_dump() for s in req.scores],
        current_user.id, allowed_classes,
    )
    return success_response(
        data=result,
        message=f"成功录入{result['count']}条成绩"
    )


@router.post("/batch")
async def batch_import(
    exam_id: int = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director", "teacher")),
):
    content = await file.read()
    result = await service.batch_import_excel(db, content, exam_id)
    return success_response(data=result,
        message=f"导入完成: {result['total_rows']}行, 新增{result['created_students']}学生, {result['created_scores']}条成绩")


@router.get("/class/{class_id}/exam/{exam_id}")
async def get_class_scores(
    class_id: int,
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director", "teacher")),
):
    scores = await service.get_class_scores(db, exam_id, class_id)
    return success_response(data=scores)


@router.get("/student/{student_id}")
async def get_student_scores(
    student_id: int,
    semester_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    scores = await service.get_student_scores(db, student_id, semester_id)
    return success_response(data=scores)
