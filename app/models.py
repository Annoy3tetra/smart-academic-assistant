from .database import Base
from sqlalchemy import Integer,Column,String,ForeignKey,Float
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"
    id = Column(Integer,primary_key=True,index=True)
    email = Column(String,unique=True,index=True)
    password_hash = Column(String)
    role = Column(String)
    
    student = relationship("Student",back_populates="user",uselist=False)
    
class Student(Base):
    __tablename__ = "student"
    id = Column(Integer,primary_key=True,index=True)
    user_id = Column(Integer,ForeignKey("users.id"))
    branch = Column(String)
    year = Column(Integer)
    
    user = relationship("User",back_populates="student")
    mark = relationship("Mark",back_populates="student")
    attendance = relationship("Attendance",back_populates="student",uselist=False)
    prediction = relationship("Prediction",back_populates="student",uselist=False)
    
    
class Subjects(Base):
    __tablename__ = "subjects"
    id = Column(Integer,primary_key=True,index=True)
    name = Column(String)
    
    mark = relationship("Mark",back_populates="subject")
    
class Mark(Base):
    __tablename__ = "marks"
    id = Column(Integer,primary_key=True,index=True)
    student_id = Column(Integer,ForeignKey("student.id"))
    subject_id = Column(Integer,ForeignKey("subjects.id"))
    semester = Column(Integer)
    score = Column(Float)
    
    subject = relationship("Subjects",back_populates="mark")
    student = relationship("Student",back_populates="mark")
    
class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer,primary_key=True,index=True)
    student_id = Column(Integer,ForeignKey("student.id"))
    attendance = Column(Float)
    
    student = relationship("Student",back_populates="attendance")
    
class Prediction(Base):
    __tablename__ = "prediction"
    id = Column(Integer,primary_key=True,index=True)
    student_id = Column(Integer,ForeignKey("student.id"))
    predicted_score = Column(Float)
    risk_level = Column(String)
    
    student = relationship("Student",back_populates="prediction")