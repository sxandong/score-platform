"""Reports module — Excel/PDF export"""
from io import BytesIO
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.core.security import require_role
from app.models.base_data import Student, Class
from app.modules.reports import service

router = APIRouter(prefix="/api/reports", tags=["Report Export"])


@router.get("/student-report")
async def student_report(
    student_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Export student exam history as HTML report"""
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        return JSONResponse({"code": 404, "message": "Student not found"})

    result = await db.execute(select(Class).where(Class.id == student.class_id))
    cls = result.scalar_one_or_none()
    class_name = cls.name if cls else ""

    from app.modules.analysis.service import student_trend
    from app.models.audit import RankSnapshot
    exams = await student_trend(db, student_id)
    if not exams:
        return JSONResponse({"code": 404, "message": "No scores"})

    # Add yuwai/top3 ranks
    for e in exams:
        for rt, key in [("yuwai", "yws_rank"), ("top3", "top3_rank")]:
            result2 = await db.execute(
                select(RankSnapshot.grade_rank).where(
                    RankSnapshot.exam_id == e["exam_id"],
                    RankSnapshot.student_id == student_id,
                    RankSnapshot.rank_type == rt,
                ).limit(1))
            rv = result2.scalar_one_or_none()
            e[key] = rv if rv else ""

    # Find subjects with actual scores
    used_subjs = set()
    for e in exams:
        for sn, sv in e.get("subjects", {}).items():
            if sv is not None and sv != "":
                used_subjs.add(sn)
    ALL_SUBJS = ['语文','数学','外语','政治','历史','地理','物理','化学','生物','技术']
    subj_names = [s for s in ALL_SUBJS if s in used_subjs]

    # Build table
    rows_html = ""
    for e in exams:
        cells = "".join(f"<td>{e['subjects'].get(sn,'')}</td>" for sn in subj_names)
        yws_rank = e.get("yws_rank","") or ""
        t3_rank = e.get("top3_rank","") or ""
        rows_html += (
            f"<tr><td>{e['exam_name']}</td><td>{e.get('exam_date','')}</td>"
            f"{cells}"
            f"<td><b>{e['total']}</b></td>"
            f"<td>{e.get('grade_rank','')}</td><td>{e.get('class_rank','')}</td>"
            f"<td><b>{e.get('yws_total','')}</b></td><td>{yws_rank}</td>"
            f"<td><b>{e.get('top3_total','')}</b></td><td>{t3_rank}</td>"
            f"</tr>")

    header_cells = "".join(f"<th>{sn}</th>" for sn in subj_names)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body{{font-family:"PingFang SC","Microsoft YaHei",sans-serif;font-size:14px;padding:20px;color:#333}}
h1{{text-align:center;font-size:22px;margin-bottom:4px;color:#1a5490}}
h2{{text-align:center;font-size:14px;color:#999;margin-top:0;margin-bottom:8px}}
.info{{text-align:center;font-size:14px;margin-bottom:20px;color:#555}}
.info span{{margin:0 12px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th,td{{border:1px solid #d0d7de;padding:6px 5px;text-align:center}}
th{{background:#1a5490;color:#fff;font-weight:600;font-size:13px}}
tr:nth-child(even){{background:#f6f8fa}}
tr:hover{{background:#e8f0fe}}
@page{{size:A4 landscape;margin:10mm}}
</style></head><body>
<h1>学生成绩报告</h1>
<h2>普通高中教学质量分析系统</h2>
<div class="info">
姓名: {student.name} | 学籍号: {student.student_no} | 班级: {class_name}
</div>
<table>
<tr><th>考试</th><th>日期</th>{header_cells}
<th>总分</th><th>年级排名</th><th>班级排名</th>
<th>语数外总分</th><th>语数外排名</th>
<th>7选3总分</th><th>7选3排名</th></tr>
{rows_html}
</table>
<p style="text-align:right;font-size:10px;color:#999;margin-top:16px">
报告生成时间: __NOW__
</p></body></html>"""

    from datetime import datetime
    html = html.replace("__NOW__", datetime.now().strftime("%Y-%m-%d %H:%M"))

    return StreamingResponse(
        BytesIO(html.encode("utf-8")),
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": "inline; filename=student_report.html"},
    )


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
            "Content-Disposition": f"attachment; filename=score_{exam_id}_{class_id}.xlsx"
        },
    )
