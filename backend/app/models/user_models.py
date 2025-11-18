import time
from sqlalchemy import Column, String, Boolean, BigInteger, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import func
import uuid

from utils.database import Base


class User(Base):
    """用户数据模型"""
    
    __tablename__ = "users"
    
    # 主键
    user_id = Column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        comment="用户唯一标识"
    )
    
    # 用户基本信息
    username = Column(
        String(20), 
        unique=True, 
        nullable=False, 
        index=True,
        comment="用户名，3-20个字符"
    )
    
    password_hash = Column(
        String(255), 
        nullable=False,
        comment="密码哈希值"
    )
    
    # 用户状态
    is_active = Column(
        Boolean, 
        default=True, 
        nullable=False,
        comment="是否激活"
    )
    
    # 时间戳
    created_at = Column(
        BigInteger, 
        default=lambda: int(time.time()), 
        nullable=False,
        comment="创建时间戳"
    )
    
    updated_at = Column(
        BigInteger, 
        default=lambda: int(time.time()), 
        onupdate=lambda: int(time.time()), 
        nullable=False,
        comment="更新时间戳"
    )
    
    # 额外信息字段（JSON格式存储扩展信息）
    extra_info = Column(
        Text,
        nullable=True,
        comment="额外信息，JSON格式"
    )
    
    # 创建索引
    __table_args__ = (
        Index('idx_user_active_created', 'is_active', 'created_at'),
        {'comment': '用户信息表'}
    )
    
    def __repr__(self):
        return f"<User(user_id='{self.user_id}', username='{self.username}')>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def to_user_info(self):
        """转换为UserInfo模型格式"""
        from schemas.user import UserInfo
        return UserInfo(
            user_id=self.user_id,
            username=self.username,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at
        )
