"""班级与学生查询路由"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db
from app.core.security import get_current_user, require_role
from app.core.response import success_response, paginated_response
from app.models.base_data import Class, Student

router = APIRouter(prefix="/api", tags=["班级学生"])


@router.get("/classes")
async def list_classes(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director", "teacher")),
):
    result = await db.execute(
        select(Class).order_by(Class.name)
    )
    classes = result.scalars().all()
    return success_response(data=[
        {"id": c.id, "name": c.name, "grade_id": c.grade_id}
        for c in classes
    ])


@router.get("/students")
async def list_students(
    class_id: int | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    conditions = []
    if class_id:
        conditions.append(Student.class_id == class_id)

    offset = (page - 1) * per_page
    query = select(Student).order_by(Student.student_no).offset(offset).limit(per_page)
    for cond in conditions:
        query = query.where(cond)

    result = await db.execute(query)
    students = result.scalars().all()

    count_q = select(func.count(Student.id))
    for cond in conditions:
        count_q = count_q.where(cond)
    result = await db.execute(count_q)
    total = result.scalar_one()

    return paginated_response(
        items=[{
            "id": s.id, "student_no": s.student_no, "name": s.name,
            "class_id": s.class_id, "status": s.status,
        } for s in students],
        total=total, page=page, per_page=per_page,
    )
