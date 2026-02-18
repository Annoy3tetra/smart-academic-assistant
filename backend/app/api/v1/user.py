from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.schemas_user import StudentCreate, SubjectCreate, MarkCreate, UserCreate, AttendanceCreate,UserLogin
from app.crud import student_crud,user_crud,analytics_crud
from app.ai_engine.performance_predictor import predict_performance
from app.models.user import Prediction, User
from app.core.security import verify_password, create_access_token, get_current_user, hash_password
from sqlalchemy.exc import IntegrityError
from fastapi.security import OAuth2PasswordRequestForm


router = APIRouter(
    prefix="/students",
    tags=["Students"]
)

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

    # Save or update prediction
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

