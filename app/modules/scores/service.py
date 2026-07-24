"""Scores module — score entry, query, batch Excel import"""
import math, re
import pandas as pd
from io import BytesIO
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.exam import Exam, ExamSubject, Score
from app.models.base_data import Class, Student, Subject, Grade
from app.core.exceptions import NotFoundException, ForbiddenException


async def create_scores(
    db: AsyncSession, exam_id: int, scores_data: list,
    entered_by: int, allowed_class_ids: set[int] | None,
) -> dict:
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalar_one_or_none()
    if exam is None: raise NotFoundException("考试不存在")
    if exam.status == "locked": raise ForbiddenException("考试已锁定")

    result = await db.execute(select(ExamSubject).where(ExamSubject.exam_id == exam_id))
    exam_subjects = {es.subject_id: es for es in result.scalars().all()}

    created = 0; errors = []
    for entry in scores_data:
        sid = entry["student_id"]; subj_id = entry["subject_id"]; score_val = entry["total_score"]
        es = exam_subjects.get(subj_id)
        if es is None: errors.append({"student_id": sid, "reason": "科目不在考试中"}); continue
        if score_val > float(es.full_score):
            errors.append({"student_id": sid, "reason": f"分数{score_val}超过满分{es.full_score}"}); continue
        if allowed_class_ids is not None:
            result = await db.execute(select(Student.class_id).where(Student.id == sid))
            cid = result.scalar_one_or_none()
            if cid is None or cid not in allowed_class_ids:
                errors.append({"student_id": sid, "reason": "无权限"}); continue

        result = await db.execute(
            select(Score).where(and_(Score.exam_id == exam_id, Score.student_id == sid,
                                      Score.subject_id == subj_id)))
        existing = result.scalar_one_or_none()
        if existing: existing.total_score = score_val; existing.entered_by = entered_by
        else: db.add(Score(exam_id=exam_id, student_id=sid, subject_id=subj_id,
                            total_score=score_val, entered_by=entered_by))
        created += 1

    await db.flush()
    from app.modules.scores.tasks import calculate_ranks_async
    await calculate_ranks_async(exam_id)
    return {"count": created, "errors": errors}


async def get_class_scores(db: AsyncSession, exam_id: int, class_id: int) -> list[dict]:
    result = await db.execute(select(Student).where(Student.class_id == class_id))
    students = {s.id: s for s in result.scalars().all()}
    result = await db.execute(
        select(Score).options(selectinload(Score.subject)).where(
            and_(Score.exam_id == exam_id, Score.student_id.in_(students.keys())))
        .order_by(Score.student_id))
    scores = list(result.scalars().all())
    YWS = {"语文", "数学", "外语"}
    student_scores: dict[int, dict] = {}
    for s in scores:
        if s.student_id not in student_scores:
            st = students.get(s.student_id)
            student_scores[s.student_id] = {
                "student_id": s.student_id, "student_name": st.name if st else "",
                "student_no": st.student_no if st else "", "subjects": {},
                "yws": {}, "top3": {}, "total": 0,
                "yws_total": 0, "top3_total": 0,
                "class_rank": s.class_rank, "grade_rank": s.grade_rank,
            }
        subj_name = s.subject.name if s.subject else str(s.subject_id)
        score_val = float(s.total_score)
        student_scores[s.student_id]["subjects"][subj_name] = score_val
        student_scores[s.student_id]["total"] += score_val
        if subj_name in YWS:
            student_scores[s.student_id]["yws"][subj_name] = score_val
            student_scores[s.student_id]["yws_total"] += score_val

    # 计算每个学生的7选3
    for sid, data in student_scores.items():
        other = {k: v for k, v in data["subjects"].items() if k not in YWS}
        top3_items = sorted(other.items(), key=lambda x: x[1], reverse=True)[:3]
        data["top3"] = dict(top3_items)
        data["top3_total"] = sum(v for _, v in top3_items)

    # 查询语数外和7选3排名
    from app.models.audit import RankSnapshot
    student_ids = list(student_scores.keys())
    if student_ids:
        for rank_type, key in [("yuwai", "yws_rank"), ("top3", "top3_rank")]:
            result = await db.execute(
                select(RankSnapshot).where(
                    and_(RankSnapshot.exam_id == exam_id,
                         RankSnapshot.rank_type == rank_type,
                         RankSnapshot.student_id.in_(student_ids))))
            for rs in result.scalars().all():
                if rs.student_id in student_scores:
                    student_scores[rs.student_id][key] = rs.grade_rank

    result = list(student_scores.values())
    result.sort(key=lambda x: x.get("grade_rank") or 9999)
    return result


async def get_student_scores(db: AsyncSession, student_id: int,
                              semester_id: int | None = None) -> list[dict]:
    query = (select(Score).options(selectinload(Score.exam), selectinload(Score.subject))
             .where(Score.student_id == student_id))
    if semester_id: query = query.join(Exam).where(Exam.semester_id == semester_id)
    query = query.order_by(Score.exam_id.desc())
    result = await db.execute(query)
    scores = result.scalars().all()
    exam_scores: dict[int, dict] = {}
    for s in scores:
        eid = s.exam_id
        if eid not in exam_scores:
            exam_scores[eid] = {
                "exam_id": eid, "exam_name": s.exam.name if s.exam else "",
                "exam_date": s.exam.exam_date.isoformat() if s.exam and s.exam.exam_date else None,
                "subjects": {}, "total": 0, "grade_rank": s.grade_rank,
            }
        subj_name = s.subject.name if s.subject else str(s.subject_id)
        exam_scores[eid]["subjects"][subj_name] = float(s.total_score)
        exam_scores[eid]["total"] += float(s.total_score)
    return sorted(exam_scores.values(), key=lambda x: x["exam_date"] or "", reverse=True)


async def batch_import_excel(
    db: AsyncSession, file_content: bytes, exam_id: int,
) -> dict:
    """导入Excel成绩: 列=学籍号,姓名,班级,语文,数学,外语,政治,历史,地理,物理,化学,生物,技术"""
    df = pd.read_excel(BytesIO(file_content))
    df = df.where(pd.notna(df), None)

    # 科目映射 (列名→subject_id)
    result = await db.execute(
        select(ExamSubject, Subject.name).join(Subject).where(ExamSubject.exam_id == exam_id))
    subject_map: dict[str, dict] = {}
    for es, subj_name in result.all():
        subject_map[subj_name] = {"id": es.subject_id, "full_score": float(es.full_score)}

    # 班级映射
    result = await db.execute(select(Class))
    class_by_name: dict[str, int] = {c.name: c.id for c in result.scalars().all()}

    # 已有学生映射
    result = await db.execute(select(Student))
    student_by_no: dict[str, Student] = {s.student_no: s for s in result.scalars().all()}

    # 年级映射
    result = await db.execute(select(Grade))
    grades_by_name: dict[str, Grade] = {g.name: g for g in result.scalars().all()}

    columns = df.columns.tolist()
    created_students, created_scores, errors = 0, 0, []

    for idx, row in df.iterrows():
        sno_val = row.get("学籍号")
        if sno_val is None: errors.append({"row": idx+2, "reason":"缺少学籍号"}); continue
        sno = str(int(sno_val)) if isinstance(sno_val, float) else str(sno_val)
        sno = sno.rstrip('.0')
        if not sno: errors.append({"row": idx+2, "reason":"学籍号为空"}); continue

        name = str(row.get("姓名", "")) if pd.notna(row.get("姓名")) else ""

        # 班级
        cls_str = str(row.get("班级", "")).strip() if pd.notna(row.get("班级")) else ""
        class_id = class_by_name.get(cls_str)
        if not class_id and cls_str:
            for cn, cid in class_by_name.items():
                if cls_str == cn or cls_str in cn or cn in cls_str:
                    class_id = cid; break
        if not class_id and cls_str:
            grade_name = cls_str[:2]
            grade = grades_by_name.get(grade_name)
            if grade:
                new_c = Class(name=cls_str, grade_id=grade.id)
                db.add(new_c); await db.flush()
                class_id = new_c.id
                class_by_name[cls_str] = class_id
        if not class_id: errors.append({"row": idx+2, "reason":f"班级'{cls_str}'无法识别"}); continue

        # 学生
        student = student_by_no.get(sno)
        if not student:
            student = Student(student_no=sno, name=name or f"学生{sno[-4:]}", class_id=class_id)
            db.add(student); await db.flush()
            student_by_no[sno] = student; created_students += 1
        else:
            if name: student.name = name
            student.class_id = class_id

        # 成绩
        for col in columns:
            if col not in subject_map: continue
            val = row[col]
            if val is None: continue
            if isinstance(val, float) and (math.isnan(val) or math.isinf(val)): continue
            try:
                sv = float(val)
                sm = subject_map[col]
                if sv > sm["full_score"]:
                    errors.append({"row":idx+2,"reason":f"{col}分数{sv}超满分{sm['full_score']}"})
                    continue
                result = await db.execute(select(Score).where(and_(
                    Score.exam_id == exam_id, Score.student_id == student.id,
                    Score.subject_id == sm["id"])))
                ex = result.scalar_one_or_none()
                if ex: ex.total_score = sv
                else: db.add(Score(exam_id=exam_id, student_id=student.id,
                                    subject_id=sm["id"], total_score=sv, entered_by=1))
                created_scores += 1
            except (ValueError, TypeError): pass

        if (idx + 1) % 50 == 0: await db.flush()

    await db.flush()

    # 排名
    from app.modules.scores.tasks import calculate_ranks_async
    await calculate_ranks_async(exam_id)

    return {"created_students": created_students, "created_scores": created_scores,
            "total_rows": len(df), "errors": errors[:20]}
