"""基础数据模型: 年级/班级/学生/科目/学期/课程"""
from sqlalchemy import Column, Integer, String, Date, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class Grade(Base):
    __tablename__ = "grades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(20), nullable=False)
    stage = Column(String(10), default="senior")

    classes = relationship("Class", back_populates="grade")


class Class(Base):
    __tablename__ = "classes"
    __table_args__ = (UniqueConstraint("name", "grade_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    grade_id = Column(Integer, ForeignKey("grades.id"), nullable=False)
    head_teacher_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    grade = relationship("Grade", back_populates="classes")
    students = relationship("Student", back_populates="class_")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    student_no = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(50), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    status = Column(String(15), default="enrolled")
    electives = Column(String(50), default="")
    enrollment_year = Column(Integer, default=2026)  # 入学年份

    class_ = relationship("Class", back_populates="students")
    user = relationship("User")


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(30), nullable=False)
    sort_order = Column(Integer, default=0)


class Semester(Base):
    __tablename__ = "semesters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    is_current = Column(Boolean, default=False)


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (UniqueConstraint("teacher_id", "subject_id", "class_id", "semester_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False)

    teacher = relationship("User")
    subject = relationship("Subject")
    class_ = relationship("Class")
    semester = relationship("Semester")
