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

from app.ai_engine.placement_model import evaluate_placement_readiness

def get_placement_readiness(db: Session, student_id: int):

    summary = get_student_performance_summary(db, student_id)

    from app.ai_engine.performance_predictor import predict_performance

    predicted_score, risk = predict_performance(
        summary["average_score"],
        summary["attendance_percentage"],
        summary["total_subjects"]
    )

    placement_status = evaluate_placement_readiness(
        summary["average_score"],
        summary["attendance_percentage"],
        risk
    )

    return {
        "student_id": student_id,
        "average_score": summary["average_score"],
        "attendance_percentage": summary["attendance_percentage"],
        "risk_level": risk,
        "placement_status": placement_status
    }

