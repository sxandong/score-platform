"""基础数据管理: 年级 / 班级 / 学生"""
from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import pandas as pd
from io import BytesIO

from app.dependencies import get_db
from app.core.security import get_current_user, require_role
from app.core.response import success_response, paginated_response
from app.core.exceptions import NotFoundException, ValidationException
from app.models.base_data import Grade, Class, Student
from app.models.user import User

router = APIRouter(prefix="/api", tags=["基础数据管理"])

# ======================= Schemas =======================

class GradeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=20)
    stage: str = "senior"

class ClassCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    grade_id: int
    head_teacher_id: int | None = None

class StudentCreate(BaseModel):
    student_no: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=50)
    class_id: int
    user_id: int | None = None

class StudentUpdate(BaseModel):
    student_no: str | None = None
    name: str | None = None
    class_id: int | None = None
    status: str | None = None

# ======================= 年级 =======================

@router.get("/grades")
async def list_grades(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Grade).order_by(Grade.id))
    return success_response(data=[
        {"id": g.id, "name": g.name, "stage": g.stage} for g in result.scalars().all()
    ])

@router.post("/grades")
async def create_grade(
    req: GradeCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    result = await db.execute(select(Grade).where(Grade.name == req.name))
    if result.scalar_one_or_none():
        raise ValidationException("年级已存在")
    g = Grade(name=req.name, stage=req.stage)
    db.add(g); await db.flush()
    return success_response(data={"id": g.id, "name": g.name}, message="年级创建成功")

@router.put("/grades/{grade_id}")
async def update_grade(
    grade_id: int, req: GradeCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    result = await db.execute(select(Grade).where(Grade.id == grade_id))
    g = result.scalar_one_or_none()
    if not g: raise NotFoundException("年级不存在")
    g.name = req.name; g.stage = req.stage; await db.flush()
    return success_response(data={"id": g.id, "name": g.name}, message="年级更新成功")

@router.delete("/grades/{grade_id}")
async def delete_grade(
    grade_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    result = await db.execute(select(Grade).where(Grade.id == grade_id))
    g = result.scalar_one_or_none()
    if not g: raise NotFoundException("年级不存在")
    await db.delete(g); await db.flush()
    return success_response(message="年级已删除")

# ======================= 班级 =======================

@router.get("/classes")
async def list_classes(
    grade_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = select(Class)
    if grade_id: q = q.where(Class.grade_id == grade_id)
    q = q.order_by(Class.grade_id, Class.name)
    result = await db.execute(q)
    classes = result.scalars().all()
    return success_response(data=[{
        "id": c.id, "name": c.name, "grade_id": c.grade_id,
        "head_teacher_id": c.head_teacher_id,
    } for c in classes])

@router.post("/classes")
async def create_class(
    req: ClassCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    c = Class(name=req.name, grade_id=req.grade_id, head_teacher_id=req.head_teacher_id)
    db.add(c); await db.flush()
    return success_response(data={"id": c.id, "name": c.name}, message="班级创建成功")

@router.put("/classes/{class_id}")
async def update_class(
    class_id: int, req: ClassCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    result = await db.execute(select(Class).where(Class.id == class_id))
    c = result.scalar_one_or_none()
    if not c: raise NotFoundException("班级不存在")
    c.name = req.name; c.grade_id = req.grade_id
    c.head_teacher_id = req.head_teacher_id; await db.flush()
    return success_response(data={"id": c.id, "name": c.name}, message="班级更新成功")

@router.delete("/classes/{class_id}")
async def delete_class(
    class_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    result = await db.execute(select(Class).where(Class.id == class_id))
    c = result.scalar_one_or_none()
    if not c: raise NotFoundException("班级不存在")
    await db.delete(c); await db.flush()
    return success_response(message="班级已删除")

# ======================= 学生 =======================

@router.get("/students")
async def list_students(
    class_id: int | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    conditions = []
    if class_id: conditions.append(Student.class_id == class_id)
    if keyword: conditions.append(
        (Student.name.contains(keyword)) | (Student.student_no.contains(keyword))
    )
    offset = (page - 1) * per_page
    q = select(Student).order_by(Student.class_id, Student.student_no)
    for cnd in conditions: q = q.where(cnd)
    q = q.offset(offset).limit(per_page)
    result = await db.execute(q)
    students = result.scalars().all()

    count_q = select(func.count(Student.id))
    for cnd in conditions: count_q = count_q.where(cnd)
    result = await db.execute(count_q)
    total = result.scalar_one()

    # 预加载班级名称
    class_ids = {s.class_id for s in students}
    if class_ids:
        result = await db.execute(select(Class).where(Class.id.in_(class_ids)))
        class_map = {c.id: c.name for c in result.scalars().all()}
    else:
        class_map = {}

    return paginated_response(items=[{
        "id": s.id, "student_no": s.student_no, "name": s.name,
        "class_id": s.class_id, "class_name": class_map.get(s.class_id, ""),
        "status": s.status, "user_id": s.user_id,
    } for s in students], total=total, page=page, per_page=per_page)

@router.post("/students")
async def create_student(
    req: StudentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    result = await db.execute(select(Student).where(Student.student_no == req.student_no))
    if result.scalar_one_or_none(): raise ValidationException("学号已存在")
    s = Student(student_no=req.student_no, name=req.name,
                class_id=req.class_id, user_id=req.user_id)
    db.add(s); await db.flush()
    return success_response(data={"id": s.id, "name": s.name}, message="学生创建成功")

@router.put("/students/{student_id}")
async def update_student(
    student_id: int, req: StudentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    result = await db.execute(select(Student).where(Student.id == student_id))
    s = result.scalar_one_or_none()
    if not s: raise NotFoundException("学生不存在")
    if req.student_no is not None: s.student_no = req.student_no
    if req.name is not None: s.name = req.name
    if req.class_id is not None: s.class_id = req.class_id
    if req.status is not None: s.status = req.status
    await db.flush()
    return success_response(data={"id": s.id, "name": s.name}, message="学生更新成功")

@router.delete("/students/{student_id}")
async def delete_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    result = await db.execute(select(Student).where(Student.id == student_id))
    s = result.scalar_one_or_none()
    if not s: raise NotFoundException("学生不存在")
    await db.delete(s); await db.flush()
    return success_response(message="学生已删除")

@router.post("/students/batch")
async def batch_import_students(
    file: UploadFile = File(...),
    class_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """Excel批量导入学生: 列=学号,姓名[,班级ID]"""
    content = await file.read()
    try:
        df = pd.read_excel(BytesIO(content))
    except Exception as e:
        raise ValidationException(f"Excel解析失败: {e}")

    created, skipped, errors = 0, 0, []
    for idx, row in df.iterrows():
        sno = str(row.get("学号", row.get("student_no", ""))).strip()
        name = str(row.get("姓名", row.get("name", ""))).strip()
        if not sno or not name:
            errors.append({"row": idx + 2, "reason": "学号或姓名为空"})
            skipped += 1; continue

        cid = class_id or int(row.get("班级ID", row.get("class_id", 0)))
        if not cid:
            errors.append({"row": idx + 2, "reason": "未指定班级"})
            skipped += 1; continue

        result = await db.execute(select(Student).where(Student.student_no == sno))
        if result.scalar_one_or_none():
            skipped += 1; continue

        db.add(Student(student_no=sno, name=name, class_id=cid))
        created += 1

    await db.flush()
    return success_response(data={
        "created": created, "skipped": skipped, "errors": errors[:10],
    }, message=f"导入完成: 新增{created}, 跳过{skipped}")
