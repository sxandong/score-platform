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
    """计算考试分数线: 特控线(前20%), 一段线(前60%)"""
    from sqlalchemy import text
    # 查总分排名人数
    result = await db.execute(text(
        "SELECT COUNT(*) FROM rank_snapshots WHERE exam_id=:eid AND rank_type='total'"
    ), {"eid": exam_id})
    total = result.scalar_one()

    if not total:
        return success_response(data={"total": 0, "cutoffs": []})

    # 计算各百分位分数
    cutoffs = []
    for pct, name in [(0.2, "特控线(前20%)"), (0.6, "一段线(前60%)")]:
        rank_pos = max(1, int(total * pct))
        result = await db.execute(text(
            "SELECT total_score FROM rank_snapshots WHERE exam_id=:eid AND rank_type='total'"
            " ORDER BY grade_rank ASC LIMIT 1 OFFSET :offset"
        ), {"eid": exam_id, "offset": rank_pos - 1})
        row = result.fetchone()
        cutoffs.append({
            "name": name,
            "percentile": f"前{int(pct*100)}%",
            "rank": rank_pos,
            "score": float(row[0]) if row else 0,
        })

    return success_response(data={"total": total, "cutoffs": cutoffs})


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
