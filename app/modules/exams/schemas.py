"""Exams & Score schemas"""
from pydantic import BaseModel, Field


class ExamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    exam_type: str = "midterm"
    semester_id: int
    grade_id: int
    exam_date: str | None = None
    subjects: list[dict] = []  # [{subject_id, full_score, weight}]


class ExamUpdate(BaseModel):
    name: str | None = None
    exam_type: str | None = None
    exam_date: str | None = None
    status: str | None = None


class ScoreEntry(BaseModel):
    student_id: int
    subject_id: int
    total_score: float = Field(..., ge=0, le=750)


class ScoresBatchCreate(BaseModel):
    exam_id: int
    scores: list[ScoreEntry]
