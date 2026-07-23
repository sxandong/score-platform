"""Reports 模块 — Excel/PDF 导出"""
from io import BytesIO
import pandas as pd
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exam import Score, Exam
from app.models.base_data import Student, Class, Subject


async def export_score_sheet(
    db: AsyncSession, exam_id: int, class_id: int,
) -> BytesIO:
    """导出班级成绩单为Excel"""
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalar_one_or_none()
    exam_name = exam.name if exam else str(exam_id)

    result = await db.execute(
        select(Class).where(Class.id == class_id)
    )
    cls = result.scalar_one_or_none()
    class_name = cls.name if cls else ""

    result = await db.execute(
        select(Score).where(
            and_(Score.exam_id == exam_id)
        ).order_by(Score.student_id)
    )
    scores = result.scalars().all()

    # 构建DataFrame
    rows: dict[int, dict] = {}
    for s in scores:
        if s.student_id not in rows:
            result = await db.execute(
                select(Student).where(Student.id == s.student_id)
            )
            st = result.scalar_one_or_none()

            result = await db.execute(
                select(Subject.name).where(Subject.id == s.subject_id)
            )
            subj_name = result.scalar_one_or_none() or str(s.subject_id)

            if st and st.class_id == class_id:  # 只导出指定班级
                rows[s.student_id] = {
                    "学籍号": st.student_no,
                    "姓名": st.name,
                }
                rows[s.student_id][subj_name] = float(s.total_score)

    if not rows:
        output = BytesIO()
        pd.DataFrame().to_excel(output, index=False)
        output.seek(0)
        return output

    df = pd.DataFrame(list(rows.values()))

    # 计算总分和排名
    score_cols = [c for c in df.columns if c not in ("学籍号", "姓名")]
    if score_cols:
        df["总分"] = df[score_cols].sum(axis=1)
        df = df.sort_values("总分", ascending=False)
        df["班级排名"] = range(1, len(df) + 1)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=f"{exam_name}-{class_name}", index=False)
    output.seek(0)
    return output
