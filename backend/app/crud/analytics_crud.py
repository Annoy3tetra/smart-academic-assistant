from app.models.user import Student
from app.ai_engine.performance_predictor import predict_performance
from app.crud.student_crud import get_student_performance_summary
from sqlalchemy.orm import Session

def predict_all_students(db: Session):

    students = db.query(Student).all()

    results = []

    for student in students:

        summary = get_student_performance_summary(db, student.id)

        predicted_score, risk = predict_performance(
            summary["average_score"],
            summary["attendance_percentage"],
            summary["total_subjects"]
        )

        results.append({
            "student_id": student.id,
            "predicted_score": predicted_score,
            "risk_level": risk
        })

    return results
