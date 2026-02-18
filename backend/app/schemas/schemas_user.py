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
