"""Exams 模块路由"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
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


@router.get("/{exam_id}/stats")
async def exam_stats(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director", "teacher")),
):
    """检查考试关联数据量"""
    from sqlalchemy import text
    result = await db.execute(text(
        "SELECT (SELECT COUNT(*) FROM scores WHERE exam_id=:eid) as scores,"
        " (SELECT COUNT(*) FROM exam_subjects WHERE exam_id=:eid) as subjects"
    ), {"eid": exam_id})
    row = result.fetchone()
    return success_response(data={"scores": row[0], "subjects": row[1]})


@router.get("/{exam_id}/cutoffs")
async def get_cutoffs(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director", "teacher")),
):
    """获取已设置的分数线"""
    from sqlalchemy import text

    result = await db.execute(text(
        "SELECT cutoff_type, score FROM score_cutoffs WHERE exam_id=:eid"
    ), {"eid": exam_id})
    saved: dict[str, float] = {row[0]: float(row[1]) for row in result.fetchall()}

    CUTOFF_TYPES = [
        ("score_930", "930分数线"),
        ("special", "特控线(前20%)"),
        ("first", "一段线(前60%)"),
    ]
    SUBJ_NAMES = ['语文','数学','外语','政治','历史','地理','物理','化学','生物','技术']
    for sn in SUBJ_NAMES:
        CUTOFF_TYPES.append((f"subj_excellent_{sn}", f"{sn}优秀线"))
        CUTOFF_TYPES.append((f"subj_good_{sn}", f"{sn}良好线"))
    cutoffs = []
    for ct, name in CUTOFF_TYPES:
        cutoffs.append({
            "type": ct, "name": name,
            "score": saved.get(ct),
        })

    return success_response(data={"cutoffs": cutoffs})


class CutoffSave(BaseModel):
    cutoffs: dict = {}

@router.post("/{exam_id}/cutoffs")
async def save_cutoffs(
    exam_id: int,
    req: CutoffSave,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director", "teacher")),
):
    """手动设置分数线"""
    from sqlalchemy import text
    values = req.cutoffs

    # 先删后插
    await db.execute(text("DELETE FROM score_cutoffs WHERE exam_id=:eid"), {"eid": exam_id})
    for ct, score in values.items():
        if score is not None and float(score) > 0:
            await db.execute(text(
                "INSERT INTO score_cutoffs (exam_id, cutoff_type, score) VALUES (:eid, :ct, :sc)"
            ), {"eid": exam_id, "ct": ct, "sc": float(score)})
    await db.commit()

    return success_response(message="分数线保存成功")


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
