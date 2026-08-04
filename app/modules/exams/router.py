"""Exams 模块路由"""
import io
import tempfile
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.core.security import get_current_user, require_role
from app.core.response import success_response, error_response, paginated_response
from app.modules.exams.schemas import ExamCreate, ExamUpdate
from app.modules.exams import service

router = APIRouter(prefix="/api/exams", tags=["考试管理"])


@router.get("")
async def list_exams(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    grade_id: int | None = None,
    semester_id: int | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director", "teacher")),
):
    exams, total = await service.list_exams(
        db, page, per_page, grade_id, semester_id, status
    )
    return paginated_response(
        items=[service._exam_to_dict(e) for e in exams],
        total=total, page=page, per_page=per_page,
    )


@router.get("/{exam_id}")
async def get_exam(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director", "teacher")),
):
    exam = await service.get_exam(db, exam_id)
    return success_response(data=service._exam_to_dict(exam))


@router.post("")
async def create_exam(
    req: ExamCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director", "teacher")),
):
    exam = await service.create_exam(db, req, current_user.id)
    return success_response(data=service._exam_to_dict(exam), message="考试创建成功")


@router.put("/{exam_id}")
async def update_exam(
    exam_id: int,
    req: ExamUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director", "teacher")),
):
    exam = await service.update_exam(db, exam_id, req)
    return success_response(data=service._exam_to_dict(exam), message="考试更新成功")


@router.get("/{exam_id}/stats")
async def exam_stats(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director", "teacher")),
):
    """检查考试关联数据量"""
    from sqlalchemy import text
    result = await db.execute(text(
        "SELECT (SELECT COUNT(*) FROM scores WHERE exam_id=:eid) as scores,"
        " (SELECT COUNT(*) FROM exam_subjects WHERE exam_id=:eid) as subjects"
    ), {"eid": exam_id})
    row = result.fetchone()
    return success_response(data={"scores": row[0], "subjects": row[1]})


@router.get("/{exam_id}/cutoffs")
async def get_cutoffs(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director", "teacher")),
):
    """获取分数线(教师只读)"""
    from sqlalchemy import text

    result = await db.execute(text(
        "SELECT cutoff_type, score FROM score_cutoffs WHERE exam_id=:eid"
    ), {"eid": exam_id})
    saved: dict[str, float] = {row[0]: float(row[1]) for row in result.fetchall()}

    CUTOFF_TYPES = [
        ("score_930", "930分数线"),
        ("special", "特控线(前20%)"),
        ("first", "一段线(前60%)"),
    ]
    SUBJ_NAMES = ['语文','数学','外语','政治','历史','地理','物理','化学','生物','技术']
    for sn in SUBJ_NAMES:
        CUTOFF_TYPES.append((f"subj_excellent_{sn}", f"{sn}优秀线"))
        CUTOFF_TYPES.append((f"subj_good_{sn}", f"{sn}良好线"))
    cutoffs = []
    for ct, name in CUTOFF_TYPES:
        cutoffs.append({
            "type": ct, "name": name,
            "score": saved.get(ct),
        })

    return success_response(data={"cutoffs": cutoffs})


class CutoffSave(BaseModel):
    cutoffs: dict = {}

@router.post("/{exam_id}/cutoffs")
async def save_cutoffs(
    exam_id: int,
    req: CutoffSave,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director")),
):
    """手动设置分数线(仅管理员/教学主管)"""
    from sqlalchemy import text
    values = req.cutoffs

    # 先删后插
    await db.execute(text("DELETE FROM score_cutoffs WHERE exam_id=:eid"), {"eid": exam_id})
    for ct, score in values.items():
        if score is not None and float(score) > 0:
            await db.execute(text(
                "INSERT INTO score_cutoffs (exam_id, cutoff_type, score) VALUES (:eid, :ct, :sc)"
            ), {"eid": exam_id, "ct": ct, "sc": float(score)})
    await db.commit()

    return success_response(message="分数线保存成功")


@router.delete("/{exam_id}")
async def delete_exam(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director")),
):
    await service.delete_exam(db, exam_id)
    return success_response(message="考试已删除")


@router.put("/{exam_id}/lock")
async def lock_exam(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director")),
):
    from app.modules.exams.schemas import ExamUpdate
    exam = await service.update_exam(db, exam_id, ExamUpdate(status="locked"))
    return success_response(data=service._exam_to_dict(exam), message="考试已锁定")


@router.get("/cutoffs/template")
async def download_cutoffs_template(
    exam_id: int = Query(..., description="考试ID"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director")),
):
    """下载分数线Excel模板"""
    import pandas as pd
    import urllib.parse
    from sqlalchemy import text

    result = await db.execute(text("SELECT name FROM exams WHERE id=:eid"), {"eid": exam_id})
    row = result.fetchone()
    exam_name = row[0] if row else "未知考试"

    # 构建模板数据
    exam_data = {
        "分数线类型": [
            "930分数线",
            "特控线(前20%)",
            "一段线(前60%)",
        ],
        "分数": ["", "", ""],
        "说明": ["填写930参考分数线", "填写特殊类型招生控制线", "填写第一段本科分数线"],
    }
    df_exam = pd.DataFrame(exam_data)

    subj_names = ['语文', '数学', '外语', '政治', '历史', '地理', '物理', '化学', '生物', '技术']
    subj_data = {"科目": [], "优秀线": [], "良好线": [], "说明": []}
    for sn in subj_names:
        subj_data["科目"].append(sn)
        subj_data["优秀线"].append("")
        subj_data["良好线"].append("")
        subj_data["说明"].append(f"{sn}科目优秀/良好分数线")

    df_subj = pd.DataFrame(subj_data)

    # 写入Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_exam.to_excel(writer, sheet_name="考试分数线", index=False, startrow=1)
        df_subj.to_excel(writer, sheet_name="学科分数线", index=False, startrow=1)

        # 调整列宽
        wb = writer.book
        for sheet_name in ["考试分数线", "学科分数线"]:
            ws = wb[sheet_name]
            ws.column_dimensions['A'].width = 25
            ws.column_dimensions['B'].width = 15
            ws.column_dimensions['C'].width = 40

        # 在Excel第一个单元格添加标题
        for sheet_name in ["考试分数线", "学科分数线"]:
            ws = wb[sheet_name]
            ws.cell(row=1, column=1, value=f"{exam_name} - 分数线导入模板")

    output.seek(0)
    excel_bytes = output.getvalue()
    safe_name = f"cutoffs_template_exam_{exam_id}.xlsx"
    cn_name = f"{exam_name}_分数线模板.xlsx"
    encoded_cn = urllib.parse.quote(cn_name)
    return StreamingResponse(
        iter([excel_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": (
                f"attachment; filename={safe_name}; "
                f"filename*=UTF-8''{encoded_cn}"
            ),
        },
    )


@router.post("/cutoffs/import")
async def import_cutoffs_excel(
    exam_id: int = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director")),
):
    """从Excel导入分数线"""
    import pandas as pd
    from sqlalchemy import text

    content = await file.read()

    # 检查该考试是否已有分数线
    check_result = await db.execute(
        text("SELECT COUNT(*) FROM score_cutoffs WHERE exam_id=:eid"),
        {"eid": exam_id},
    )
    existing_count = check_result.scalar()

    try:
        # 读取Excel
        df_exam = pd.read_excel(io.BytesIO(content), sheet_name="考试分数线", header=1)
        df_subj = pd.read_excel(io.BytesIO(content), sheet_name="学科分数线", header=1)
    except Exception as e:
        return error_response(400, f"Excel格式错误: {str(e)}")

    # 解析考试分数线
    type_map = {
        "930分数线": "score_930",
        "特控线(前20%)": "special",
        "一段线(前60%)": "first",
    }
    cutoffs: dict[str, float] = {}
    for _, row in df_exam.iterrows():
        name = str(row.get("分数线类型", "")).strip()
        score = row.get("分数")
        if name in type_map and pd.notna(score) and float(score) > 0:
            cutoffs[type_map[name]] = float(score)

    # 解析学科分数线
    SUBJ_NAMES = ['语文', '数学', '外语', '政治', '历史', '地理', '物理', '化学', '生物', '技术']
    for _, row in df_subj.iterrows():
        subject = str(row.get("科目", "")).strip()
        excellent = row.get("优秀线")
        good = row.get("良好线")
        if subject in SUBJ_NAMES:
            if pd.notna(excellent) and float(excellent) > 0:
                cutoffs[f"subj_excellent_{subject}"] = float(excellent)
            if pd.notna(good) and float(good) > 0:
                cutoffs[f"subj_good_{subject}"] = float(good)

    if not cutoffs:
        return error_response(400, "未从Excel中解析到有效的分数线数据")

    # 保存（先删后插）
    await db.execute(text("DELETE FROM score_cutoffs WHERE exam_id=:eid"), {"eid": exam_id})
    for ct, score in cutoffs.items():
        await db.execute(text(
            "INSERT INTO score_cutoffs (exam_id, cutoff_type, score) VALUES (:eid, :ct, :sc)"
        ), {"eid": exam_id, "ct": ct, "sc": score})
    await db.commit()

    msg = f"导入成功，共导入{len(cutoffs)}项分数线"
    if existing_count > 0:
        msg += f"（已覆盖原有{existing_count}项数据）"
    return success_response(message=msg)
