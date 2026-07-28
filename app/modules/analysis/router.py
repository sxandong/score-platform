"""Analysis 模块路由"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.core.security import get_current_user, require_role
from app.core.response import success_response, paginated_response
from app.modules.analysis import service

router = APIRouter(prefix="/api/analysis", tags=["统计分析"])


@router.get("/class-cutoff-stats")
async def class_cutoff_stats(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director", "teacher")),
):
    """各班级分数线人数统计"""
    from sqlalchemy import text

    # 获取分数线设置
    result = await db.execute(text(
        "SELECT cutoff_type, score FROM score_cutoffs WHERE exam_id=:eid"
    ), {"eid": exam_id})
    cutoffs: dict[str, float] = {row[0]: float(row[1]) for row in result.fetchall()}

    # 获取该考试对应年级的班级(无结果则显示全部)
    result = await db.execute(text(
        "SELECT id, name FROM classes WHERE grade_id = (SELECT grade_id FROM exams WHERE id=:eid)"
        " ORDER BY id"), {"eid": exam_id})
    classes = [{"id": row[0], "name": row[1]} for row in result.fetchall()]
    if not classes:  # fallback
        result = await db.execute(text("SELECT id, name FROM classes ORDER BY id"))
        classes = [{"id": row[0], "name": row[1]} for row in result.fetchall()]

    # 对每个班级统计各项指标
    for cls in classes:
        cid = cls["id"]
        # 930线人数
        if "score_930" in cutoffs:
            result = await db.execute(text(
                "SELECT COUNT(*) FROM rank_snapshots rs JOIN students s ON rs.student_id=s.id"
                " WHERE rs.exam_id=:eid AND rs.rank_type='total' AND s.class_id=:cid"
                " AND rs.total_score >= :sc"
            ), {"eid": exam_id, "cid": cid, "sc": cutoffs["score_930"]})
            cls["count_930"] = result.scalar_one()

        # 特控线人数
        if "special" in cutoffs:
            result = await db.execute(text(
                "SELECT COUNT(*) FROM rank_snapshots rs JOIN students s ON rs.student_id=s.id"
                " WHERE rs.exam_id=:eid AND rs.rank_type='total' AND s.class_id=:cid"
                " AND rs.total_score >= :sc"
            ), {"eid": exam_id, "cid": cid, "sc": cutoffs["special"]})
            cls["count_special"] = result.scalar_one()

        # 一段线人数
        if "first" in cutoffs:
            result = await db.execute(text(
                "SELECT COUNT(*) FROM rank_snapshots rs JOIN students s ON rs.student_id=s.id"
                " WHERE rs.exam_id=:eid AND rs.rank_type='total' AND s.class_id=:cid"
                " AND rs.total_score >= :sc"
            ), {"eid": exam_id, "cid": cid, "sc": cutoffs["first"]})
            cls["count_first"] = result.scalar_one()

        # 前N位人数
        for top_n in [20, 30, 50, 80, 100]:
            result = await db.execute(text(
                "SELECT COUNT(*) FROM rank_snapshots rs JOIN students s ON rs.student_id=s.id"
                " WHERE rs.exam_id=:eid AND rs.rank_type='total' AND s.class_id=:cid"
                " AND rs.grade_rank <= :n"
            ), {"eid": exam_id, "cid": cid, "n": top_n})
            cls[f"top{top_n}"] = result.scalar_one()

    # 各科优秀/良好线上线统计
    subj_stats: dict[str, list] = {}
    for key_prefix, label in [("subj_excellent_", "优秀"), ("subj_good_", "良好")]:
        for subj_name in ['语文','数学','外语','政治','历史','地理','物理','化学','生物','技术']:
            ct = f"{key_prefix}{subj_name}"
            if ct in cutoffs:
                sc = cutoffs[ct]
                result = await db.execute(text(
                    "SELECT s.class_id, COUNT(*) FROM scores sc2"
                    " JOIN students s ON sc2.student_id=s.id"
                    " JOIN subjects sub ON sc2.subject_id=sub.id"
                    " WHERE sc2.exam_id=:eid AND sub.name=:sn AND sc2.total_score>=:sc"
                    " GROUP BY s.class_id"
                ), {"eid": exam_id, "sn": subj_name, "sc": sc})
                for row in result.fetchall():
                    cid, cnt = row[0], row[1]
                    key = f"{subj_name}{label}"
                    if key not in subj_stats:
                        subj_stats[key] = []
                    subj_stats[key].append({"class_id": cid, "count": cnt})

    return success_response(data={
        "classes": classes,
        "cutoffs": {k: v for k, v in cutoffs.items()},
        "subj_stats": subj_stats,
    })


@router.get("/multi-exam-compare")
async def multi_exam_compare(
    exam_ids: str = "",
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director", "teacher")),
):
    """多考试班级对比: ?exam_ids=1,2,3"""
    from sqlalchemy import text
    ids = [int(x.strip()) for x in exam_ids.split(",") if x.strip()]
    if len(ids) < 2:
        return success_response(data={"exams": [], "classes": [], "data": {}})

    ids_str = ','.join(str(i) for i in ids)
    result = await db.execute(
        text(f"SELECT id, name FROM exams WHERE id IN ({ids_str}) ORDER BY exam_date"))
    exams = [{"id": r[0], "name": r[1]} for r in result.fetchall()]

    # 取第一个考试的年级来筛选班级(无结果则显示全部)
    first_eid = ids[0]
    result = await db.execute(text(
        "SELECT id, name FROM classes WHERE grade_id = (SELECT grade_id FROM exams WHERE id=:eid)"
        " ORDER BY id"), {"eid": first_eid})
    classes = [{"id": r[0], "name": r[1]} for r in result.fetchall()]
    if not classes:
        result = await db.execute(text("SELECT id, name FROM classes ORDER BY id"))
        classes = [{"id": r[0], "name": r[1]} for r in result.fetchall()]

    data: dict = {}
    for eid in ids:
        result = await db.execute(text(
            "SELECT cutoff_type, score FROM score_cutoffs WHERE exam_id=:eid"
        ), {"eid": eid})
        cutoffs = {r[0]: float(r[1]) for r in result.fetchall()}

        class_counts = []
        for cls in classes:
            cid = cls["id"]
            entry = {"class_id": cid, "class_name": cls["name"]}
            for ct, key in [("score_930","c930"), ("special","special"), ("first","first")]:
                if ct in cutoffs:
                    result = await db.execute(text(
                        "SELECT COUNT(*) FROM rank_snapshots rs JOIN students s ON rs.student_id=s.id"
                        " WHERE rs.exam_id=:eid AND rs.rank_type='total' AND s.class_id=:cid"
                        " AND rs.total_score >= :sc"
                    ), {"eid": eid, "cid": cid, "sc": cutoffs[ct]})
                    entry[key] = result.scalar_one()
            class_counts.append(entry)
        data[str(eid)] = {"cutoffs": cutoffs, "class_counts": class_counts}

    return success_response(data={"exams": exams, "classes": classes, "data": data})


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


@router.get("/cutoff-trend")
async def cutoff_trend(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director", "teacher")),
):
    """历次考试930/特控/一段上线人数趋势"""
    from sqlalchemy import text
    result = await db.execute(text("SELECT id, name, exam_date FROM exams ORDER BY exam_date"))
    exams = [{"id": r[0], "name": r[1], "date": str(r[2]) if r[2] else None} for r in result.fetchall()]
    data = []
    for e in exams:
        entry = {"exam_id": e["id"], "exam_name": e["name"], "exam_date": e["date"]}
        result = await db.execute(text(
            "SELECT cutoff_type, score FROM score_cutoffs WHERE exam_id=:eid"), {"eid": e["id"]})
        cutoffs = {r[0]: float(r[1]) for r in result.fetchall()}
        for ct, key in [("score_930","c930"),("special","special"),("first","first")]:
            entry[key] = 0
            if ct in cutoffs:
                result = await db.execute(text(
                    "SELECT COUNT(*) FROM rank_snapshots WHERE exam_id=:eid"
                    " AND rank_type='total' AND total_score >= :sc"
                ), {"eid": e["id"], "sc": cutoffs[ct]})
                entry[key] = result.scalar_one()
        data.append(entry)
    return success_response(data=data)


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
