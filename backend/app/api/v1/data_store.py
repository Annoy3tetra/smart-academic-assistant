from datetime import datetime, timezone
import math
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import AppDocument, Attendance, Mark, Prediction, Student, Subject, User

router = APIRouter(
    prefix="/data",
    tags=["DataStore"],
)

ALLOWED_COLLECTIONS = {"users", "predictions", "courses"}


class SetDocRequest(BaseModel):
    data: dict = Field(default_factory=dict)
    merge: bool = True


class AddDocRequest(BaseModel):
    data: dict = Field(default_factory=dict)


def _normalize_db_role(role: str) -> str:
    value = str(role or "").strip().lower()
    if value in {"admin", "prof", "professor"}:
        return "admin"
    if value == "hod":
        return "hod"
    return "student"


def _role_label(db_role: str) -> str:
    value = _normalize_db_role(db_role)
    if value == "admin":
        return "Admin"
    if value == "hod":
        return "HOD"
    return "Student"


def _is_admin_role(role: str) -> bool:
    return _normalize_db_role(role) in {"admin", "hod"}


def _assert_collection(collection: str) -> str:
    name = str(collection or "").strip().lower()
    if name not in ALLOWED_COLLECTIONS:
        raise HTTPException(status_code=400, detail="Unsupported collection")
    return name


def _replace_server_timestamps(value, now_iso: str):
    if isinstance(value, dict):
        if value.get("__server_timestamp__") is True and len(value) == 1:
            return now_iso
        return {k: _replace_server_timestamps(v, now_iso) for k, v in value.items()}
    if isinstance(value, list):
        return [_replace_server_timestamps(v, now_iso) for v in value]
    return value


def _deep_merge(existing, incoming):
    base = dict(existing or {})
    for key, value in (incoming or {}).items():
        if isinstance(base.get(key), dict) and isinstance(value, dict):
            base[key] = _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _ensure_user_doc(db: Session, user: User) -> None:
    doc_id = str(user.id)
    doc = db.query(AppDocument).filter(
        AppDocument.collection == "users",
        AppDocument.doc_id == doc_id
    ).first()

    payload = {
        "name": user.name,
        "email": user.email,
        "role": _role_label(user.role),
    }

    if doc:
        merged = dict(doc.payload or {})
        merged.update(payload)
        doc.payload = merged
        db.add(doc)
        db.commit()
        return

    db.add(AppDocument(collection="users", doc_id=doc_id, payload=payload))
    db.commit()


def _sync_all_user_docs(db: Session) -> None:
    users = db.query(User).all()
    existing_ids = {
        doc.doc_id
        for doc in db.query(AppDocument).filter(AppDocument.collection == "users").all()
    }

    changed = False
    for user in users:
        if str(user.id) in existing_ids:
            continue
        db.add(AppDocument(
            collection="users",
            doc_id=str(user.id),
            payload={
                "name": user.name,
                "email": user.email,
                "role": _role_label(user.role),
            },
        ))
        changed = True

    if changed:
        db.commit()


def _get_document(db: Session, collection: str, doc_id: str) -> AppDocument | None:
    return db.query(AppDocument).filter(
        AppDocument.collection == collection,
        AppDocument.doc_id == doc_id
    ).first()


def _assert_doc_access(current_user: dict, collection: str, doc_id: str, write: bool) -> None:
    role = str(current_user.get("role", "student"))
    current_uid = str(current_user.get("user_id"))
    is_admin = _is_admin_role(role)

    if collection == "courses":
        if write and not is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        return

    if collection == "users":
        if is_admin or doc_id == current_uid:
            return
        raise HTTPException(status_code=403, detail="Forbidden")

    if collection == "predictions":
        if is_admin:
            return
        if write:
            return
        # Read for non-admin is filtered later by owner check.
        return

    raise HTTPException(status_code=403, detail="Forbidden")


def _sync_user_table_from_user_doc(
    db: Session,
    current_user: dict,
    doc_id: str,
    payload: dict,
) -> None:
    db_user = db.query(User).filter(User.id == int(doc_id)).first()
    if not db_user:
        return

    is_admin = _is_admin_role(str(current_user.get("role", "")))
    is_self = str(current_user.get("user_id")) == str(doc_id)

    changed = False

    if "name" in payload:
        name = str(payload["name"] or "").strip()
        if name:
            db_user.name = name
            changed = True

    if is_admin and "email" in payload:
        email = str(payload["email"] or "").strip().lower()
        if email and email != db_user.email:
            db_user.email = email
            changed = True

    if "role" in payload:
        if not is_admin and is_self:
            payload["role"] = _role_label(db_user.role)
        elif is_admin:
            db_user.role = _normalize_db_role(str(payload["role"]))
            payload["role"] = _role_label(db_user.role)
            changed = True

    if changed:
        try:
            db.add(db_user)
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=400, detail="Email already exists")


def _to_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _to_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed


def _extract_subject_marks(payload: dict) -> list[tuple[str, float]]:
    raw = payload.get("subject_marks")
    if raw is None:
        raw = payload.get("subjectMarks")
    if raw is None:
        raw = payload.get("marks")
    if raw is None:
        return []

    pairs: list[tuple[str, float]] = []

    if isinstance(raw, dict):
        for subject, score in raw.items():
            name = str(subject or "").strip()
            numeric = _to_float(score)
            if not name or numeric is None or numeric < 0 or numeric > 100:
                continue
            pairs.append((name, numeric))
        return pairs

    if isinstance(raw, list):
        for idx, item in enumerate(raw):
            if isinstance(item, dict):
                name = str(item.get("subject") or item.get("name") or f"Subject {idx + 1}").strip()
                numeric = _to_float(item.get("mark", item.get("marks", item.get("score"))))
            else:
                name = f"Subject {idx + 1}"
                numeric = _to_float(item)

            if not name or numeric is None or numeric < 0 or numeric > 100:
                continue
            pairs.append((name, numeric))

    return pairs


def _extract_attendance(payload: dict) -> float | None:
    candidates = [
        payload.get("attendance"),
        (payload.get("last_prediction_input") or {}).get("attendance") if isinstance(payload.get("last_prediction_input"), dict) else None,
        (payload.get("input_data") or {}).get("attendance") if isinstance(payload.get("input_data"), dict) else None,
    ]
    for item in candidates:
        numeric = _to_float(item)
        if numeric is None:
            continue
        if 0 <= numeric <= 100:
            return numeric
    return None


def _extract_prediction(payload: dict) -> tuple[float | None, str | None]:
    score = _to_float(payload.get("predicted_score"))
    risk = payload.get("risk_level")

    if score is None and isinstance(payload.get("latest_prediction"), dict):
        latest = payload.get("latest_prediction") or {}
        score = _to_float(latest.get("predicted_score"))
        risk = risk or latest.get("risk_level")

    if score is None:
        return None, None

    risk_text = str(risk or "").strip().upper()
    if not risk_text:
        risk_text = "MEDIUM"
    return score, risk_text


def _resolve_semester(payload: dict, student: Student) -> int:
    candidates = [
        payload.get("semester"),
        payload.get("current_semester"),
        (payload.get("last_prediction_input") or {}).get("semester") if isinstance(payload.get("last_prediction_input"), dict) else None,
        (payload.get("input_data") or {}).get("semester") if isinstance(payload.get("input_data"), dict) else None,
        student.year,
    ]
    for item in candidates:
        parsed = _to_int(item)
        if parsed is None:
            continue
        if 1 <= parsed <= 12:
            return parsed
    return 1


def _get_or_create_student(db: Session, user_id: int, payload: dict) -> Student:
    student = db.query(Student).filter(Student.user_id == user_id).first()
    if student:
        branch = str(payload.get("branch") or "").strip()
        if branch:
            student.branch = branch
        year = _to_int(payload.get("year"))
        if year is not None and 1 <= year <= 8:
            student.year = year
        db.add(student)
        return student

    branch = str(payload.get("branch") or "General").strip() or "General"
    year = _to_int(payload.get("year"))
    if year is None or year < 1 or year > 8:
        year = 1

    student = Student(user_id=user_id, branch=branch, year=year)
    db.add(student)
    db.flush()
    return student


def _get_or_create_subject(db: Session, subject_name: str) -> Subject:
    cleaned = str(subject_name or "").strip()
    if not cleaned:
        raise ValueError("Subject name cannot be empty.")

    subject = db.query(Subject).filter(Subject.name == cleaned).first()
    if subject:
        return subject

    subject = Subject(name=cleaned)
    db.add(subject)
    db.flush()
    return subject


def _sync_marks_to_relational(db: Session, student: Student, payload: dict) -> bool:
    entries = _extract_subject_marks(payload)
    if not entries:
        return False

    semester = _resolve_semester(payload, student)

    db.query(Mark).filter(Mark.student_id == student.id).delete(synchronize_session=False)
    for subject_name, score in entries:
        subject = _get_or_create_subject(db, subject_name)
        db.add(
            Mark(
                student_id=student.id,
                subject_id=subject.id,
                semester=semester,
                score=float(score),
            )
        )
    return True


def _sync_attendance_to_relational(db: Session, student: Student, payload: dict) -> bool:
    attendance = _extract_attendance(payload)
    if attendance is None:
        return False

    row = db.query(Attendance).filter(Attendance.student_id == student.id).first()
    if row:
        row.attendance_percentage = float(attendance)
        db.add(row)
    else:
        db.add(Attendance(student_id=student.id, attendance_percentage=float(attendance)))
    return True


def _sync_prediction_to_relational(db: Session, student: Student, payload: dict) -> bool:
    score, risk_level = _extract_prediction(payload)
    if score is None or not risk_level:
        return False

    row = db.query(Prediction).filter(Prediction.student_id == student.id).first()
    if row:
        row.predicted_score = float(score)
        row.risk_level = risk_level
        db.add(row)
    else:
        db.add(
            Prediction(
                student_id=student.id,
                predicted_score=float(score),
                risk_level=risk_level,
            )
        )
    return True


def _sync_user_doc_to_relational(db: Session, doc_id: str, payload: dict) -> bool:
    if not str(doc_id).isdigit():
        return False

    user_id = int(doc_id)
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        return False

    student = _get_or_create_student(db, user_id=user_id, payload=payload)
    changed = True
    changed = _sync_marks_to_relational(db, student, payload) or changed
    changed = _sync_attendance_to_relational(db, student, payload) or changed
    changed = _sync_prediction_to_relational(db, student, payload) or changed
    return changed


def _sync_prediction_doc_to_relational(db: Session, payload: dict) -> bool:
    owner_id = str(payload.get("user_id") or payload.get("uid") or payload.get("userId") or "").strip()
    if not owner_id.isdigit():
        return False

    user_id = int(owner_id)
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        return False

    student = _get_or_create_student(db, user_id=user_id, payload=payload)
    changed = True
    changed = _sync_prediction_to_relational(db, student, payload) or changed
    changed = _sync_attendance_to_relational(db, student, payload) or changed

    # Prediction event may also include input subject marks.
    if isinstance(payload.get("input_data"), dict):
        input_payload = dict(payload.get("input_data") or {})
        if "subject_marks" in input_payload and "subject_marks" not in payload:
            merged = dict(payload)
            merged["subject_marks"] = input_payload.get("subject_marks")
            changed = _sync_marks_to_relational(db, student, merged) or changed

    return changed


def _serialize_document(doc: AppDocument) -> dict:
    return {
        "id": doc.doc_id,
        "data": dict(doc.payload or {}),
    }


@router.get("/docs/{collection}/{doc_id}")
def get_doc(
    collection: str,
    doc_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    collection = _assert_collection(collection)
    _assert_doc_access(current_user, collection, doc_id, write=False)

    if collection == "users":
        db_user = db.query(User).filter(User.id == int(doc_id)).first() if str(doc_id).isdigit() else None
        if db_user:
            _ensure_user_doc(db, db_user)

    doc = _get_document(db, collection, doc_id)
    if not doc:
        return {"id": doc_id, "exists": False, "data": {}}

    if collection == "predictions" and not _is_admin_role(current_user.get("role", "")):
        owner = str((doc.payload or {}).get("user_id", ""))
        if owner != str(current_user.get("user_id")):
            raise HTTPException(status_code=403, detail="Forbidden")

    return {"id": doc_id, "exists": True, "data": dict(doc.payload or {})}


@router.put("/docs/{collection}/{doc_id}")
def set_doc(
    collection: str,
    doc_id: str,
    request: SetDocRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    collection = _assert_collection(collection)
    _assert_doc_access(current_user, collection, doc_id, write=True)

    now_iso = datetime.now(timezone.utc).isoformat()
    incoming = _replace_server_timestamps(dict(request.data or {}), now_iso)

    if collection == "users" and not _is_admin_role(current_user.get("role", "")):
        incoming.pop("email", None)
        if "role" in incoming:
            incoming.pop("role")

    doc = _get_document(db, collection, doc_id)
    if doc:
        payload = _deep_merge(doc.payload or {}, incoming) if request.merge else incoming
        doc.payload = payload
        db.add(doc)
    else:
        payload = incoming
        doc = AppDocument(collection=collection, doc_id=doc_id, payload=payload)
        db.add(doc)

    db.commit()
    db.refresh(doc)

    sync_changed = False
    if collection == "users" and str(doc_id).isdigit():
        _sync_user_table_from_user_doc(db, current_user, doc_id, doc.payload)
        sync_changed = _sync_user_doc_to_relational(db, doc_id, doc.payload) or sync_changed
        doc = _get_document(db, collection, doc_id)
    elif collection == "predictions":
        sync_changed = _sync_prediction_doc_to_relational(db, doc.payload) or sync_changed

    if sync_changed:
        try:
            db.commit()
        except IntegrityError as err:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Relational sync failed: {err}") from err

    return {"id": doc_id, "data": dict(doc.payload or {})}


@router.post("/collections/{collection}")
def add_doc(
    collection: str,
    request: AddDocRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    collection = _assert_collection(collection)
    _assert_doc_access(current_user, collection, "__new__", write=True)

    now_iso = datetime.now(timezone.utc).isoformat()
    payload = _replace_server_timestamps(dict(request.data or {}), now_iso)

    if collection == "predictions" and not _is_admin_role(current_user.get("role", "")):
        payload["user_id"] = str(current_user.get("user_id"))

    doc_id = uuid.uuid4().hex
    doc = AppDocument(
        collection=collection,
        doc_id=doc_id,
        payload=payload,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    if collection == "predictions":
        try:
            if _sync_prediction_doc_to_relational(db, doc.payload):
                db.commit()
        except IntegrityError as err:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Relational sync failed: {err}") from err

    return _serialize_document(doc)


@router.get("/collections/{collection}")
def list_docs(
    collection: str,
    where_field: str | None = Query(default=None),
    where_op: str | None = Query(default=None),
    where_value: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    collection = _assert_collection(collection)

    if collection == "users":
        _sync_all_user_docs(db)

    docs = db.query(AppDocument).filter(AppDocument.collection == collection).all()

    is_admin = _is_admin_role(current_user.get("role", ""))
    current_uid = str(current_user.get("user_id"))

    if collection == "users" and not is_admin:
        docs = [doc for doc in docs if doc.doc_id == current_uid]
    elif collection == "predictions" and not is_admin:
        docs = [doc for doc in docs if str((doc.payload or {}).get("user_id", "")) == current_uid]

    if where_field and where_op and where_value is not None:
        if where_op != "==":
            raise HTTPException(status_code=400, detail="Only == operator is supported")
        docs = [
            doc for doc in docs
            if str((doc.payload or {}).get(where_field, "")) == str(where_value)
        ]

    return {
        "documents": [_serialize_document(doc) for doc in docs]
    }


@router.post("/admin/sync-relational")
def sync_relational_tables(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_admin_role(str(current_user.get("role", ""))):
        raise HTTPException(status_code=403, detail="Admin access required")

    users_docs = db.query(AppDocument).filter(AppDocument.collection == "users").all()
    prediction_docs = db.query(AppDocument).filter(AppDocument.collection == "predictions").all()

    users_synced = 0
    users_failed = 0
    prediction_synced = 0
    prediction_failed = 0

    for doc in users_docs:
        try:
            if _sync_user_doc_to_relational(db, doc.doc_id, dict(doc.payload or {})):
                db.commit()
                users_synced += 1
        except Exception:
            db.rollback()
            users_failed += 1

    for doc in prediction_docs:
        try:
            if _sync_prediction_doc_to_relational(db, dict(doc.payload or {})):
                db.commit()
                prediction_synced += 1
        except Exception:
            db.rollback()
            prediction_failed += 1

    return {
        "ok": True,
        "users_docs_total": len(users_docs),
        "users_docs_synced": users_synced,
        "users_docs_failed": users_failed,
        "prediction_docs_total": len(prediction_docs),
        "prediction_docs_synced": prediction_synced,
        "prediction_docs_failed": prediction_failed,
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }


@router.delete("/docs/{collection}/{doc_id}")
def delete_doc(
    collection: str,
    doc_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    collection = _assert_collection(collection)
    _assert_doc_access(current_user, collection, doc_id, write=True)

    if collection == "users" and not _is_admin_role(current_user.get("role", "")):
        raise HTTPException(status_code=403, detail="Forbidden")

    if collection == "predictions" and not _is_admin_role(current_user.get("role", "")):
        doc = _get_document(db, collection, doc_id)
        owner = str((doc.payload or {}).get("user_id", "")) if doc else ""
        if owner != str(current_user.get("user_id")):
            raise HTTPException(status_code=403, detail="Forbidden")

    doc = _get_document(db, collection, doc_id)
    if not doc:
        return {"ok": True}

    db.delete(doc)
    db.commit()
    return {"ok": True}
