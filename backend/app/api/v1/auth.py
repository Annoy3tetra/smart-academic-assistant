from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, get_current_user, hash_password, verify_password
from app.models.user import AppDocument, Student, User

router = APIRouter(
    prefix="/students",
    tags=["Auth"],
)


def _db_unavailable_error(err: Exception) -> HTTPException:
    msg = str(getattr(err, "orig", err) or "").lower()
    if "does not exist" in msg or "undefined table" in msg:
        return HTTPException(
            status_code=503,
            detail="Database schema is not initialized. Run migrations or enable AUTO_CREATE_TABLES.",
        )

    if "network is unreachable" in msg and "supabase.co" in msg:
        return HTTPException(
            status_code=503,
            detail="Database unavailable. Render could not reach the direct Supabase host. Use the Supavisor pooler/IPv4 DATABASE_URL.",
        )

    return HTTPException(
        status_code=503,
        detail="Database unavailable. Verify DATABASE_URL, SSL settings, and that the PostgreSQL host is reachable.",
    )


class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=256)
    role: str = Field(default="Student", min_length=3, max_length=32)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


def _normalize_db_role(role: str) -> str:
    value = str(role or "").strip().lower()
    if value in {"admin", "prof", "professor", "hod"}:
        if value == "hod":
            return "hod"
        return "admin"
    return "student"


def _role_label(db_role: str) -> str:
    value = str(db_role or "").strip().lower()
    if value == "admin":
        return "Admin"
    if value == "hod":
        return "HOD"
    return "Student"


def _ensure_student_record(db: Session, user: User) -> None:
    if _normalize_db_role(user.role) != "student":
        return

    existing = db.query(Student).filter(Student.user_id == user.id).first()
    if existing:
        return

    db.add(Student(user_id=user.id, branch="General", year=1))
    db.commit()


def _ensure_user_doc(db: Session, user: User) -> AppDocument:
    doc_id = str(user.id)
    doc = db.query(AppDocument).filter(
        AppDocument.collection == "users",
        AppDocument.doc_id == doc_id
    ).first()

    base_payload = {
        "name": user.name,
        "email": user.email,
        "role": _role_label(user.role),
    }

    if doc:
        payload = dict(doc.payload or {})
        payload.update(base_payload)
        doc.payload = payload
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc

    payload = dict(base_payload)
    payload["created_at"] = None
    doc = AppDocument(
        collection="users",
        doc_id=doc_id,
        payload=payload
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def _serialize_user(user: User) -> dict:
    return {
        "uid": str(user.id),
        "name": user.name,
        "displayName": user.name,
        "email": user.email,
        "role": _role_label(user.role),
    }


@router.post("/signup")
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    role = _normalize_db_role(payload.role)

    try:
        existing = db.query(User).filter(User.email == email).first()
    except SQLAlchemyError as err:
        raise _db_unavailable_error(err) from err

    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    user = User(
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        role=role
    )
    db.add(user)

    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already exists")
    except SQLAlchemyError as err:
        db.rollback()
        raise _db_unavailable_error(err) from err

    _ensure_student_record(db, user)
    _ensure_user_doc(db, user)

    access_token = create_access_token(
        data={"sub": str(user.id), "role": role}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": _serialize_user(user),
    }


@router.post("/login-json")
def login_json(payload: LoginRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()

    try:
        user = db.query(User).filter(User.email == email).first()
    except SQLAlchemyError as err:
        raise _db_unavailable_error(err) from err

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    _ensure_student_record(db, user)
    _ensure_user_doc(db, user)

    access_token = create_access_token(
        data={"sub": str(user.id), "role": str(user.role).lower()}
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": _serialize_user(user),
    }


@router.get("/me")
def me(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.id == current_user["user_id"]).first()
    except SQLAlchemyError as err:
        raise _db_unavailable_error(err) from err

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_doc = _ensure_user_doc(db, user)

    return {
        "user": _serialize_user(user),
        "profile": user_doc.payload or {},
    }
