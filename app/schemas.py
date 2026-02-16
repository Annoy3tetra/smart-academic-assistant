from pydantic import BaseModel

class StudentCreate(BaseModel):
    branch : str
    year : int
    
class SubjectCreate(BaseModel):
    name : str
    
class MarkCreate(BaseModel):
    student_id : int
    subject_id : int
    semester : int
    score : float
    
        