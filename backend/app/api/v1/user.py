from functools import lru_cache
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.schemas_user import (
    StudentCreate,
    SubjectCreate,
    MarkCreate,
    UserCreate,
    AttendanceCreate,
    UserLogin,
    PredictDirectRequest,
    CourseRecommendationRequest,
    CourseRecommendationResponse,
    RagQueryRequest,
)
from app.crud import student_crud,user_crud,analytics_crud
from app.ai_engine.performance_predictor import predict_performance
from app.ai_engine.placement_model import evaluate_placement_readiness
from app.ai_engine.course_recommender import recommend_courses_with_gemini
from app.models.user import Prediction, User
from app.core.security import verify_password, create_access_token, get_current_user, hash_password
from sqlalchemy.exc import IntegrityError
from fastapi.security import OAuth2PasswordRequestForm


router = APIRouter(
    prefix="/students",
    tags=["Students"]
)


@lru_cache(maxsize=1)
def _load_rag_generate_answer():
    repo_root = Path(__file__).resolve().parents[4]
    rag_engine_path = repo_root / "RAG MODEL" / "ml" / "rag" / "rag_engine.py"

    if not rag_engine_path.exists():
        raise FileNotFoundError(f"RAG engine not found at: {rag_engine_path}")

    spec = spec_from_file_location("rag_engine_module", rag_engine_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load RAG engine module spec")

    rag_module = module_from_spec(spec)
    spec.loader.exec_module(rag_module)

    generate_answer = getattr(rag_module, "generate_answer", None)
    if not callable(generate_answer):
        raise RuntimeError("generate_answer function missing in RAG engine")

    return generate_answer

@router.post('/')
def create_student(student: StudentCreate, db: Session = Depends(get_db)):
    return student_crud.create_student(db, student)


@router.post('/subjects')
def create_subject(subject: SubjectCreate, db: Session = Depends(get_db)):
    return student_crud.create_subject(db, subject)


@router.post('/marks')
def create_marks(mark: MarkCreate, db: Session = Depends(get_db)):
    return student_crud.create_marks(db, mark)

@router.post('/attendance')
def create_attendance(attendance:AttendanceCreate,db: Session = Depends(get_db)):
    return student_crud.create_attendance(db, attendance)

@router.post("/users")
def create_user(user: UserCreate, db: Session = Depends(get_db)):

    hashed_password = hash_password(user.password)

    new_user = User(
    name=user.name,
    email=user.email,
    password_hash=hashed_password,
    role=user.role
)

    db.add(new_user)

    try:
        db.commit()
        db.refresh(new_user)
        return new_user
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already exists")

@router.get("/predict-all")
def predict_all(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    return analytics_crud.predict_all_students(db)

@router.get("/{student_id}/placement-readiness")
def placement_readiness(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    return analytics_crud.get_placement_readiness(db, student_id)


@router.get('/{student_id}/marks')
def get_marks(student_id: int, db: Session = Depends(get_db)):
    return student_crud.get_marks_by_student(db, student_id)

@router.get("/{student_id}/predict")
def predict_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
    ):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    summary = student_crud.get_student_performance_summary(db, student_id)

    predicted_score, risk = predict_performance(
        summary["average_score"],
        summary["attendance_percentage"],
        summary["total_subjects"]
    )

    existing = db.query(Prediction).filter(Prediction.student_id == student_id).first()

    if existing:
        existing.predicted_score = predicted_score
        existing.risk_level = risk
    else:
        new_prediction = Prediction(
            student_id=student_id,
            predicted_score=predicted_score,
            risk_level=risk
        )
        db.add(new_prediction)

    db.commit()

    return {
        "student_id": student_id,
        "predicted_score": predicted_score,
        "risk_level": risk
    }

@router.post("/predict-direct")
def predict_direct(payload: PredictDirectRequest):
    if len(payload.subject_marks) < 4 or len(payload.subject_marks) > 7:
        raise HTTPException(status_code=422, detail="subject_marks must contain 4 to 7 values")
    if any(mark < 0 or mark > 100 for mark in payload.subject_marks):
        raise HTTPException(status_code=422, detail="Each subject mark must be between 0 and 100")

    total_subjects = len(payload.subject_marks)
    average_score = sum(payload.subject_marks) / total_subjects

    predicted_score, risk = predict_performance(
        average_score,
        payload.attendance,
        total_subjects
    )
    placement_readiness = evaluate_placement_readiness(
        average_score,
        payload.attendance,
        risk
    )

    return {
        "average_score": round(float(average_score), 2),
        "total_subjects": total_subjects,
        "predicted_score": predicted_score,
        "risk_level": risk,
        "placement_readiness": placement_readiness
    }


@router.post("/recommend-courses", response_model=CourseRecommendationResponse)
def recommend_courses(payload: CourseRecommendationRequest):
    subjects = [
        {"name": item.name.strip(), "score": float(item.score)}
        for item in payload.subjects
        if item.name.strip()
    ]
    if not subjects:
        raise HTTPException(status_code=422, detail="At least one valid subject is required")

    return recommend_courses_with_gemini(
        subjects=subjects,
        attendance=payload.attendance,
        top_n=payload.top_n,
    )


@router.post("/rag-query")
def rag_query(payload: RagQueryRequest):
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="Query cannot be empty")

    try:
        generate_answer = _load_rag_generate_answer()
        answer = generate_answer(query)
    except FileNotFoundError as err:
        raise HTTPException(status_code=500, detail=str(err)) from err
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"RAG processing failed: {err}") from err

    return {
        "query": query,
        "answer": answer
    }

@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):

    db_user = db.query(User).filter(User.email == form_data.username).first()

    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(form_data.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(
        data={
            "sub": str(db_user.id),
            "role": db_user.role
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/")
def get_students(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    return student_crud.get_all_students(db)

