from datetime import datetime, timedelta
from typing import Optional, List
from enum import Enum as PyEnum

from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from database import Base, get_db_session


class UserRole(str, PyEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), default=UserRole.EMPLOYEE.value)
    employee_id = Column(Integer, ForeignKey("employees.id"), unique=True)
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    employee = relationship("Employee", foreign_keys=[employee_id])
    
    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN.value
    
    @property
    def is_manager(self) -> bool:
        return self.role in [UserRole.ADMIN.value, UserRole.MANAGER.value]


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2, max_length=100)
    role: UserRole = UserRole.EMPLOYEE
    employee_id: Optional[int] = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    employee_id: Optional[int]
    is_active: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None


class ChangePassword(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)


def get_user_by_username(username: str) -> Optional[User]:
    with get_db_session() as session:
        return session.query(User).filter(User.username == username).first()


def get_user_by_email(email: str) -> Optional[User]:
    with get_db_session() as session:
        return session.query(User).filter(User.email == email).first()


def get_user_by_id(user_id: int) -> Optional[User]:
    with get_db_session() as session:
        return session.query(User).filter(User.id == user_id).first()


def create_user(user_data: UserCreate, hashed_password: str) -> User:
    with get_db_session() as session:
        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            role=user_data.role.value,
            employee_id=user_data.employee_id,
            is_active=True,
        )
        session.add(user)
        session.flush()
        user_id = user.id
    
    return get_user_by_id(user_id)


def update_user_last_login(user_id: int):
    with get_db_session() as session:
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            user.last_login_at = datetime.now()


def list_users(skip: int = 0, limit: int = 100, role: Optional[str] = None) -> List[User]:
    with get_db_session() as session:
        query = session.query(User)
        if role:
            query = query.filter(User.role == role)
        return query.offset(skip).limit(limit).all()


def change_user_password(user_id: int, new_hashed_password: str) -> bool:
    with get_db_session() as session:
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            user.hashed_password = new_hashed_password
            return True
        return False


def toggle_user_active(user_id: int, is_active: bool) -> Optional[User]:
    with get_db_session() as session:
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            user.is_active = is_active
            return user
        return None
