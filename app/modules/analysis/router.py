"""Analysis 模块路由"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.core.security import get_current_user, require_role
from app.core.response import success_response, paginated_response
from app.modules.analysis import service

router = APIRouter(prefix="/api/analysis", tags=["统计分析"])


@router.get("/class-compare")
async def class_compare(
    exam_id: int,
    subject_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director", "teacher")),
):
    data = await service.class_compare(db, exam_id, subject_id)
    return success_response(data=data)


@router.get("/student-trend")
async def student_trend(
    student_id: int,
    subject_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = await service.student_trend(db, student_id, subject_id)
    return success_response(data=data)


@router.get("/grade-overview")
async def grade_overview(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director")),
):
    data = await service.grade_overview(db, exam_id)
    return success_response(data=data)


@router.get("/score-distribution")
async def score_distribution(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director", "teacher")),
):
    """各学科分数段统计"""
    from sqlalchemy import text
    thresholds = [130, 120, 110, 100, 95, 90, 85, 80, 75, 70, 65, 60, 55, 50, 45, 40]
    result = []
    for t in thresholds:
        r = await db.execute(text(
            "SELECT subj.name, COUNT(sc.id) as cnt FROM scores sc "
            "JOIN subjects subj ON sc.subject_id = subj.id "
            "WHERE sc.exam_id = :eid AND sc.total_score >= :th "
            "GROUP BY subj.name ORDER BY subj.sort_order"
        ), {"eid": exam_id, "th": t})
        for row in r.fetchall():
            result.append({"threshold": t, "subject": row[0], "count": row[1]})
    return success_response(data=result)


@router.get("/ranks")
async def get_ranks(
    exam_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=10000),
    class_id: int | None = None,
    rank_type: str = "total",
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director", "teacher", "student")),
):
    rows, total = await service.get_ranks(
        db, exam_id, page, per_page, class_id, rank_type
    )
    return paginated_response(items=rows, total=total, page=page, per_page=per_page)
