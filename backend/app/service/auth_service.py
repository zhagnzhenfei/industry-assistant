import os
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from schemas.user import UserRegister, UserLogin, UserInfo, TokenResponse, UserResponse, PasswordChange, UserUpdate
from models import User
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


class AuthService:
    """用户认证服务"""
    
    def __init__(self):
        """初始化认证服务"""
        # 日志记录器
        self.logger = logging.getLogger(__name__)
        
        # JWT配置 - 安全要求：必须设置环境变量
        self.secret_key = os.environ.get('JWT_SECRET_KEY')
        self.algorithm = os.environ.get('JWT_ALGORITHM', 'HS256')
        self.access_token_expire_minutes = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', '1440'))

        # 安全验证：关键配置不能为空
        if not self.secret_key:
            raise ValueError("JWT_SECRET_KEY environment variable is required and cannot be empty")
        
        # 密码加密配置
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """生成密码哈希"""
        # bcrypt有72字节长度限制，超长密码需要截断
        if len(password.encode('utf-8')) > 72:
            password = password[:72]
        return self.pwd_context.hash(password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """创建JWT访问令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证JWT令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None
    

    
    def get_user_by_id(self, user_id: str) -> Optional[UserInfo]:
        """根据用户ID获取用户信息"""
        try:
            from utils.database import default_manager
            
            # 使用数据库管理器的会话
            db = default_manager.session_factory()
            try:
                user = db.query(User).filter(User.user_id == user_id).first()
                if user:
                    return user.to_user_info()
                return None
            finally:
                db.close()  # 关闭会话
        except Exception as e:
            print(f"获取用户信息失败: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[UserInfo]:
        """根据用户名获取用户信息"""
        try:
            from utils.database import default_manager
            
            # 使用数据库管理器的会话
            db = default_manager.session_factory()
            try:
                user = db.query(User).filter(User.username == username).first()
                if user:
                    return user.to_user_info()
                return None
            finally:
                db.close()  # 关闭会话
        except Exception as e:
            print(f"根据用户名获取用户失败: {e}")
            return None
    

    
    def register_user(self, user_data: UserRegister) -> UserResponse:
        """用户注册"""
        try:
            from utils.database import default_manager
            
            # 使用数据库管理器的会话
            db = default_manager.session_factory()
            try:
                # 检查用户名是否已存在
                existing_username = db.query(User).filter(User.username == user_data.username).first()
                if existing_username:
                    return UserResponse(
                        success=False,
                        message="用户名已存在"
                    )
                
                # 创建新用户
                new_user = User(
                    username=user_data.username,
                    password_hash=self.get_password_hash(user_data.password),
                    is_active=True
                )
                
                # 保存到数据库
                db.add(new_user)
                db.commit()
                db.refresh(new_user)
                
                # 返回成功响应
                user_info = new_user.to_user_info()
                return UserResponse(
                    success=True,
                    message="注册成功",
                    user_info=user_info
                )
                
            finally:
                db.close()  # 关闭会话
                
        except Exception as e:
            print(f"用户注册失败: {e}")
            return UserResponse(
                success=False,
                message=f"注册失败: {str(e)}"
            )
    
    def login_user(self, login_data: UserLogin) -> TokenResponse:
        """用户登录"""
        try:
            from utils.database import default_manager
            
            # 使用数据库管理器的会话
            db = default_manager.session_factory()
            try:
                # 按用户名查找用户
                user = db.query(User).filter(User.username == login_data.username).first()
                
                if not user:
                    # 记录详细日志：用户不存在
                    self.logger.warning(
                        f"登录失败: 用户不存在 - 用户名: {login_data.username}"
                    )
                    raise Exception("用户名或密码错误")
                
                # 验证密码
                if not self.verify_password(login_data.password, user.password_hash):
                    # 记录详细日志：密码错误（不记录密码内容）
                    self.logger.warning(
                        f"登录失败: 密码错误 - 用户名: {login_data.username}, 用户ID: {user.user_id}"
                    )
                    raise Exception("用户名或密码错误")
                
                if not user.is_active:
                    # 记录详细日志：账户被禁用
                    self.logger.warning(
                        f"登录失败: 账户已禁用 - 用户名: {login_data.username}, 用户ID: {user.user_id}"
                    )
                    raise Exception("账户已被禁用")
                
                # 登录成功
                self.logger.info(
                    f"用户登录成功 - 用户名: {login_data.username}, 用户ID: {user.user_id}"
                )
                
                # 创建访问令牌
                access_token_expires = timedelta(minutes=self.access_token_expire_minutes)
                access_token = self.create_access_token(
                    data={"sub": user.user_id, "username": user.username},
                    expires_delta=access_token_expires
                )
                
                return TokenResponse(
                    access_token=access_token,
                    token_type="bearer"
                )
                
            finally:
                db.close()  # 关闭会话
                
        except Exception as e:
            # 记录完整的错误堆栈（用于排查问题）
            self.logger.error(
                f"用户登录异常 - 用户名: {login_data.username}",
                exc_info=True  # 这会记录完整的 traceback
            )
            raise e
    
    def get_current_user(self, token: str) -> Optional[UserInfo]:
        """根据令牌获取当前用户"""
        payload = self.verify_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        return self.get_user_by_id(user_id)
    
    def change_password(self, user_id: str, password_data: PasswordChange) -> UserResponse:
        """修改密码"""
        try:
            from utils.database import default_manager
            
            # 使用数据库管理器的会话
            db = default_manager.session_factory()
            try:
                # 获取用户
                user = db.query(User).filter(User.user_id == user_id).first()
                if not user:
                    return UserResponse(
                        success=False,
                        message="用户不存在"
                    )
                
                # 验证旧密码
                if not self.verify_password(password_data.old_password, user.password_hash):
                    return UserResponse(
                        success=False,
                        message="旧密码错误"
                    )
                
                # 更新密码
                user.password_hash = self.get_password_hash(password_data.new_password)
                user.updated_at = int(time.time())
                
                db.commit()
                
                return UserResponse(
                    success=True,
                    message="密码修改成功"
                )
                
            finally:
                db.close()  # 关闭会话
                
        except Exception as e:
            print(f"修改密码失败: {e}")
            return UserResponse(
                success=False,
                message=f"修改密码失败: {str(e)}"
            )
    
    def update_user_info(self, user_id: str, update_data: UserUpdate) -> UserResponse:
        """更新用户信息"""
        try:
            from utils.database import default_manager
            
            # 使用数据库管理器的会话
            db = default_manager.session_factory()
            try:
                # 获取用户
                user = db.query(User).filter(User.user_id == user_id).first()
                if not user:
                    return UserResponse(
                        success=False,
                        message="用户不存在"
                    )
                
                # 更新时间戳
                user.updated_at = int(time.time())
                
                db.commit()
                db.refresh(user)
                
                # 构建更新后的用户信息
                updated_user_info = user.to_user_info()
                
                return UserResponse(
                    success=True,
                    message="用户信息更新成功",
                    user_info=updated_user_info
                )
                
            finally:
                db.close()  # 关闭会话
                
        except Exception as e:
            print(f"更新用户信息失败: {e}")
            return UserResponse(
                success=False,
                message=f"更新用户信息失败: {str(e)}"
            )


# 创建全局认证服务实例
auth_service = AuthService()

# 创建HTTP Bearer认证方案
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """
    从JWT令牌中获取当前用户
    
    Args:
        credentials: HTTP Bearer认证凭据
        
    Returns:
        当前用户对象
        
    Raises:
        HTTPException: 当认证失败时
    """
    try:
        # 验证令牌
        payload = auth_service.verify_token(credentials.credentials)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 获取用户ID
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌中缺少用户ID",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 从数据库获取用户信息
        from utils.database import default_manager
        db = default_manager.session_factory()
        try:
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="用户不存在",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="用户账户已被禁用",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return user
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败",
            headers={"WWW-Authenticate": "Bearer"},
        )
