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

class ClassBatchCreate(BaseModel):
    grade_id: int
    names: list[str]

class ClassAutoGenerate(BaseModel):
    grade_id: int
    count: int = Field(..., ge=1, le=30)

class BatchDelete(BaseModel):
    ids: list[int]

class StudentPromote(BaseModel):
    from_grade_id: int
    target_grade_id: int

class StudentReassign(BaseModel):
    class_assignments: list[dict]  # [{student_id, new_class_id}]

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
    electives: str | None = None

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

@router.delete("/grades/batch-delete")
async def batch_delete_grades(
    req: BatchDelete,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    from sqlalchemy import delete as sql_delete
    for gid in req.ids:
        await db.execute(sql_delete(Student).where(
            Student.class_id.in_(select(Class.id).where(Class.grade_id == gid))
        ))
        await db.execute(sql_delete(Class).where(Class.grade_id == gid))
    await db.execute(sql_delete(Grade).where(Grade.id.in_(req.ids)))
    await db.commit()
    return success_response(message=f"已删除{len(req.ids)}个年级")


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

@router.delete("/grades/batch-delete")
async def batch_delete_grades(
    req: BatchDelete,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    from sqlalchemy import delete as sql_delete
    for gid in req.ids:
        await db.execute(sql_delete(Class).where(Class.grade_id == gid))
    await db.execute(sql_delete(Grade).where(Grade.id.in_(req.ids)))
    await db.commit()
    return success_response(message=f"已删除{len(req.ids)}个年级及其班级")


@router.delete("/grades/batch-delete")
async def batch_delete_grades(
    req: BatchDelete,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    from sqlalchemy import delete as sql_delete
    for gid in req.ids:
        await db.execute(sql_delete(Student).where(
            Student.class_id.in_(
                select(Class.id).where(Class.grade_id == gid)
            )
        ))
        await db.execute(sql_delete(Class).where(Class.grade_id == gid))
    await db.execute(sql_delete(Grade).where(Grade.id.in_(req.ids)))
    await db.commit()
    return success_response(message=f"已删除{len(req.ids)}个年级及关联班级学生")


# ======================= 班级 =======================

@router.get("/classes")
async def list_classes(
    grade_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = select(Class)
    if grade_id: q = q.where(Class.grade_id == grade_id)
    result = await db.execute(q)
    classes = list(result.scalars().all())
    # 按年级→班号数字排序(避免"10班"排在"2班"前面)
    import re
    def _sort_key(c):
        m = re.search(r'\((\d+)\)', c.name)
        num = int(m.group(1)) if m else 0
        return (c.grade_id, num)
    classes.sort(key=_sort_key)
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

@router.post("/classes/batch")
async def batch_create_classes(
    req: ClassBatchCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    created, skipped = 0, 0
    for name in req.names:
        name = name.strip()
        if not name: continue
        db.add(Class(name=name, grade_id=req.grade_id))
        created += 1
    await db.flush()
    return success_response(data={"created": created}, message=f"批量创建完成: 新增{created}个班级")


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

@router.delete("/classes/batch-delete")
async def batch_delete_classes(
    req: BatchDelete,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    from sqlalchemy import delete as sql_delete
    for cid in req.ids:
        await db.execute(sql_delete(Student).where(Student.class_id == cid))
    await db.execute(sql_delete(Class).where(Class.id.in_(req.ids)))
    await db.commit()
    return success_response(message=f"已删除{len(req.ids)}个班级及关联学生")


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


@router.post("/classes/auto-generate")
async def auto_generate_classes(
    req: ClassAutoGenerate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """按数量自动生成班级: 高三/15 → 高三(1)班~高三(15)班"""
    result = await db.execute(select(Grade).where(Grade.id == req.grade_id))
    grade = result.scalar_one_or_none()
    if not grade: raise NotFoundException("年级不存在")
    result = await db.execute(
        select(func.count(Class.id)).where(Class.grade_id == req.grade_id))
    existing = result.scalar_one()
    created = 0
    for i in range(existing + 1, existing + req.count + 1):
        db.add(Class(name=f"{grade.name}({i})班", grade_id=req.grade_id))
        created += 1
    await db.flush()
    return success_response(data={"created": created}, message=f"自动生成{created}个班级")


@router.post("/classes/batch-excel")
async def batch_import_classes(
    grade_id: int | None = None,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    content = await file.read()
    try: df = pd.read_excel(BytesIO(content))
    except Exception as e: raise ValidationException(f"Excel解析失败: {e}")
    created, skipped = 0, 0
    for _, row in df.iterrows():
        name = str(row.get("班级名称", row.get("name", ""))).strip()
        gid = grade_id or int(row.get("年级ID", row.get("grade_id", 0)))
        if not name or not gid: skipped += 1; continue
        db.add(Class(name=name, grade_id=gid)); created += 1
    await db.flush()
    return success_response(data={"created": created, "skipped": skipped},
                            message=f"导入完成: 新增{created}, 跳过{skipped}")


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
        "electives": s.electives or "",
    } for s in students], total=total, page=page, per_page=per_page)

@router.post("/students")
async def create_student(
    req: StudentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    result = await db.execute(select(Student).where(Student.student_no == req.student_no))
    if result.scalar_one_or_none(): raise ValidationException("学籍号已存在")
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
    if req.electives is not None: s.electives = req.electives
    await db.flush()
    return success_response(data={"id": s.id, "name": s.name}, message="学生更新成功")

@router.delete("/students/batch-delete")
async def batch_delete_students(
    req: BatchDelete,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    from sqlalchemy import delete as sql_delete
    await db.execute(sql_delete(Student).where(Student.id.in_(req.ids)))
    await db.commit()
    return success_response(message=f"已删除{len(req.ids)}个学生")


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
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """Excel导入: 列=学籍号,姓名,班级[,政治,历史,地理,物理,化学,生物,技术(1/0)]"""
    content = await file.read()
    try:
        df = pd.read_excel(BytesIO(content))
    except Exception as e:
        raise ValidationException(f"Excel解析失败: {e}")

    # 7选3科目列表
    ELEC_SUBJS = ['政治', '历史', '地理', '物理', '化学', '生物', '技术']

    # 预加载班级映射 (名称→ID)
    result = await db.execute(select(Class))
    class_by_name: dict[str, int] = {}
    class_by_id: dict[int, int] = {}
    for c in result.scalars().all():
        class_by_name[c.name] = c.id
        class_by_id[c.id] = c.id

    created, updated, skipped, errors = 0, 0, 0, []
    for idx, row in df.iterrows():
        sno_val = row.get("学籍号", row.get("学号", row.get("student_no", "")))
        if isinstance(sno_val, float):
            sno = str(int(sno_val)).zfill(12)
        else:
            sno = str(sno_val).strip().zfill(12)
        name = str(row.get("姓名", row.get("name", ""))).strip()
        if not sno or not name:
            errors.append({"row": idx + 2, "reason": "学籍号或姓名为空"})
            skipped += 1; continue

        # 识别班级
        cls_val = row.get("班级", row.get("班级名称", row.get("class_name",
                   row.get("班级ID", row.get("class_id", "")))))
        cls_str = str(cls_val).strip() if pd.notna(cls_val) else ""
        if cls_str:
            cid = class_by_name.get(cls_str) or class_by_id.get(
                int(cls_str) if cls_str.isdigit() else 0)
        else:
            cid = None
        if not cid:
            errors.append({"row": idx + 2, "reason": f"班级'{cls_str}'不存在"})
            skipped += 1; continue

        # 解析7选3选科
        selected = []
        for subj in ELEC_SUBJS:
            val = row.get(subj)
            if val is not None and int(val) == 1:
                selected.append(subj)
        electives_str = ','.join(selected)

        # 已存在则更新，不存在则新增
        result = await db.execute(select(Student).where(Student.student_no == sno))
        existing = result.scalar_one_or_none()
        if existing:
            existing.name = name
            existing.class_id = cid
            if electives_str:
                existing.electives = electives_str
            updated += 1
        else:
            db.add(Student(student_no=sno, name=name, class_id=cid,
                          electives=electives_str))
            created += 1

    await db.flush()
    return success_response(data={
        "created": created, "updated": updated, "skipped": skipped, "errors": errors[:10],
    }, message=f"导入完成: 新增{created}, 更新{updated}, 跳过{skipped}")


@router.post("/students/promote")
async def promote_students(
    req: StudentPromote,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """升年级: 按班号(括号内数字)匹配，如高一(3)班→高二(3)班"""
    from sqlalchemy import text
    import re

    def _class_number(c) -> int:
        m = re.search(r'\((\d+)\)', c.name)
        return int(m.group(1)) if m else 0

    result = await db.execute(
        select(Class).where(Class.grade_id.in_([req.from_grade_id, req.target_grade_id])))
    classes = list(result.scalars().all())

    src_classes = [c for c in classes if c.grade_id == req.from_grade_id]
    tgt_by_number = {_class_number(c): c.id for c in classes if c.grade_id == req.target_grade_id}

    migrated = 0
    for sc in src_classes:
        tgt_id = tgt_by_number.get(_class_number(sc))
        if tgt_id is None: continue
        result = await db.execute(
            select(func.count(Student.id)).where(Student.class_id == sc.id))
        count = result.scalar_one()
        if count == 0: continue
        await db.execute(text(
            "UPDATE students SET class_id = :tgt WHERE class_id = :src"
        ), {"tgt": tgt_id, "src": sc.id})
        migrated += count

    await db.commit()
    return success_response(data={"migrated": migrated}, message=f"升年级完成: {migrated}名学生")


@router.post("/students/reassign")
async def reassign_students(
    req: StudentReassign,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """批量重新分班: [{student_id, new_class_id}, ...]"""
    from sqlalchemy import text
    updated = 0
    for item in req.class_assignments:
        sid = item.get("student_id")
        cid = item.get("new_class_id")
        if sid and cid:
            await db.execute(text(
                "UPDATE students SET class_id = :cid WHERE id = :sid"
            ), {"cid": cid, "sid": sid})
            updated += 1
    await db.commit()
    return success_response(data={"updated": updated}, message=f"重新分班完成: {updated}名学生")
