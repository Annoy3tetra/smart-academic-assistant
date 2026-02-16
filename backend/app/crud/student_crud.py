from sqlalchemy.orm import Session
from app.models import user
from app.schemas.schemas_user import StudentCreate, SubjectCreate, MarkCreate, AttendanceCreate
from sqlalchemy import func
from app.models.user import Mark, Attendance


def get_student_performance_summary(db, student_id: int):

    avg_score = db.query(func.avg(Mark.score))\
        .filter(Mark.student_id == student_id)\
        .scalar()

    total_subjects = db.query(func.count(Mark.id))\
        .filter(Mark.student_id == student_id)\
        .scalar()

    attendance = db.query(Attendance.attendance_percentage)\
        .filter(Attendance.student_id == student_id)\
        .scalar()

    return {
        "student_id": student_id,
        "average_score": float(avg_score) if avg_score else 0,
        "total_subjects": total_subjects or 0,
        "attendance_percentage": float(attendance) if attendance else 0
    }


def create_student(db: Session, student: StudentCreate):
    db_student = user.Student(
        user_id=student.user_id,
        branch=student.branch,
        year=student.year
    )

    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student



def create_subject(db: Session, subject: SubjectCreate):
    subject_db = user.Subject(name=subject.name)
    db.add(subject_db)
    db.commit()
    db.refresh(subject_db)
    return subject_db


def create_marks(db: Session, mark: MarkCreate):
    mark_db = user.Mark(
        student_id=mark.student_id,
        subject_id=mark.subject_id,
        semester=mark.semester,
        score=mark.score
    )
    db.add(mark_db)
    db.commit()
    db.refresh(mark_db)
    return mark_db


def get_marks_by_student(db: Session, student_id: int):
    return db.query(user.Mark).filter(
        user.Mark.student_id == student_id
    ).all()

def create_attendance(db:Session,attendance:AttendanceCreate):
    attendance_db = user.Attendance(
        student_id = attendance.student_id,
        attendance_percentage=attendance.attendance_percentage
    )
    db.add(attendance_db)
    db.commit()
    db.refresh(attendance_db)
    return attendance_db

def get_all_students(db: Session):
    return db.query(user.Student).all()
