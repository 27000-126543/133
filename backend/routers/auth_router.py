from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from auth import (
    User, UserCreate, UserLogin, UserResponse, Token,
    ChangePassword, list_users, toggle_user_active, change_user_password,
    UserRole
)
from security import (
    get_current_active_user, register_user, login_user,
    get_password_hash, require_role
)
from audit_logger import get_audit_logger

router = APIRouter(prefix="/auth", tags=["认证"])
audit_logger = get_audit_logger()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, current_user: User = Depends(require_role([UserRole.ADMIN]))):
    """注册新用户（仅管理员）"""
    user = register_user(user_data)
    
    audit_logger.log(
        action="user_register",
        user_id=current_user.id,
        user_name=current_user.full_name,
        resource_type="user",
        resource_id=user.id,
        details={"username": user.username, "role": user.role, "created_by": current_user.username},
    )
    
    return user


@router.post("/login", response_model=Token)
async def login(user_data: UserLogin):
    """用户登录"""
    result = login_user(user_data.username, user_data.password)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    audit_logger.log(
        action="user_login",
        user_id=result["user"].id,
        user_name=result["user"].full_name,
        resource_type="user",
        resource_id=result["user"].id,
        details={"username": result["user"].username},
    )
    
    return result


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return current_user


@router.post("/change-password")
async def change_password(
    password_data: ChangePassword,
    current_user: User = Depends(get_current_active_user)
):
    """修改当前用户密码"""
    from security import verify_password
    
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误"
        )
    
    new_hashed = get_password_hash(password_data.new_password)
    success = change_user_password(current_user.id, new_hashed)
    
    if success:
        audit_logger.log(
            action="password_change",
            user_id=current_user.id,
            user_name=current_user.full_name,
            resource_type="user",
            resource_id=current_user.id,
        )
        return {"message": "密码修改成功"}
    
    raise HTTPException(status_code=500, detail="密码修改失败")


@router.get("/users", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    role: str = None,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER]))
):
    """获取用户列表（管理员/部门经理）"""
    users = list_users(skip, limit, role)
    return users


@router.patch("/users/{user_id}/toggle-active")
async def toggle_user(
    user_id: int,
    is_active: bool,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """启用/禁用用户（仅管理员）"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能禁用自己")
    
    user = toggle_user_active(user_id, is_active)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    audit_logger.log(
        action="user_toggle_active",
        user_id=current_user.id,
        user_name=current_user.full_name,
        resource_type="user",
        resource_id=user_id,
        details={"target_user": user.username, "is_active": is_active},
    )
    
    return {"message": f"用户已{'启用' if is_active else '禁用'}", "user": UserResponse.model_validate(user)}
