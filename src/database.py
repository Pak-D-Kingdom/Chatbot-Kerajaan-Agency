import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import declarative_base, sessionmaker

from src.config import DB_PATH, PROJECT_ROOT

# Ensure data directory exists
os.makedirs(os.path.join(PROJECT_ROOT, "data"), exist_ok=True)

engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()



class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String, index=True)
    sender = Column(String, nullable=False) # 'user' or 'bot'
    message = Column(Text, nullable=False)
    intent = Column(String, nullable=True)
    purchase_intent = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserForm(Base):
    __tablename__ = "user_forms"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully.")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
