"""Analysis 模块业务逻辑 — 统计分析"""
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.exam import Exam, ExamSubject, Score
from app.models.base_data import Class, Student, Subject
from app.models.audit import RankSnapshot
from app.core.constants import (
    YWYS_NAMES, EXCELLENT_RATIO, PASS_RATIO, RANK_TYPE_TOTAL,
    RANK_TYPE_SUBJECT, RANK_TYPE_YUWAI, RANK_TYPE_TOP3
)


async def class_compare(
    db: AsyncSession, exam_id: int, subject_id: int | None = None,
) -> list[dict]:
    """班级横向对比分析"""
    conditions = [Score.exam_id == exam_id]
    full_score = 100.0
    if subject_id:
        conditions.append(Score.subject_id == subject_id)
        result = await db.execute(
            select(ExamSubject.full_score).where(
                and_(ExamSubject.exam_id == exam_id,
                     ExamSubject.subject_id == subject_id)
            )
        )
        fs = result.scalar_one_or_none()
        if fs:
            full_score = float(fs)

    excellent_threshold = full_score * EXCELLENT_RATIO
    pass_threshold = full_score * PASS_RATIO

    result = await db.execute(
        select(
            Class.id, Class.name,
            func.avg(Score.total_score).label("avg_score"),
            func.max(Score.total_score).label("max_score"),
            func.min(Score.total_score).label("min_score"),
            func.count(Score.id).label("count"),
            func.sum(
                case((Score.total_score >= excellent_threshold, 1), else_=0)
            ).label("excellent_count"),
            func.sum(
                case((Score.total_score >= pass_threshold, 1), else_=0)
            ).label("pass_count"),
        ).select_from(Score).join(Student).join(Class).where(
            and_(*conditions)
        ).group_by(Class.id, Class.name).order_by(
            func.avg(Score.total_score).desc()
        )
    )

    rows = []
    for row in result.all():
        count = row.count or 1
        rows.append({
            "class_id": row.id,
            "class_name": row.name,
            "avg_score": round(float(row.avg_score), 1),
            "max_score": float(row.max_score) if row.max_score else 0,
            "min_score": float(row.min_score) if row.min_score else 0,
            "excellent_rate": round(row.excellent_count / count * 100, 1),
            "pass_rate": round(row.pass_count / count * 100, 1),
            "student_count": count,
        })
    return rows


async def student_trend(
    db: AsyncSession, student_id: int, subject_id: int | None = None,
) -> list[dict]:
    """学生成绩纵向追踪"""
    conditions = [Score.student_id == student_id]
    if subject_id:
        conditions.append(Score.subject_id == subject_id)

    result = await db.execute(
        select(Score).options(
            selectinload(Score.exam), selectinload(Score.subject)
        ).where(and_(*conditions)).order_by(Score.exam_id)
    )
    scores = list(result.scalars().all())

    exam_data: dict[int, dict] = {}
    for s in scores:
        eid = s.exam_id
        if eid not in exam_data:
            e = s.exam
            exam_data[eid] = {
                "exam_id": eid,
                "exam_name": e.name if e else "",
                "exam_date": e.exam_date.isoformat() if e and e.exam_date else None,
                "subjects": {},
                "yws": {}, "top3": {},
                "total": 0, "yws_total": 0, "top3_total": 0,
                "grade_rank": s.grade_rank,
                "class_rank": s.class_rank,
            }
        sn = s.subject.name if s.subject else str(s.subject_id)
        score_val = float(s.total_score)
        exam_data[eid]["subjects"][sn] = score_val
        exam_data[eid]["total"] += score_val
        if sn in YWYS_NAMES:
            exam_data[eid]["yws"][sn] = score_val
            exam_data[eid]["yws_total"] += score_val

    result = await db.execute(select(Student).where(Student.id == student_id))
    stu = result.scalar_one_or_none()
    electives_str = stu.electives if stu and stu.electives else ""
    for eid, data in exam_data.items():
        if electives_str:
            selected = [s.strip() for s in electives_str.split(",") if s.strip()]
            top3_items = [(k, data["subjects"].get(k, 0)) for k in selected]
            data["top3"] = {k: v for k, v in top3_items}
            data["top3_total"] = sum(v for _, v in top3_items)
        else:
            other = {k: v for k, v in data["subjects"].items() if k not in YWYS_NAMES}
            top3_items = sorted(other.items(), key=lambda x: x[1], reverse=True)[:3]
            data["top3"] = dict(top3_items)
            data["top3_total"] = sum(v for _, v in top3_items)

    return list(exam_data.values())


async def grade_overview(
    db: AsyncSession, exam_id: int,
) -> dict:
    """年级总览"""
    result = await db.execute(
        select(
            func.avg(func.total_score).label("avg"),
            func.max(func.total_score).label("max"),
            func.min(func.total_score).label("min"),
        ).select_from(
            select(
                Score.exam_id, Score.student_id,
                func.sum(Score.total_score).label("total_score"),
            ).where(Score.exam_id == exam_id).group_by(
                Score.exam_id, Score.student_id
            ).subquery()
        )
    )
    stats = result.one()

    result = await db.execute(
        select(
            func.sum(
                case((Score.total_score >= 90, 1), else_=0)
            ).label("a_level"),
            func.sum(
                case(
                    (and_(Score.total_score >= 80, Score.total_score < 90), 1),
                    else_=0,
                )
            ).label("b_level"),
            func.sum(
                case(
                    (and_(Score.total_score >= 70, Score.total_score < 80), 1),
                    else_=0,
                )
            ).label("c_level"),
            func.sum(
                case(
                    (and_(Score.total_score >= 60, Score.total_score < 70), 1),
                    else_=0,
                )
            ).label("d_level"),
            func.sum(
                case((Score.total_score < 60, 1), else_=0)
            ).label("f_level"),
            func.count(Score.id).label("total"),
        ).where(Score.exam_id == exam_id)
    )
    dist = result.one()

    return {
        "total_avg": round(float(stats.avg), 1) if stats.avg else 0,
        "total_max": float(stats.max) if stats.max else 0,
        "total_min": float(stats.min) if stats.min else 0,
        "distribution": {
            "A(90-100)": dist.a_level or 0,
            "B(80-89)": dist.b_level or 0,
            "C(70-79)": dist.c_level or 0,
            "D(60-69)": dist.d_level or 0,
            "F(<60)": dist.f_level or 0,
        },
    }


async def get_ranks(
    db: AsyncSession, exam_id: int, page: int = 1, per_page: int = 50,
    class_id: int | None = None, rank_type: str = RANK_TYPE_TOTAL,
) -> tuple[list[dict], int]:
    """获取排名列表"""
    conditions = [
        RankSnapshot.exam_id == exam_id,
        RankSnapshot.rank_type == rank_type,
    ]
    if class_id:
        conditions.append(Student.class_id == class_id)

    subj_names: dict[int, str] = {}
    if rank_type == RANK_TYPE_SUBJECT:
        result = await db.execute(select(Subject))
        subj_names = {s.id: s.name for s in result.scalars().all()}

    offset = (page - 1) * per_page
    query = (
        select(RankSnapshot, Student.name, Student.student_no, Class.name)
        .select_from(RankSnapshot)
        .join(Student, RankSnapshot.student_id == Student.id)
        .join(Class, Student.class_id == Class.id)
        .where(and_(*conditions))
        .order_by(RankSnapshot.grade_rank.asc())
        .offset(offset).limit(per_page)
    )
    result = await db.execute(query)
    rows = []
    ranked_student_ids = []
    for rs, sname, sno, cname in result.all():
        row = {
            "rank": rs.grade_rank,
            "class_rank": rs.class_rank,
            "student_id": rs.student_id,
            "student_name": sname,
            "student_no": sno,
            "class_name": cname,
            "total_score": float(rs.total_score),
        }
        if rs.rank_type == RANK_TYPE_SUBJECT and rs.subject_id:
            row["subject_name"] = subj_names.get(rs.subject_id, str(rs.subject_id))
        rows.append(row)
        ranked_student_ids.append(rs.student_id)

    # 补充各科成绩 + 语数外/7选3排名
    if rank_type == RANK_TYPE_TOTAL and rows:
        result2 = await db.execute(
            select(Score).options(selectinload(Score.subject))
            .where(and_(Score.exam_id == exam_id, Score.student_id.in_(ranked_student_ids))))
        subj_scores: dict[int, dict] = {}
        for sc in result2.scalars().all():
            if sc.student_id not in subj_scores:
                subj_scores[sc.student_id] = {}
            sn = sc.subject.name if sc.subject else str(sc.subject_id)
            subj_scores[sc.student_id][sn] = float(sc.total_score)

        # 批量查询语数外排名
        for rt, key, total_key in [
            (RANK_TYPE_YUWAI, "yuwai_rank", "yuwai_total"),
            (RANK_TYPE_TOP3, "top3_rank", "top3_total"),
        ]:
            result3 = await db.execute(
                select(RankSnapshot).where(and_(
                    RankSnapshot.exam_id == exam_id, RankSnapshot.rank_type == rt,
                    RankSnapshot.student_id.in_(ranked_student_ids))))
            rank_map = {rs.student_id: rs.grade_rank for rs in result3.scalars().all()}
            total_map = {rs.student_id: float(rs.total_score) for rs in result3.scalars().all()}
            for row in rows:
                row[key] = rank_map.get(row["student_id"])
                row[total_key] = total_map.get(row["student_id"])

        for row in rows:
            row["subjects"] = subj_scores.get(row["student_id"], {})

    # 总数
    count_q = (
        select(func.count(RankSnapshot.id))
        .select_from(RankSnapshot)
        .join(Student, RankSnapshot.student_id == Student.id)
        .where(and_(*conditions))
    )
    if class_id:
        count_q = count_q.join(Class, Student.class_id == Class.id)
    result = await db.execute(count_q)
    total = result.scalar_one()

    return rows, total