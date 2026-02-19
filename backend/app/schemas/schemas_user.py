from pydantic import BaseModel, EmailStr, Field
from typing import Literal

class StudentCreate(BaseModel):
    user_id : int
    branch : str
    year : int
    
class SubjectCreate(BaseModel):
    name : str
    
class MarkCreate(BaseModel):
    student_id : int
    subject_id : int
    semester : int
    score : float
    
class UserCreate(BaseModel):
    name : str
    email : EmailStr
    password: str = Field(min_length=6)
    role : Literal["student","admin"]
    
class AttendanceCreate(BaseModel):
    student_id : int
    attendance_percentage : float
    
class UserLogin(BaseModel):
    email: str
    password: str

class PredictDirectRequest(BaseModel):
    subject_marks: list[float]
    attendance: float = Field(ge=0, le=100)


class SubjectPerformance(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    score: float = Field(ge=0, le=100)


class CourseRecommendationRequest(BaseModel):
    subjects: list[SubjectPerformance] = Field(min_length=1, max_length=12)
    attendance: float | None = Field(default=None, ge=0, le=100)
    top_n: int = Field(default=4, ge=1, le=8)


class RecommendedCourse(BaseModel):
    title: str
    focus_subject: str
    provider: str
    course_url: str
    reason: str
    level: Literal["Beginner", "Intermediate", "Advanced"]
    priority: Literal["High", "Medium", "Low"]
    estimated_hours: int = Field(ge=1, le=300)


class CourseRecommendationResponse(BaseModel):
    model_used: str
    weak_subjects: list[str]
    recommendations: list[RecommendedCourse]


class RagQueryRequest(BaseModel):
    query: str = Field(min_length=3, max_length=2000)
