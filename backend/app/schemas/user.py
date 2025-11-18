from typing import Optional
from pydantic import BaseModel, Field, validator
import re


class UserRegister(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=20, description="用户名，3-20个字符")
    password: str = Field(..., min_length=6, max_length=128, description="密码，至少6位")
    
    @validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('用户名只能包含字母、数字、下划线和连字符')
        return v


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class UserInfo(BaseModel):
    """用户信息响应"""
    user_id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    is_active: bool = Field(..., description="是否激活")
    created_at: int = Field(..., description="创建时间戳")
    updated_at: int = Field(..., description="更新时间戳")


class TokenResponse(BaseModel):
    """登录成功响应"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field("bearer", description="令牌类型")


class UserResponse(BaseModel):
    """用户操作响应"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")
    user_info: Optional[UserInfo] = Field(None, description="用户信息")


class PasswordChange(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=128, description="新密码，至少6位")
    confirm_new_password: str = Field(..., description="确认新密码")
    
    @validator('confirm_new_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('两次输入的新密码不一致')
        return v


class UserUpdate(BaseModel):
    """用户信息更新请求"""
    email: Optional[str] = Field(None, description="邮箱地址")
    
    @validator('email')
    def validate_email(cls, v):
        if v is not None:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v):
                raise ValueError('请输入有效的邮箱地址')
        return v
