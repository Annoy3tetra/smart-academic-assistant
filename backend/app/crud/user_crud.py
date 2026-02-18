from sqlalchemy.orm import Session
from app.models.user import User
from sqlalchemy.exc import IntegrityError
from app.core.security import hash_password

def create_user(db: Session, email: str, password_hash: str, role: str):

    new_user = User(
    name=User.name,
    email=User.email,
    password_hash=hash_password,
    role=User.role
)


    db.add(new_user)

    try:
        db.commit()
        db.refresh(new_user)
        return new_user
    except IntegrityError:
        db.rollback()
        return None
