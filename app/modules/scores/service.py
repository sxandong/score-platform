"""Scores module — score entry, query, batch Excel import"""
import math
import pandas as pd
from io import BytesIO
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.exam import Exam, ExamSubject, Score
from app.models.base_data import Class, Student, Subject, Grade
from app.core.exceptions import NotFoundException, ForbiddenException
from app.core.constants import (
    YWYS_NAMES, DEFAULT_FULL_SCORE, EXCELLENT_RATIO, PASS_RATIO
)


async def create_scores(
    db: AsyncSession, exam_id: int, scores_data: list,
    entered_by: int, allowed_class_ids: set[int] | None,
) -> dict:
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalar_one_or_none()
    if exam is None:
        raise NotFoundException("考试不存在")
    if exam.status == "locked":
        raise ForbiddenException("考试已锁定")

    result = await db.execute(select(ExamSubject).where(ExamSubject.exam_id == exam_id))
    exam_subjects = {es.subject_id: es for es in result.scalars().all()}

    # 预查询所有学生的 class_id, 避免 N+1
    student_ids = {entry["student_id"] for entry in scores_data}
    class_map: dict[int, int] = {}
    if student_ids:
        result = await db.execute(
            select(Student.id, Student.class_id).where(Student.id.in_(student_ids))
        )
        class_map = {sid: cid for sid, cid in result.all()}

    created = 0
    errors = []
    for entry in scores_data:
        sid = entry["student_id"]
        subj_id = entry["subject_id"]
        score_val = entry["total_score"]
        es = exam_subjects.get(subj_id)
        if es is None:
            errors.append({"student_id": sid, "reason": "科目不在考试中"})
            continue
        if score_val > float(es.full_score):
            errors.append({"student_id": sid, "reason": f"分数{score_val}超过满分{es.full_score}"})
            continue
        if allowed_class_ids is not None:
            cid = class_map.get(sid)
            if cid is None or cid not in allowed_class_ids:
                errors.append({"student_id": sid, "reason": "无权限"})
                continue

        result = await db.execute(
            select(Score).where(and_(Score.exam_id == exam_id, Score.student_id == sid,
                                      Score.subject_id == subj_id)))
        existing = result.scalar_one_or_none()
        if existing:
            existing.total_score = score_val
            existing.entered_by = entered_by
        else:
            db.add(Score(exam_id=exam_id, student_id=sid, subject_id=subj_id,
                        total_score=score_val, entered_by=entered_by))
        created += 1

    await db.flush()
    from app.modules.scores.tasks import calculate_ranks, calculate_ranks_async
    try:
        calculate_ranks.delay(exam_id)
    except Exception:
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
    student_scores: dict[int, dict] = {}
    for s in scores:
        if s.student_id not in student_scores:
            st = students.get(s.student_id)
            student_scores[s.student_id] = {
                "student_id": s.student_id, "student_name": st.name if st else "",
                "student_no": st.student_no if st else "", "subjects": {},
                "total": 0, "yuwai_total": 0, "top3_total": 0,
                "class_rank": s.class_rank, "grade_rank": s.grade_rank,
            }
        subj_name = s.subject.name if s.subject else str(s.subject_id)
        score_val = float(s.total_score)
        student_scores[s.student_id]["subjects"][subj_name] = score_val
        student_scores[s.student_id]["total"] += score_val
        if subj_name in YWYS_NAMES or subj_name == "英语":
            student_scores[s.student_id]["yuwai_total"] += score_val

    # 计算每个学生的7选3
    for sid, data in student_scores.items():
        st = students.get(sid)
        electives_str = st.electives if st and st.electives else ""
        if electives_str:
            selected = [s.strip() for s in electives_str.split(",") if s.strip()]
            top3_sum = sum(data["subjects"].get(k, 0) for k in selected[:3])
            data["top3_total"] = top3_sum
        else:
            other = {k: v for k, v in data["subjects"].items() if k not in YWYS_NAMES and k != "英语"}
            top3_items = sorted(other.values(), reverse=True)[:3]
            data["top3_total"] = sum(top3_items)

    # 查询语数外和7选3排名
    from app.models.audit import RankSnapshot
    student_ids = list(student_scores.keys())
    if student_ids:
        for rank_type, key in [("yuwai", "yuwai_rank"), ("top3", "top3_rank")]:
            result = await db.execute(
                select(RankSnapshot).where(
                    and_(RankSnapshot.exam_id == exam_id,
                         RankSnapshot.rank_type == rank_type,
                         RankSnapshot.student_id.in_(student_ids))))
            rank_map = {rs.student_id: rs.grade_rank for rs in result.scalars().all()}
            for sid, data in student_scores.items():
                data[key] = rank_map.get(sid)

    result_list = list(student_scores.values())
    result_list.sort(key=lambda x: x.get("grade_rank") or 9999)
    return result_list


async def get_student_scores(db: AsyncSession, student_id: int,
                              semester_id: int | None = None) -> list[dict]:
    query = (select(Score).options(selectinload(Score.exam), selectinload(Score.subject))
             .where(Score.student_id == student_id))
    if semester_id:
        query = query.join(Exam).where(Exam.semester_id == semester_id)
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
    entered_by: int,
) -> dict:
    """导入Excel成绩: 列=学籍号,姓名,班级,语文,数学,外语,政治,历史,地理,物理,化学,生物,技术

    性能优化:
      1. 一次性预加载 ExamSubject / Class / Student / Grade / Score 数据到内存
      2. 用字典做 O(1) 查找，避免 N+1 查询
      3. 使用 bulk_mappings 批量 upsert 成绩，flush 按批次提交
    """
    import time
    t0 = time.time()

    def _read_sno(x):
        if pd.isna(x):
            return ''
        if isinstance(x, (int, float)):
            return str(int(x)).zfill(12)
        s = str(x).strip()
        if 'E' in s.upper() or 'e' in s:
            return str(int(float(s))).zfill(12)
        return s

    converters = {}
    for col_hint in ('学籍号', '学号', 'student_no'):
        converters[col_hint] = _read_sno

    df = pd.read_excel(BytesIO(file_content), converters=converters)
    df = df.where(pd.notna(df), None)

    # ---------- 1. 一次性预加载所有依赖数据 ----------
    # 科目映射: 名称 -> {id, full_score}
    result = await db.execute(
        select(ExamSubject, Subject.name).join(Subject).where(ExamSubject.exam_id == exam_id))
    subject_map: dict[str, dict] = {}
    for es, subj_name in result.all():
        subject_map[subj_name] = {"id": es.subject_id, "full_score": float(es.full_score)}

    # 年级映射
    result = await db.execute(select(Grade))
    grades_by_name: dict[str, Grade] = {g.name: g for g in result.scalars().all()}

    # 班级映射: 名称 -> id (预加载全部)
    result = await db.execute(select(Class))
    class_by_name: dict[str, int] = {c.name: c.id for c in result.scalars().all()}

    # 已有学生映射: 学籍号 -> Student
    result = await db.execute(select(Student))
    student_by_no: dict[str, Student] = {s.student_no: s for s in result.scalars().all()}

    # 已有成绩映射: (student_id, subject_id) -> Score (预加载全部当前考试的成绩，避免N+1)
    result = await db.execute(
        select(Score).where(Score.exam_id == exam_id))
    existing_score_map: dict[tuple, Score] = {
        (s.student_id, s.subject_id): s for s in result.scalars().all()
    }

    # ---------- 2. 构建班级名 -> id 的精确/模糊查找缓存 ----------
    # 预先构建按后缀匹配映射，避免在循环中 O(n*m) 扫描
    class_by_suffix: dict[str, int] = {}
    for cn, cid in class_by_name.items():
        # 去掉年级前缀如 "高一(1)班" -> 后缀 "(1)班"
        for start in range(1, min(6, len(cn))):
            key = cn[start:]
            if key:
                class_by_suffix[key] = cid

    columns = df.columns.tolist()
    created_students, created_scores, updated_scores, skipped_same, errors = 0, 0, 0, 0, []

    # ---------- 3. 预遍历: 处理每行 ----------
    # 先收集需要新建的班级（避免循环内 flush）
    new_classes: dict[str, int] = {}  # cls_str -> class_id
    new_students: list[Student] = []

    def _resolve_class(cls_str: str) -> int | None:
        """解析班级: 精确匹配 -> 包含匹配 -> 后缀匹配 -> 新建"""
        if not cls_str:
            return None
        # 精确
        if cls_str in class_by_name:
            return class_by_name[cls_str]
        # 已在本轮预创建
        if cls_str in new_classes:
            return new_classes[cls_str]
        # 包含匹配 (短名 in 长名)
        for cn, cid in class_by_name.items():
            if cls_str == cn or cls_str in cn or cn in cls_str:
                return cid
        # 后缀匹配
        for suf, cid in class_by_suffix.items():
            if cls_str.endswith(suf) or suf.endswith(cls_str):
                return cid
        # 尝试根据年级名新建班级
        grade_name = cls_str[:2]
        grade = grades_by_name.get(grade_name)
        if grade:
            # 先挂起，稍后批量创建
            new_classes[cls_str] = -1  # 占位
            return -1  # 标记为待创建
        return None

    # 第一遍: 解析所有班级 / 学生 (不写成绩)
    row_contexts = []  # 每行解析后的上下文
    for idx, row in df.iterrows():
        sno_val = row.get("学籍号")
        if sno_val is None or str(sno_val).strip() == '' or str(sno_val) == 'nan':
            errors.append({"row": idx + 2, "reason": "缺少学籍号"})
            row_contexts.append(None)
            continue
        sno = str(sno_val).strip()
        if not sno:
            errors.append({"row": idx + 2, "reason": "学籍号为空"})
            row_contexts.append(None)
            continue

        name_val = row.get("姓名", "")
        name = str(name_val).strip() if name_val and str(name_val) != 'nan' else ""

        cls_val = row.get("班级", "")
        cls_str = str(cls_val).strip() if cls_val and str(cls_val) != 'nan' else ""

        class_id = _resolve_class(cls_str)
        if class_id is None:
            errors.append({"row": idx + 2, "reason": f"班级'{cls_str}'无法识别"})
            row_contexts.append(None)
            continue

        row_contexts.append({
            "idx": idx, "sno": sno, "name": name,
            "cls_str": cls_str, "class_id": class_id,
        })

    # ---------- 4. 批量创建缺失的班级 ----------
    if new_classes:
        # 为每个待创建班级分配ID (先flush以获取自增ID)
        for cls_str, _ in list(new_classes.items()):
            grade_name = cls_str[:2]
            grade = grades_by_name.get(grade_name)
            if not grade:
                # 找不到年级的跳过
                new_classes[cls_str] = None
                continue
            new_c = Class(name=cls_str, grade_id=grade.id)
            db.add(new_c)
        await db.flush()
        for cls_str, c in [(k, v) for k, v in new_classes.items() if v == -1]:
            # 查找刚创建的班级
            result = await db.execute(select(Class).where(Class.name == cls_str))
            cobj = result.scalar_one_or_none()
            if cobj:
                new_classes[cls_str] = cobj.id
                class_by_name[cls_str] = cobj.id

    # ---------- 5. 确定每行的实际 class_id (替换占位符 -1) ----------
    valid_contexts = []
    for ctx in row_contexts:
        if ctx is None:
            continue
        if ctx["class_id"] == -1:
            ctx["class_id"] = new_classes.get(ctx["cls_str"])
            if not ctx["class_id"]:
                errors.append({"row": ctx["idx"] + 2, "reason": f"班级'{ctx['cls_str']}'创建失败"})
                continue
        valid_contexts.append(ctx)

    # ---------- 6. 批量创建/更新学生 ----------
    for ctx in valid_contexts:
        sno = ctx["sno"]
        student = student_by_no.get(sno)
        if not student:
            student = Student(
                student_no=sno,
                name=ctx["name"] or f"学生{sno[-4:]}",
                class_id=ctx["class_id"],
            )
            db.add(student)
            new_students.append(student)
            student_by_no[sno] = student
            created_students += 1
        else:
            if ctx["name"]:
                student.name = ctx["name"]
            student.class_id = ctx["class_id"]

    # 先flush一次以获取新学生ID
    if new_students:
        await db.flush()

    # ---------- 7. 处理成绩 (内存校验 + 批量upsert) ----------
    # 为新学生建立 student_no -> id 的快速查找
    for ctx in valid_contexts:
        student = student_by_no.get(ctx["sno"])
        if not student:
            continue

        # 该生应导入的科目: 语数外 + 选科
        electives_set = set()
        if student.electives:
            electives_set = {s.strip() for s in student.electives.split(',') if s.strip()}
        allowed_subjects = YWYS_NAMES | electives_set

        for col in columns:
            if col not in subject_map:
                continue
            if col not in allowed_subjects:
                continue
            val = df.iloc[ctx["idx"]][col]
            if val is None:
                continue
            if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                continue
            try:
                sv = float(val)
            except (ValueError, TypeError):
                errors.append({"row": ctx["idx"] + 2, "reason": f"{col}成绩值无效"})
                continue

            sm = subject_map[col]
            if sv > sm["full_score"]:
                errors.append({"row": ctx["idx"] + 2,
                               "reason": f"{col}分数{sv}超满分{sm['full_score']}"})
                continue

            sid = student.id
            subj_id = sm["id"]
            ex = existing_score_map.get((sid, subj_id))
            if ex:
                if float(ex.total_score) != sv:
                    ex.total_score = sv
                    ex.entered_by = entered_by
                    updated_scores += 1
                else:
                    # 分数相同，跳过
                    skipped_same += 1
            else:
                new_score = Score(
                    exam_id=exam_id, student_id=sid,
                    subject_id=subj_id, total_score=sv,
                    entered_by=entered_by,
                )
                db.add(new_score)
                existing_score_map[(sid, subj_id)] = new_score
                created_scores += 1

    # ---------- 8. 最终flush并计算排名 ----------
    await db.flush()
    await db.commit()

    from app.modules.scores.tasks import calculate_ranks, calculate_ranks_async
    try:
        calculate_ranks.delay(exam_id)
    except Exception:
        try:
            await calculate_ranks_async(exam_id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Rank calculation failed: {e}", exc_info=True)

    elapsed = time.time() - t0
    return {
        "created_students": created_students,
        "created_scores": created_scores,
        "updated_scores": updated_scores,
        "skipped_same": skipped_same,
        "total_rows": len(df),
        "errors": errors[:50],
        "elapsed_seconds": round(elapsed, 2),
    }