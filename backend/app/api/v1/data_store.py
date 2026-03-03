from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import AppDocument, User

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

    if collection == "users" and str(doc_id).isdigit():
        _sync_user_table_from_user_doc(db, current_user, doc_id, doc.payload)
        doc = _get_document(db, collection, doc_id)

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
