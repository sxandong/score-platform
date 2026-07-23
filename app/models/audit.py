"""审计日志与排名快照模型"""
from datetime import datetime
from sqlalchemy import (
    Column, BigInteger, String, Integer, DateTime, ForeignKey, Numeric, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    target_type = Column(String(50), nullable=False)
    target_id = Column(BigInteger, nullable=True)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    ip_address = Column(String(50), default="")
    created_at = Column(DateTime, default=datetime.now, index=True)

    user = relationship("User")


class RankSnapshot(Base):
    __tablename__ = "rank_snapshots"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    exam_id = Column(BigInteger, ForeignKey("exams.id"), nullable=False, index=True)
    student_id = Column(BigInteger, ForeignKey("students.id"), nullable=False)
    total_score = Column(Numeric(7, 1), nullable=False)
    grade_rank = Column(Integer, nullable=False)
    class_rank = Column(Integer, nullable=False)
    rank_type = Column(String(10), default="total")
    subject_id = Column(BigInteger, ForeignKey("subjects.id"), nullable=True)
    calc_at = Column(DateTime, default=datetime.now)

    exam = relationship("Exam")
    student = relationship("Student")
    subject = relationship("Subject")
