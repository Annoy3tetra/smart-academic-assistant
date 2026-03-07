from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base,sessionmaker
from app.core.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_timeout=30,
)

sessionLocal = sessionmaker(bind=engine,autoflush=False,autocommit=False)

Base = declarative_base()

def get_db():
    db = sessionLocal()
    try :
        yield db
    finally:
        db.close()
        
