"""Scores 模块 — 排名计算任务

科目名称: 语文(1) 数学(2) 外语(3) 物理(4) 化学(5) 生物(6) 政治(7) 历史(8) 地理(9) 技术(10)
语数外科目ID: 1, 2, 3
7选3科目ID: 4, 5, 6, 7, 8, 9, 10
"""
import logging
from datetime import datetime
from sqlalchemy import text

from app.core.celery_app import celery_app
from app.config import settings

logger = logging.getLogger(__name__)

# 常量: 语数外科目 ID
YWYS_IDS = (1, 2, 3)
# 常量: 7选3科目 ID
SEVEN_IDS = (4, 5, 6, 7, 8, 9, 10)
# 语数外科目名称
YWYS_NAMES = {"语文", "数学", "外语"}


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@celery_app.task(bind=True, max_retries=3)
def calculate_ranks(self, exam_id: int):
    """Celery 入口 — 在生产模式下使用"""
    import asyncio
    try:
        asyncio.run(_calculate_ranks_async(exam_id))
        return {"exam_id": exam_id, "status": "completed"}
    except Exception as e:
        raise self.retry(exc=e, countdown=2 ** self.request.retries)


async def calculate_ranks_async(exam_id: int):
    """开发模式直接调用此函数"""
    await _calculate_ranks_async(exam_id)


async def _calculate_ranks_async(exam_id: int):
    from app.core.database import async_session_factory
    from app.models.audit import RankSnapshot
    from app.models.exam import Score

    now_str = _now_str()

    async with async_session_factory() as db:
        try:
            # 0. 清除旧排名
            await db.execute(
                text("DELETE FROM rank_snapshots WHERE exam_id = :eid"),
                {"eid": exam_id}
            )
            logger.info(f"[RankCalc] Exam {exam_id}: cleared old ranks")

            # ===== 1. 总分排名 =====
            await db.execute(text("""
                INSERT INTO rank_snapshots (exam_id, student_id, total_score,
                    grade_rank, class_rank, rank_type, calc_at)
                SELECT :eid, student_id, SUM(total_score),
                    ROW_NUMBER() OVER (ORDER BY SUM(total_score) DESC),
                    ROW_NUMBER() OVER (PARTITION BY s.class_id ORDER BY SUM(total_score) DESC),
                    'total', :now
                FROM scores JOIN students s ON scores.student_id = s.id
                WHERE scores.exam_id = :eid
                GROUP BY student_id, s.class_id
            """), {"eid": exam_id, "now": now_str})
            logger.info(f"[RankCalc] Exam {exam_id}: total ranks calculated")

            # 回写 scores 的 class_rank/grade_rank (跨库兼容)
            rank_result = await db.execute(text("""
                SELECT student_id, class_rank, grade_rank
                FROM rank_snapshots
                WHERE exam_id = :eid AND rank_type = 'total'
            """), {"eid": exam_id})
            rank_updates = [
                {"eid": exam_id, "sid": row.student_id, "cr": row.class_rank, "gr": row.grade_rank}
                for row in rank_result
            ]
            if rank_updates:
                await db.execute(text("""
                    UPDATE scores SET class_rank = :cr, grade_rank = :gr
                    WHERE exam_id = :eid AND student_id = :sid
                """), rank_updates)
            logger.info(f"[RankCalc] Exam {exam_id}: class/grade ranks written back")

            # ===== 2. 单科排名 =====
            await db.execute(text("""
                INSERT INTO rank_snapshots (exam_id, student_id, subject_id, total_score,
                    grade_rank, class_rank, rank_type, calc_at)
                SELECT :eid, student_id, subject_id, total_score,
                    ROW_NUMBER() OVER (PARTITION BY subject_id ORDER BY total_score DESC),
                    ROW_NUMBER() OVER (PARTITION BY subject_id, s.class_id ORDER BY total_score DESC),
                    'subject', :now
                FROM scores JOIN students s ON scores.student_id = s.id
                WHERE scores.exam_id = :eid
            """), {"eid": exam_id, "now": now_str})
            logger.info(f"[RankCalc] Exam {exam_id}: subject ranks calculated")

            # ===== 3. 语数外排名 =====
            ywys_list = ",".join(str(i) for i in YWYS_IDS)
            await db.execute(text(f"""
                INSERT INTO rank_snapshots (exam_id, student_id, total_score,
                    grade_rank, class_rank, rank_type, calc_at)
                SELECT :eid, student_id, SUM(total_score),
                    ROW_NUMBER() OVER (ORDER BY SUM(total_score) DESC),
                    ROW_NUMBER() OVER (PARTITION BY s.class_id ORDER BY SUM(total_score) DESC),
                    'yuwai', :now
                FROM scores JOIN students s ON scores.student_id = s.id
                WHERE scores.exam_id = :eid AND scores.subject_id IN ({ywys_list})
                GROUP BY student_id, s.class_id
            """), {"eid": exam_id, "now": now_str})
            logger.info(f"[RankCalc] Exam {exam_id}: yuwai ranks calculated")

            # ===== 4. 7选3 (按学生选科计算) =====
            try:
                await _calc_top3_python(db, exam_id, now_str)
                logger.info(f"[RankCalc] Exam {exam_id}: top3 ranks calculated")
            except Exception as e:
                logger.error(f"[RankCalc] Exam {exam_id}: top3 ranks failed: {e}", exc_info=True)
                # 即使 top3 失败，也继续提交其他排名

            await db.commit()
            logger.info(f"[RankCalc] Exam {exam_id}: all ranks committed")

        except Exception as e:
            logger.error(f"[RankCalc] Exam {exam_id}: rank calculation failed: {e}", exc_info=True)
            await db.rollback()
            raise


async def _calc_top3_python(db, exam_id: int, now_str: str):
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
    for sid, subs in student_scores.items():
        st = students.get(sid)
        electives_str = st.electives if st else ''

        if electives_str:
            selected = [s.strip() for s in electives_str.split(',') if s.strip()]
            top3_sum = sum(subs.get(s, 0) for s in selected)
        else:
            other = {k: v for k, v in subs.items() if k not in YWYS_NAMES}
            top3_items = sorted(other.values(), reverse=True)[:3]
            top3_sum = sum(top3_items)

        top3_data.append({
            'student_id': sid,
            'total_score': top3_sum,
            'class_id': st.class_id if st else 0,
        })

    # 排序并计算排名
    top3_data.sort(key=lambda x: x['total_score'], reverse=True)
    for i, d in enumerate(top3_data):
        d['grade_rank'] = i + 1

    class_ranks: dict[int, int] = {}
    for d in top3_data:
        cid = d['class_id']
        class_ranks[cid] = class_ranks.get(cid, 0) + 1
        d['class_rank'] = class_ranks[cid]

    # 批量写入
    if top3_data:
        values_list = [
            {"eid": exam_id, "sid": d['student_id'], "ts": d['total_score'],
             "gr": d['grade_rank'], "cr": d['class_rank'], "now": now_str}
            for d in top3_data
        ]
        await db.execute(text("""
            INSERT INTO rank_snapshots (exam_id, student_id, total_score,
                grade_rank, class_rank, rank_type, calc_at)
            VALUES (:eid, :sid, :ts, :gr, :cr, 'top3', :now)
        """), values_list)