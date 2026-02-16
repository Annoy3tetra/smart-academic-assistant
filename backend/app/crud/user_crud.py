from sqlalchemy.orm import Session
from app.models.user import User
from sqlalchemy.exc import IntegrityError
from app.core.security import hash_password

def create_user(db: Session, email: str, password_hash: str, role: str):

    user = User(
        email=email,
        password_hash=hash_password(user.password_hash),
        role=role
    )

    db.add(user)

    try:
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError:
        db.rollback()
        return None
