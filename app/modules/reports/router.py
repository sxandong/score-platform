"""Reports module - Excel/HTML export"""
from io import BytesIO
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.core.security import require_role
from app.models.base_data import Student, Class
from app.modules.reports import service

router = APIRouter(prefix="/api/reports", tags=["Report"])


@router.get("/student-report")
async def student_report(
    student_id: int,
    db: AsyncSession = Depends(get_db),
):
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

    for e in exams:
        for rt, key in [("yuwai", "yws_rank"), ("top3", "top3_rank")]:
            r2 = await db.execute(
                select(RankSnapshot.grade_rank).where(
                    RankSnapshot.exam_id == e["exam_id"],
                    RankSnapshot.student_id == student_id,
                    RankSnapshot.rank_type == rt).limit(1))
            rv = r2.scalar_one_or_none()
            e[key] = rv if rv else ""

    ALL_SUBJS = ["Chinese","Math","English","Politics","History","Geography","Physics","Chemistry","Biology","Tech"]
    used_subjs = set()
    for e in exams:
        for sn, sv in e.get("subjects", {}).items():
            if sv is not None and sv != "":
                used_subjs.add(sn)
    subj_names = [s for s in ALL_SUBJS if s in used_subjs]

    rows_html = ""
    for e in exams:
        cells = "".join(f"<td>{e['subjects'].get(sn,'')}</td>" for sn in subj_names)
        yw_r = e.get("yws_rank","") or ""
        t3_r = e.get("top3_rank","") or ""
        rows_html += (
            f"<tr><td>{e['exam_name']}</td><td>{e.get('exam_date','')}</td>{cells}"
            f"<td><b>{e['total']}</b></td>"
            f"<td>{e.get('grade_rank','')}</td><td>{e.get('class_rank','')}</td>"
            f"<td><b>{e.get('yws_total','')}</b></td><td>{yw_r}</td>"
            f"<td><b>{e.get('top3_total','')}</b></td><td>{t3_r}</td></tr>")

    header_cells = "".join(f"<th>{sn}</th>" for sn in subj_names)

    # Chart data
    sorted_exams = sorted(exams, key=lambda x: x.get("exam_date","") or "")
    chart_labels = [(e["exam_name"] or "")[:12] for e in sorted_exams]
    subj_series = {}
    for e in sorted_exams:
        for sn, sv in e.get("subjects",{}).items():
            if sv:
                subj_series.setdefault(sn, []).append(float(sv) if sv else None)
    chart_data = {
        "labels": chart_labels,
        "subjSeries": {k: v for k, v in subj_series.items()},
        "totalRanks": [e.get("grade_rank") for e in sorted_exams],
        "ywsRanks": [e.get("yws_rank") for e in sorted_exams],
        "t3Ranks": [e.get("top3_rank") for e in sorted_exams],
    }
    chart_json = json.dumps(chart_data, ensure_ascii=False)

    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
body{{font-family:"PingFang SC","Microsoft YaHei",sans-serif;font-size:14px;padding:20px;color:#333}}
h1{{text-align:center;font-size:22px;margin-bottom:4px;color:#1a5490}}
h2{{text-align:center;font-size:14px;color:#999;margin-top:0;margin-bottom:8px}}
h3{{color:#1a5490;margin-top:24px;font-size:16px}}
.info{{text-align:center;font-size:14px;margin-bottom:20px;color:#555}}
.info span{{margin:0 12px}}
table{{width:100%;border-collapse:collapse;font-size:13px;margin-bottom:20px}}
th,td{{border:1px solid #d0d7de;padding:6px 5px;text-align:center}}
th{{background:#1a5490;color:#fff;font-weight:600;font-size:13px}}
tr:nth-child(even){{background:#f6f8fa}}
.chart{{width:100%;height:360px;margin-bottom:16px}}
.chart-row{{display:flex;gap:12px;flex-wrap:wrap}}
.chart-row .chart{{flex:1;min-width:450px;height:340px}}
</style></head><body>
<h1>Student Score Report</h1>
<h2>High School Teaching Quality System</h2>
<div class="info"><span>Name: {student.name}</span><span>No: {student.student_no}</span><span>Class: {class_name}</span></div>
<table>
<tr><th>Exam</th><th>Date</th>{header_cells}
<th>Total</th><th>G-Rank</th><th>C-Rank</th>
<th>YWY Total</th><th>YWY Rank</th>
<th>Top3 Total</th><th>Top3 Rank</th></tr>
{rows_html}
</table>

<h3>Score Trend Charts</h3>
<div class="chart-row">
<div class="chart" id="chart-subj"></div>
<div class="chart" id="chart-total"></div>
</div>
<div class="chart-row">
<div class="chart" id="chart-yws"></div>
<div class="chart" id="chart-t3"></div>
</div>

<script>
var data = {chart_json};
var labels = data.labels;
var colors = ['#5470c6','#91cc75','#fac858','#ee6666','#73c0de','#3ba272','#fc8452','#9a60b4','#ea7ccc','#48b8d0'];
function makeChart(domId, series, yName, isRank) {{
  var el = document.getElementById(domId); if(!el) return;
  var opt = {{tooltip:{{trigger:'axis'}},legend:{{top:0,type:'scroll'}},
    grid:{{left:55,right:20,top:40,bottom:25}},
    xAxis:{{type:'category',data:labels}},
    yAxis:{{type:'value',name:yName,minInterval:1}} }};
  if(isRank) opt.yAxis.inverse = true;
  opt.series = series;
  echarts.init(el).setOption(opt);
}}
var subjArr = [], idx = 0;
for(var k in data.subjSeries) {{
  subjArr.push({{name:k,type:'line',data:data.subjSeries[k],smooth:true,
    itemStyle:{{color:colors[idx%10]}},label:{{show:true,fontSize:10}}}});
  idx++;
}}
makeChart('chart-subj', subjArr, 'Score', false);
makeChart('chart-total', [{{name:'Total Rank',type:'line',data:data.totalRanks,smooth:true,label:{{show:true,fontSize:10}}}}], 'Rank', true);
makeChart('chart-yws', [{{name:'YWY Rank',type:'line',data:data.ywsRanks,smooth:true,label:{{show:true,fontSize:10}}}}], 'Rank', true);
makeChart('chart-t3', [{{name:'Top3 Rank',type:'line',data:data.t3Ranks,smooth:true,label:{{show:true,fontSize:10}}}}], 'Rank', true);
</script>

<p style="text-align:right;font-size:10px;color:#999">Generated: {now}</p>
</body></html>"""

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
        headers={"Content-Disposition": f"attachment; filename=score_{exam_id}_{class_id}.xlsx"},
    )
