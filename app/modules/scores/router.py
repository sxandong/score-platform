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
    result = await service.batch_import_excel(db, content, exam_id, current_user.id)
    
    # 构建详细的成功提示信息
    msg_parts = []
    has_new = result['created_students'] > 0 or result['created_scores'] > 0
    has_update = result['updated_scores'] > 0
    has_error = len(result['errors']) > 0
    has_skipped = result['skipped_same'] > 0
    
    if has_new and has_update:
        msg_parts.append("导入完成")
    elif has_new:
        msg_parts.append("新增导入完成")
    elif has_update:
        msg_parts.append("覆盖更新完成")
    else:
        msg_parts.append("导入处理完成")
    
    if result['created_students'] > 0:
        msg_parts.append(f"新增 {result['created_students']} 名学生")
    if result['created_scores'] > 0:
        msg_parts.append(f"新增 {result['created_scores']} 条成绩")
    if result['updated_scores'] > 0:
        msg_parts.append(f"覆盖更新 {result['updated_scores']} 条成绩")
    if result['skipped_same'] > 0:
        msg_parts.append(f"跳过 {result['skipped_same']} 条(分数相同)")
    if has_error:
        msg_parts.append(f"失败 {len(result['errors'])} 条")
    
    elapsed = result.get('elapsed_seconds', 0)
    if elapsed:
        msg_parts.append(f"耗时 {elapsed} 秒")
    
    message = "，".join(msg_parts)
    
    return success_response(data=result, message=message)


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
