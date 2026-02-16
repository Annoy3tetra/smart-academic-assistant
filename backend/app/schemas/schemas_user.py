from pydantic import BaseModel

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
    email : str
    password : str
    role : str
    
class AttendanceCreate(BaseModel):
    student_id : int
    attendance_percentage : float
    
class UserLogin(BaseModel):
    email: str
    password: str
