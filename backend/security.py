from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from config import WebConfig
from auth import (
    User, get_user_by_username, get_user_by_id,
    UserCreate, create_user, update_user_last_login,
    UserRole
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{WebConfig.API_V1_PREFIX}/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=WebConfig.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, WebConfig.SECRET_KEY, algorithm=WebConfig.ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, WebConfig.SECRET_KEY, algorithms=[WebConfig.ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user_by_id(user_id) if user_id else get_user_by_username(username)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已被禁用"
        )
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="用户未激活")
    return current_user


def require_role(allowed_roles: list):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_active_user), **kwargs):
            if current_user.role not in [r.value for r in allowed_roles]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="权限不足"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator


def authenticate_user(username: str, password: str) -> Optional[User]:
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def login_user(username: str, password: str) -> Optional[Dict]:
    user = authenticate_user(username, password)
    if not user:
        return None
    
    update_user_last_login(user.id)
    
    access_token_expires = timedelta(minutes=WebConfig.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": WebConfig.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user,
    }


def register_user(user_data: UserCreate) -> User:
    if get_user_by_username(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    if get_user_by_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已存在"
        )
    
    hashed_password = get_password_hash(user_data.password)
    return create_user(user_data, hashed_password)


def init_default_admin():
    admin_user = get_user_by_username(WebConfig.ADMIN_DEFAULT_USERNAME)
    if not admin_user:
        user_data = UserCreate(
            username=WebConfig.ADMIN_DEFAULT_USERNAME,
            email=WebConfig.ADMIN_DEFAULT_EMAIL,
            password=WebConfig.ADMIN_DEFAULT_PASSWORD,
            full_name="系统管理员",
            role=UserRole.ADMIN,
        )
        register_user(user_data)
        print(f"Default admin created: {WebConfig.ADMIN_DEFAULT_USERNAME} / {WebConfig.ADMIN_DEFAULT_PASSWORD}")
