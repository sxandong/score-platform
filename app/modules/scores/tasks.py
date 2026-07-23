"""Scores 模块 — 排名计算 Celery 任务"""
from app.core.celery_app import celery_app
from sqlalchemy import create_engine, text
from app.config import settings


@celery_app.task(bind=True, max_retries=3)
def calculate_ranks(self, exam_id: int):
    """计算一次考试的总分和单科排名，写入 rank_snapshots"""
    sync_url = settings.DATABASE_URL.replace("+aiomysql", "+pymysql")
    engine = create_engine(sync_url)

    with engine.connect() as conn:
        # 清除旧快照
        conn.execute(text(
            "DELETE FROM rank_snapshots WHERE exam_id = :eid AND rank_type = 'total'"
        ), {"eid": exam_id})

        # 计算总分排名 (年级+班级)
        conn.execute(text("""
            INSERT INTO rank_snapshots
                (exam_id, student_id, total_score, grade_rank, class_rank,
                 rank_type, calc_at)
            SELECT :eid, student_id, SUM(total_score),
                   ROW_NUMBER() OVER (ORDER BY SUM(total_score) DESC),
                   ROW_NUMBER() OVER (
                       PARTITION BY s.class_id ORDER BY SUM(total_score) DESC
                   ),
                   'total', NOW()
            FROM scores
            JOIN students s ON scores.student_id = s.id
            WHERE scores.exam_id = :eid
            GROUP BY student_id, s.class_id
        """), {"eid": exam_id})

        # 回写 scores 表
        conn.execute(text("""
            UPDATE scores
            INNER JOIN (
                SELECT exam_id, student_id, class_rank, grade_rank
                FROM rank_snapshots
                WHERE exam_id = :eid AND rank_type = 'total'
            ) rs ON scores.exam_id = rs.exam_id
                AND scores.student_id = rs.student_id
            SET scores.class_rank = rs.class_rank,
                scores.grade_rank = rs.grade_rank
            WHERE scores.exam_id = :eid
        """), {"eid": exam_id})

        conn.commit()

    engine.dispose()
    return {"exam_id": exam_id, "status": "completed"}
