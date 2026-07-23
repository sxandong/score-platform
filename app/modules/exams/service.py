"""Exams 模块业务逻辑"""
from datetime import date
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.exam import Exam, ExamSubject
from app.models.base_data import Subject
from app.core.exceptions import NotFoundException


async def list_exams(
    db: AsyncSession, page: int = 1, per_page: int = 20,
    grade_id: int | None = None, semester_id: int | None = None,
    status: str | None = None,
) -> tuple[list[Exam], int]:
    conditions = []
    if grade_id:
        conditions.append(Exam.grade_id == grade_id)
    if semester_id:
        conditions.append(Exam.semester_id == semester_id)
    if status:
        conditions.append(Exam.status == status)

    offset = (page - 1) * per_page
    query = select(Exam).options(
        selectinload(Exam.exam_subjects).selectinload(ExamSubject.subject)
    ).order_by(Exam.id.desc()).offset(offset).limit(per_page)
    for cond in conditions:
        query = query.where(cond)

    result = await db.execute(query)
    exams = result.scalars().all()

    count_query = select(func.count(Exam.id))
    for cond in conditions:
        count_query = count_query.where(cond)
    result = await db.execute(count_query)
    total = result.scalar_one()

    return list(exams), total


async def get_exam(db: AsyncSession, exam_id: int) -> Exam:
    result = await db.execute(
        select(Exam).options(
            selectinload(Exam.exam_subjects).selectinload(ExamSubject.subject)
        ).where(Exam.id == exam_id)
    )
    exam = result.scalar_one_or_none()
    if exam is None:
        raise NotFoundException("考试不存在")
    return exam


async def create_exam(db: AsyncSession, data, created_by: int) -> Exam:
    exam = Exam(
        name=data.name,
        exam_type=data.exam_type,
        semester_id=data.semester_id,
        grade_id=data.grade_id,
        exam_date=date.fromisoformat(data.exam_date) if data.exam_date else None,
        created_by=created_by,
    )
    db.add(exam)
    await db.flush()

    for subj in data.subjects:
        es = ExamSubject(
            exam_id=exam.id,
            subject_id=subj["subject_id"],
            full_score=subj.get("full_score", 100.0),
            weight=subj.get("weight", 1.0),
        )
        db.add(es)
    await db.flush()
    return exam


async def update_exam(db: AsyncSession, exam_id: int, data) -> Exam:
    exam = await get_exam(db, exam_id)
    if data.name is not None:
        exam.name = data.name
    if data.exam_type is not None:
        exam.exam_type = data.exam_type
    if data.exam_date is not None:
        exam.exam_date = date.fromisoformat(data.exam_date) if data.exam_date else None
    if data.status is not None:
        exam.status = data.status
    await db.flush()
    return exam


def _exam_to_dict(exam: Exam) -> dict:
    return {
        "id": exam.id,
        "name": exam.name,
        "exam_type": exam.exam_type,
        "semester_id": exam.semester_id,
        "grade_id": exam.grade_id,
        "exam_date": exam.exam_date.isoformat() if exam.exam_date else None,
        "status": exam.status,
        "created_by": exam.created_by,
        "created_at": exam.created_at.isoformat() if exam.created_at else None,
        "subjects": [
            {
                "id": es.id,
                "subject_id": es.subject_id,
                "subject_name": es.subject.name if es.subject else "",
                "full_score": float(es.full_score),
                "weight": float(es.weight),
            }
            for es in (exam.exam_subjects or [])
        ],
    }
