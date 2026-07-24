"""Scores 模块 — 排名计算 Celery 任务
科目ID: 1=语文 2=数学 3=外语 4=物理 5=化学 6=生物 7=政治 8=历史 9=地理 10=技术
"""
from app.core.celery_app import celery_app

YWYS = (1, 2, 3)
SEVEN = (4, 5, 6, 7, 8, 9, 10)


@celery_app.task(bind=True, max_retries=3)
def calculate_ranks(self, exam_id: int):
    """Celery 入口 — 仅在生产模式(MySQL)下工作"""
    import asyncio
    asyncio.run(_calculate_ranks_async(exam_id))
    return {"exam_id": exam_id, "status": "completed"}


async def calculate_ranks_async(exam_id: int):
    """开发模式直接调用此函数"""
    await _calculate_ranks_async(exam_id)


async def _calculate_ranks_async(exam_id: int):
    from app.dependencies import get_db
    from app.core.database import async_session_factory
    from sqlalchemy import text

    async with async_session_factory() as db:
        # 0. 清除旧排名
        await db.execute(text("DELETE FROM rank_snapshots WHERE exam_id = :eid"),
                         {"eid": exam_id})

        # ===== 1. 总分排名 =====
        await db.execute(text(f"""
            INSERT INTO rank_snapshots (exam_id, student_id, total_score,
                grade_rank, class_rank, rank_type, calc_at)
            SELECT :eid, student_id, SUM(total_score),
               ROW_NUMBER() OVER (ORDER BY SUM(total_score) DESC),
               ROW_NUMBER() OVER (PARTITION BY s.class_id ORDER BY SUM(total_score) DESC),
               'total', datetime('now','localtime')
            FROM scores JOIN students s ON scores.student_id = s.id
            WHERE scores.exam_id = :eid
            GROUP BY student_id, s.class_id
        """), {"eid": exam_id})

        # 回写 scores
        await db.execute(text("""
            UPDATE scores SET (class_rank, grade_rank) = (
                SELECT rs.class_rank, rs.grade_rank FROM rank_snapshots rs
                WHERE rs.exam_id = scores.exam_id AND rs.student_id = scores.student_id
                  AND rs.rank_type = 'total'
            ) WHERE scores.exam_id = :eid
        """), {"eid": exam_id})

        # ===== 2. 单科排名 =====
        await db.execute(text(f"""
            INSERT INTO rank_snapshots (exam_id, student_id, subject_id, total_score,
                grade_rank, class_rank, rank_type, calc_at)
            SELECT :eid, student_id, subject_id, total_score,
               ROW_NUMBER() OVER (PARTITION BY subject_id ORDER BY total_score DESC),
               ROW_NUMBER() OVER (PARTITION BY subject_id, s.class_id ORDER BY total_score DESC),
               'subject', datetime('now','localtime')
            FROM scores JOIN students s ON scores.student_id = s.id
            WHERE scores.exam_id = :eid
        """), {"eid": exam_id})

        # ===== 3. 语数外 =====
        await db.execute(text(f"""
            INSERT INTO rank_snapshots (exam_id, student_id, total_score,
                grade_rank, class_rank, rank_type, calc_at)
            SELECT :eid, student_id, SUM(total_score),
               ROW_NUMBER() OVER (ORDER BY SUM(total_score) DESC),
               ROW_NUMBER() OVER (PARTITION BY s.class_id ORDER BY SUM(total_score) DESC),
               'yuwai', datetime('now','localtime')
            FROM scores JOIN students s ON scores.student_id = s.id
            WHERE scores.exam_id = :eid AND scores.subject_id IN {YWYS}
            GROUP BY student_id, s.class_id
        """), {"eid": exam_id})

        # ===== 4. 7选3 (按学生选科计算, 无选科则自动取前3) =====
        await _calc_top3_python(db, exam_id)

        await db.commit()


async def _calc_top3_python(db, exam_id: int):
    """按学生选科计算7选3总分, 未选科则自动取前3"""
    from sqlalchemy import select as sa_select
    from app.models.base_data import Student, Subject
    from app.models.exam import Score

    # 获取所有学生选科
    result = await db.execute(sa_select(Student))
    students = {s.id: s for s in result.scalars().all()}

    # 获取科目名称映射
    result = await db.execute(sa_select(Subject))
    subj_map = {s.id: s.name for s in result.scalars().all()}

    # 获取本次考试所有成绩
    result = await db.execute(
        sa_select(Score).where(Score.exam_id == exam_id))
    scores = list(result.scalars().all())

    # 按学生分组
    student_scores: dict[int, dict] = {}
    for sc in scores:
        sid = sc.student_id
        if sid not in student_scores:
            student_scores[sid] = {}
        sn = subj_map.get(sc.subject_id, '')
        student_scores[sid][sn] = float(sc.total_score)

    # 计算每个学生的7选3总分
    top3_data = []
    YWS = {'语文', '数学', '外语'}
    for sid, subs in student_scores.items():
        st = students.get(sid)
        electives_str = st.electives if st else ''

        if electives_str:
            # 按选科计算
            selected = [s.strip() for s in electives_str.split(',') if s.strip()]
            top3_sum = sum(subs.get(s, 0) for s in selected)
        else:
            # 无选科, 自动取7科中前3
            other = {k: v for k, v in subs.items() if k not in YWS}
            top3_items = sorted(other.values(), reverse=True)[:3]
            top3_sum = sum(top3_items)

        top3_data.append({
            'student_id': sid,
            'total_score': top3_sum,
            'class_id': st.class_id if st else 0,
        })

    # 排序并写入 rank_snapshots
    top3_data.sort(key=lambda x: x['total_score'], reverse=True)
    # 年级排名
    for i, d in enumerate(top3_data):
        d['grade_rank'] = i + 1
    # 班级排名
    class_ranks: dict[int, int] = {}
    for d in top3_data:
        cid = d['class_id']
        class_ranks[cid] = class_ranks.get(cid, 0) + 1
        d['class_rank'] = class_ranks[cid]

    from sqlalchemy import text
    for d in top3_data:
        await db.execute(text(
            "INSERT INTO rank_snapshots (exam_id, student_id, total_score,"
            " grade_rank, class_rank, rank_type, calc_at)"
            " VALUES (:eid, :sid, :ts, :gr, :cr, 'top3', datetime('now','localtime'))"
        ), {"eid": exam_id, "sid": d['student_id'], "ts": d['total_score'],
            "gr": d['grade_rank'], "cr": d['class_rank']})
