from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from service.auth_service import AuthService
from schemas.user import (
    UserRegister, UserLogin, UserInfo, UserResponse, 
    PasswordChange, UserUpdate
)

# 创建路由实例
router = APIRouter(tags=["user"])

# HTTP Bearer 认证scheme
security = HTTPBearer()


def get_auth_service() -> AuthService:
    """获取认证服务实例"""
    return AuthService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> UserInfo:
    """获取当前认证用户的依赖注入函数"""
    token = credentials.credentials
    user = auth_service.get_current_user(token)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    用户注册接口
    
    Args:
        user_data: 用户注册信息
        
    Returns:
        注册结果
    """
    try:
        result = auth_service.register_user(user_data)
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        return {"message": "User registered successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败: {str(e)}"
        )


@router.post("/login", status_code=status.HTTP_200_OK)
async def login(
    login_data: UserLogin,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    用户登录接口
    
    Args:
        login_data: 用户登录信息
        
    Returns:
        登录成功后的令牌
    """
    try:
        result = auth_service.login_user(login_data)
        
        return {
            "access_token": result.access_token,
            "token_type": result.token_type
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"  # 统一错误消息，不泄露具体错误原因
        )


@router.get("/me", response_model=UserInfo, status_code=status.HTTP_200_OK)
async def get_current_user_info(
    current_user: UserInfo = Depends(get_current_user)
):
    """
    获取当前用户信息接口
    
    Args:
        current_user: 通过JWT认证的当前用户
        
    Returns:
        当前用户信息
    """
    return current_user


@router.put("/password", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def change_password(
    password_data: PasswordChange,
    current_user: UserInfo = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    修改密码接口
    
    Args:
        password_data: 密码修改信息
        current_user: 通过JWT认证的当前用户
        
    Returns:
        密码修改结果
    """
    try:
        result = auth_service.change_password(current_user.user_id, password_data)
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"修改密码失败: {str(e)}"
        )


@router.put("/profile", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def update_profile(
    update_data: UserUpdate,
    current_user: UserInfo = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    更新用户信息接口
    
    Args:
        update_data: 用户信息更新数据
        current_user: 通过JWT认证的当前用户
        
    Returns:
        用户信息更新结果
    """
    try:
        result = auth_service.update_user_info(current_user.user_id, update_data)
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新用户信息失败: {str(e)}"
        )




@router.get("/verify-token", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def verify_token(current_user: UserInfo = Depends(get_current_user)):
    """
    验证令牌有效性接口
    
    Args:
        current_user: 通过JWT认证的当前用户
        
    Returns:
        令牌验证结果和用户信息
    """
    return {
        "valid": True,
        "message": "令牌有效",
        "user_info": current_user.dict()
    }
