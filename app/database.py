from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base,sessionmaker

DATABASE_URL = 'sqlite:///./user.db'

engine = create_engine(DATABASE_URL,connect_args={"check_same_thread":False})

sessionLocal = sessionmaker(bind=engine,autoflush=False,autocommit=False)

Base = declarative_base()

def get_db():
    db = sessionLocal()
    try :
        yield db
    finally:
        db.close()
        
