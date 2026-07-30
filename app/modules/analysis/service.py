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

    # 加载科目名称映射
    subj_names_map: dict[int, str] = {}
    subj_result = await db.execute(select(Subject))
    for s in subj_result.scalars().all():
        subj_names_map[s.id] = s.name

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
                "total": 0, "yuwai_total": 0, "top3_total": 0,
                "grade_rank": s.grade_rank,
                "class_rank": s.class_rank,
            }
        sn = s.subject.name if s.subject else str(s.subject_id)
        score_val = float(s.total_score)
        exam_data[eid]["subjects"][sn] = score_val
        exam_data[eid]["total"] += score_val
        if sn in YWYS_NAMES or sn == "英语":
            exam_data[eid]["yuwai_total"] += score_val

    result = await db.execute(select(Student).where(Student.id == student_id))
    stu = result.scalar_one_or_none()
    electives_str = stu.electives if stu and stu.electives else ""
    for eid, data in exam_data.items():
        if electives_str:
            selected = [s.strip() for s in electives_str.split(",") if s.strip()]
            top3_sum = sum(data["subjects"].get(k, 0) for k in selected[:3])
            data["top3_total"] = top3_sum
        else:
            other = {k: v for k, v in data["subjects"].items() if k not in YWYS_NAMES and k != "英语"}
            top3_items = sorted(other.values(), reverse=True)[:3]
            data["top3_total"] = sum(top3_items)

    # 查询语数外、7选3排名和科目排名
    exam_ids = list(exam_data.keys())
    if exam_ids:
        from app.models.audit import RankSnapshot
        for eid, data in exam_data.items():
            # 查询语数外和7选3排名
            for rank_type, key in [("yuwai", "yuwai_rank"), ("top3", "top3_rank")]:
                result = await db.execute(
                    select(RankSnapshot).where(
                        and_(RankSnapshot.exam_id == eid,
                             RankSnapshot.rank_type == rank_type,
                             RankSnapshot.student_id == student_id)))
                rs = result.scalar_one_or_none()
                data[key] = rs.grade_rank if rs else None

            # 查询各科排名
            subj_ranks: dict[str, int] = {}
            subj_result = await db.execute(
                select(RankSnapshot).where(
                    and_(RankSnapshot.exam_id == eid,
                         RankSnapshot.rank_type == "subject",
                         RankSnapshot.student_id == student_id)))
            for rs in subj_result.scalars().all():
                if rs.subject_id:
                    subj_name = subj_names_map.get(rs.subject_id, str(rs.subject_id))
                    subj_ranks[subj_name] = rs.grade_rank
            data["subject_ranks"] = subj_ranks

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

        # 获取学生选科信息
        result_stu = await db.execute(
            select(Student).where(Student.id.in_(ranked_student_ids)))
        stu_map = {s.id: s for s in result_stu.scalars().all()}

        # 定义语数外科目名 (含"英语"作为"外语"的别名)
        local_ywys = YWYS_NAMES | {"英语"}

        # 先从 rank_snapshots 查询 yuwai/top3 排名
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

        # 回退: 如果 rank_snapshots 没有 yuwai/top3 数据, 直接从成绩计算
        needs_yuwai_fallback = all(row.get("yuwai_total") is None for row in rows)
        needs_top3_fallback = all(row.get("top3_total") is None for row in rows)

        if needs_yuwai_fallback or needs_top3_fallback:
            # 先计算总分
            for row in rows:
                sid = row["student_id"]
                subs = subj_scores.get(sid, {})
                if needs_yuwai_fallback:
                    yuwai_sum = sum(subs.get(sn, 0) for sn in local_ywys)
                    row["yuwai_total"] = yuwai_sum
                if needs_top3_fallback:
                    st = stu_map.get(sid)
                    electives_str = st.electives if st else ''
                    if electives_str:
                        selected = [s.strip() for s in electives_str.split(',') if s.strip()]
                        top3_sum = sum(subs.get(s, 0) for s in selected[:3])
                    else:
                        other = {k: v for k, v in subs.items() if k not in local_ywys}
                        top3_items = sorted(other.values(), reverse=True)[:3]
                        top3_sum = sum(top3_items)
                    row["top3_total"] = top3_sum

            # 再计算排名 (如果 rank_snapshots 没有)
            if needs_yuwai_fallback:
                sorted_yuwai = sorted(
                    [(row["student_id"], row["yuwai_total"]) for row in rows],
                    key=lambda x: x[1], reverse=True)
                for rank, (sid, _) in enumerate(sorted_yuwai, 1):
                    for row in rows:
                        if row["student_id"] == sid:
                            row["yuwai_rank"] = rank
                            break

            if needs_top3_fallback:
                sorted_top3 = sorted(
                    [(row["student_id"], row["top3_total"]) for row in rows],
                    key=lambda x: x[1], reverse=True)
                for rank, (sid, _) in enumerate(sorted_top3, 1):
                    for row in rows:
                        if row["student_id"] == sid:
                            row["top3_rank"] = rank
                            break

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