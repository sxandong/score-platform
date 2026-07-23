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

        # ===== 4. 7选3 (每人在7科中取前3高分之和) =====
        await db.execute(text(f"""
            INSERT INTO rank_snapshots (exam_id, student_id, total_score,
                grade_rank, class_rank, rank_type, calc_at)
            SELECT :eid, student_id, SUM(total_score),
               ROW_NUMBER() OVER (ORDER BY SUM(total_score) DESC),
               ROW_NUMBER() OVER (PARTITION BY class_id ORDER BY SUM(total_score) DESC),
               'top3', datetime('now','localtime')
            FROM (
                SELECT sc.exam_id, sc.student_id, sc.total_score, s.class_id,
                       ROW_NUMBER() OVER (PARTITION BY sc.student_id
                           ORDER BY sc.total_score DESC) AS rn
                FROM scores sc JOIN students s ON sc.student_id = s.id
                WHERE sc.exam_id = :eid AND sc.subject_id IN {SEVEN}
            ) ranked WHERE ranked.rn <= 3
            GROUP BY exam_id, student_id, class_id
        """), {"eid": exam_id})

        await db.commit()
