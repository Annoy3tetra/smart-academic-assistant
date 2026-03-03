from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, JSON, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String,nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)

    student = relationship(
        "Student",
        back_populates="user",
        uselist=False,
        cascade="all, delete"
    )


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    branch = Column(String, nullable=False)
    year = Column(Integer, nullable=False)

    user = relationship("User", back_populates="student")

    marks = relationship(
        "Mark",
        back_populates="student",
        cascade="all, delete"
    )

    attendance = relationship(
        "Attendance",
        back_populates="student",
        uselist=False,
        cascade="all, delete"
    )

    prediction = relationship(
        "Prediction",
        back_populates="student",
        uselist=False,
        cascade="all, delete"
    )


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    marks = relationship(
        "Mark",
        back_populates="subject",
        cascade="all, delete"
    )


class Mark(Base):
    __tablename__ = "marks"

    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    subject_id = Column(
        Integer,
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    semester = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)

    student = relationship("Student", back_populates="marks")
    subject = relationship("Subject", back_populates="marks")


class Attendance(Base):
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    attendance_percentage = Column(Float, nullable=False)

    student = relationship("Student", back_populates="attendance")


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    predicted_score = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)

    student = relationship("Student", back_populates="prediction")


class AppDocument(Base):
    __tablename__ = "app_documents"
    __table_args__ = (
        UniqueConstraint("collection", "doc_id", name="uq_app_documents_collection_doc_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    collection = Column(String, nullable=False, index=True)
    doc_id = Column(String, nullable=False, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
