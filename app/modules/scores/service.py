"""Scores 模块业务逻辑"""
import pandas as pd
from io import BytesIO
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.exam import Exam, ExamSubject, Score
from app.models.base_data import Class, Student, Subject
from app.core.exceptions import NotFoundException, ForbiddenException


async def create_scores(
    db: AsyncSession, exam_id: int, scores_data: list,
    entered_by: int, allowed_class_ids: set[int] | None,
) -> dict:
    """批量录入成绩。allowed_class_ids=None 表示所有班级。"""
    # 验证考试存在且未锁定
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalar_one_or_none()
    if exam is None:
        raise NotFoundException("考试不存在")
    if exam.status == "locked":
        raise ForbiddenException("考试已锁定，无法录入成绩")

    # 获取考试科目
    result = await db.execute(
        select(ExamSubject).where(ExamSubject.exam_id == exam_id)
    )
    exam_subjects = {es.subject_id: es for es in result.scalars().all()}

    created = 0
    errors = []

    for entry in scores_data:
        sid = entry["student_id"]
        subj_id = entry["subject_id"]
        score_val = entry["total_score"]

        # 验证科目属于本次考试
        es = exam_subjects.get(subj_id)
        if es is None:
            errors.append({"student_id": sid, "reason": "科目不在本次考试中"})
            continue

        # 验证分数范围
        if score_val > float(es.full_score):
            errors.append({
                "student_id": sid,
                "reason": f"分数{score_val}超过满分{es.full_score}",
            })
            continue

        # 数据权限校验
        if allowed_class_ids is not None:
            result = await db.execute(
                select(Student.class_id).where(Student.id == sid)
            )
            class_id = result.scalar_one_or_none()
            if class_id is None or class_id not in allowed_class_ids:
                errors.append({"student_id": sid, "reason": "无权限"})
                continue

        # UPSERT
        result = await db.execute(
            select(Score).where(
                and_(
                    Score.exam_id == exam_id,
                    Score.student_id == sid,
                    Score.subject_id == subj_id,
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.total_score = score_val
            existing.entered_by = entered_by
        else:
            db.add(Score(
                exam_id=exam_id, student_id=sid, subject_id=subj_id,
                total_score=score_val, entered_by=entered_by,
            ))
        created += 1

    await db.flush()

    # 同步计算排名 (生产环境可改为 Celery 异步)
    from app.modules.scores.tasks import calculate_ranks_async
    await calculate_ranks_async(exam_id)

    return {"count": created, "errors": errors}


async def get_class_scores(
    db: AsyncSession, exam_id: int, class_id: int,
) -> list[dict]:
    """获取班级某次考试全部成绩单"""
    result = await db.execute(
        select(Student).where(Student.class_id == class_id)
    )
    students = {s.id: s for s in result.scalars().all()}

    result = await db.execute(
        select(Score).options(
            selectinload(Score.subject)
        ).where(
            and_(Score.exam_id == exam_id, Score.student_id.in_(students.keys()))
        ).order_by(Score.student_id)
    )
    scores = result.scalars().all()

    # 按学生分组
    student_scores: dict[int, dict] = {}
    for s in scores:
        if s.student_id not in student_scores:
            st = students.get(s.student_id)
            student_scores[s.student_id] = {
                "student_id": s.student_id,
                "student_name": st.name if st else "",
                "student_no": st.student_no if st else "",
                "subjects": {},
                "total": 0,
                "class_rank": s.class_rank,
                "grade_rank": s.grade_rank,
            }
        student_scores[s.student_id]["subjects"][
            s.subject.name if s.subject else str(s.subject_id)
        ] = float(s.total_score)
        student_scores[s.student_id]["total"] += float(s.total_score)

    return list(student_scores.values())


async def get_student_scores(
    db: AsyncSession, student_id: int, semester_id: int | None = None,
) -> list[dict]:
    """获取学生所有考试成绩"""
    query = (
        select(Score).options(
            selectinload(Score.exam), selectinload(Score.subject)
        ).where(Score.student_id == student_id)
    )
    if semester_id:
        query = query.join(Exam).where(Exam.semester_id == semester_id)
    query = query.order_by(Score.exam_id.desc())

    result = await db.execute(query)
    scores = result.scalars().all()

    # 按考试分组
    exam_scores: dict[int, dict] = {}
    for s in scores:
        eid = s.exam_id
        if eid not in exam_scores:
            exam_scores[eid] = {
                "exam_id": eid,
                "exam_name": s.exam.name if s.exam else "",
                "exam_date": s.exam.exam_date.isoformat() if s.exam and s.exam.exam_date else None,
                "subjects": {},
                "total": 0,
                "grade_rank": s.grade_rank,
            }
        exam_scores[eid]["subjects"][
            s.subject.name if s.subject else str(s.subject_id)
        ] = float(s.total_score)
        exam_scores[eid]["total"] += float(s.total_score)

    return sorted(exam_scores.values(), key=lambda x: x["exam_date"] or "", reverse=True)


async def batch_import_excel(
    db: AsyncSession, file_content: bytes, exam_id: int,
) -> dict:
    """解析Excel文件，返回预览数据 (不保存)"""
    df = pd.read_excel(BytesIO(file_content))
    # 预期列: 学号, 姓名, [各科目名...]
    columns = df.columns.tolist()
    student_cols = [c for c in columns if c in ("学号", "学籍号", "姓名", "student_no", "name")]
    subject_cols = [c for c in columns if c not in student_cols]

    # 获取考试科目映射
    result = await db.execute(
        select(ExamSubject, Subject.name).join(Subject).where(
            ExamSubject.exam_id == exam_id
        )
    )
    subject_map = {}
    for es, subj_name in result.all():
        subject_map[subj_name] = {"id": es.subject_id, "full_score": float(es.full_score)}

    preview = []
    for idx, row in df.iterrows():
        student_no = str(row.get("学籍号", row.get("学号", row.get("student_no", ""))))
        if not student_no:
            preview.append({"row": idx + 1, "status": "error", "reason": "缺少学号"})
            continue

        scores = {}
        has_error = False
        for col in subject_cols:
            if col in subject_map:
                val = row[col]
                try:
                    val = float(val)
                    if val > subject_map[col]["full_score"]:
                        preview.append({
                            "row": idx + 1, "status": "error",
                            "reason": f"{col}分数{val}超过满分{subject_map[col]['full_score']}",
                        })
                        has_error = True
                        break
                    scores[subject_map[col]["id"]] = val
                except (ValueError, TypeError):
                    scores[subject_map[col]["id"]] = 0

        if not has_error:
            preview.append({
                "row": idx + 1, "status": "ok",
                "student_no": student_no,
                "scores": scores,
            })

    return {"preview": preview, "headers": columns, "subject_cols": subject_cols}
