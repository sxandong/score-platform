"""Reports 模块路由"""
from io import BytesIO
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.core.security import require_role
from app.models.base_data import Student, Class
from app.modules.reports import service

router = APIRouter(prefix="/api/reports", tags=["报表导出"])


@router.get("/student-report")
async def student_report(
    student_id: int,
    db: AsyncSession = Depends(get_db),
):
    """导出学生历次考试成绩PDF报告"""
    from jinja2 import Template
    from app.models.base_data import Student, Class

    # 获取学生信息
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        return JSONResponse({"code":404,"message":"学生不存在"})

    result = await db.execute(select(Class).where(Class.id == student.class_id))
    cls = result.scalar_one_or_none()
    class_name = cls.name if cls else ""

    from app.modules.analysis.service import student_trend
    exams = await student_trend(db, student_id)
    if not exams:
        return JSONResponse({"code":404,"message":"该学生没有考试成绩"})

    # 构建HTML
    rows_html = ""
    subj_names = ['语文','数学','外语','政治','历史','地理','物理','化学','生物','技术']
    for e in exams:
        cells = ""
        for sn in subj_names:
            cells += f"<td>{e['subjects'].get(sn,'')}</td>"
        rows_html += f"""
        <tr>
            <td>{e['exam_name']}</td>
            <td>{e.get('exam_date','')}</td>
            {cells}
            <td>{e['total']}</td>
            <td>{e.get('grade_rank','')}</td>
        </tr>"""

    header_cells = "".join(f"<th>{sn}</th>" for sn in subj_names)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body{{font-family:'PingFang SC','Microsoft YaHei',sans-serif;font-size:12px;padding:20px}}
h1{{text-align:center;font-size:18px;margin-bottom:4px}}
h2{{text-align:center;font-size:14px;color:#666;margin-top:0;margin-bottom:4px}}
.info{{text-align:center;font-size:12px;margin-bottom:16px;color:#333}}
table{{width:100%;border-collapse:collapse;font-size:10px}}
th,td{{border:1px solid #ccc;padding:4px 3px;text-align:center}}
th{{background:#e8f0fe;font-weight:bold}}
tr:nth-child(even){{background:#fafcfd}}
.total-row td{{font-weight:bold}}
@page{{size:A4;margin:12mm}}
</style></head><body>
<h1>学生成绩报告</h1>
<h2>普通高中教学质量分析系统</h2>
<div class="info">姓名: {student.name} | 学籍号: {student.student_no} | 班级: {class_name}</div>
<table>
<tr><th>考试</th><th>日期</th>{header_cells}<th>总分</th><th>年级排名</th></tr>
{rows_html}
</table>
<p style="text-align:right;font-size:10px;color:#999;margin-top:16px">报告生成时间: __NOW__</p>
</body></html>"""

    from datetime import datetime
    html = html.replace("__NOW__", datetime.now().strftime("%Y-%m-%d %H:%M"))

    return StreamingResponse(BytesIO(html.encode('utf-8')),
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": "inline; filename=student_report.html"})


@router.get("/score-sheet")
async def export_score_sheet(
    exam_id: int,
    class_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "director", "teacher")),
):
    output = await service.export_score_sheet(db, exam_id, class_id)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=成绩单_{exam_id}_{class_id}.xlsx"
        },
    )
