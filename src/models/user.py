from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from src.db.base import Base

class User(Base):
    """User model."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String)  # admin, manager, user
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __init__(self, username: str, password_hash: str, role: str = "user"):
        self.username = username
        self.password_hash = password_hash
        self.role = role
        self.last_login = None
        self.created_at = datetime.utcnow()

    def __repr__(self):
        return f"<User {self.username}>"