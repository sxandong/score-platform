"""考试与成绩模型 (核心)"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Date, Boolean, ForeignKey,
    UniqueConstraint, Numeric, DateTime,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    exam_type = Column(String(20), default="midterm")
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False)
    grade_id = Column(Integer, ForeignKey("grades.id"), nullable=False)
    exam_date = Column(Date, nullable=True)
    status = Column(String(15), default="draft")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    semester = relationship("Semester")
    grade = relationship("Grade")
    creator = relationship("User")
    exam_subjects = relationship("ExamSubject", back_populates="exam")
    scores = relationship("Score", back_populates="exam")


class ExamSubject(Base):
    __tablename__ = "exam_subjects"
    __table_args__ = (UniqueConstraint("exam_id", "subject_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    full_score = Column(Numeric(5, 1), default=100.0)
    weight = Column(Numeric(3, 2), default=1.00)

    exam = relationship("Exam", back_populates="exam_subjects")
    subject = relationship("Subject")


class Score(Base):
    __tablename__ = "scores"
    __table_args__ = (UniqueConstraint("exam_id", "student_id", "subject_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    total_score = Column(Numeric(6, 1), nullable=False)
    class_rank = Column(Integer, nullable=True)
    grade_rank = Column(Integer, nullable=True)
    entered_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    entered_at = Column(DateTime, default=datetime.now)
    is_approved = Column(Boolean, default=False)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    exam = relationship("Exam", back_populates="scores")
    student = relationship("Student")
    subject = relationship("Subject")
    enterer = relationship("User", foreign_keys=[entered_by])
    details = relationship("ScoreDetail", back_populates="score", cascade="all, delete-orphan")


class ScoreDetail(Base):
    __tablename__ = "score_details"

    id = Column(Integer, primary_key=True, autoincrement=True)
    score_id = Column(Integer, ForeignKey("scores.id", ondelete="CASCADE"), nullable=False)
    question_no = Column(String(20), nullable=False)
    knowledge_point = Column(String(200), default="")
    max_score = Column(Numeric(5, 1), nullable=False)
    actual_score = Column(Numeric(5, 1), nullable=False)

    score = relationship("Score", back_populates="details")
