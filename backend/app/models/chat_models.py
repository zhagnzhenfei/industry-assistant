import time
import uuid
from sqlalchemy import Column, String, Boolean, BigInteger, Text, Index, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from utils.database import Base


class ChatSession(Base):
    """聊天会话数据模型"""
    
    __tablename__ = "chat_sessions"
    
    # 主键
    session_id = Column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        comment="会话唯一标识"
    )
    
    # 外键
    user_id = Column(
        String(36), 
        ForeignKey('users.user_id'),
        nullable=False,
        comment="用户ID"
    )
    
    assistant_id = Column(
        String(36), 
        ForeignKey('assistants.assistant_id'),
        nullable=False,
        comment="智能体ID"
    )
    
    # 基本信息
    title = Column(
        String(200), 
        nullable=False,
        comment="会话标题"
    )
    
    status = Column(
        String(20),
        default='active',
        nullable=False,
        comment="会话状态：active, archived, deleted"
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
    
    # 关系
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    assistant = relationship("Assistant", back_populates="chat_sessions")
    
    # 创建索引
    __table_args__ = (
        Index('idx_chat_sessions_user', 'user_id'),
        Index('idx_chat_sessions_assistant', 'assistant_id'),
        Index('idx_chat_sessions_status', 'status'),
        Index('idx_chat_sessions_created', 'created_at'),
        {'comment': '聊天会话表'}
    )
    
    def __repr__(self):
        return f"<ChatSession(session_id='{self.session_id}', title='{self.title}', user_id='{self.user_id}')>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'assistant_id': self.assistant_id,
            'title': self.title,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class ChatMessage(Base):
    """聊天消息数据模型"""
    
    __tablename__ = "chat_messages"
    
    # 主键
    message_id = Column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        comment="消息唯一标识"
    )
    
    # 外键
    session_id = Column(
        String(36), 
        ForeignKey('chat_sessions.session_id'),
        nullable=False,
        comment="会话ID"
    )
    
    # 消息内容
    role = Column(
        String(20),
        nullable=False,
        comment="消息角色：user, assistant, system"
    )
    
    content = Column(
        Text,
        nullable=False,
        comment="消息内容"
    )
    
    message_metadata = Column(
        JSONB,
        nullable=True,
        comment="额外信息，JSON格式"
    )
    
    # 时间戳
    created_at = Column(
        BigInteger, 
        default=lambda: int(time.time()), 
        nullable=False,
        comment="创建时间戳"
    )
    
    # 关系
    session = relationship("ChatSession", back_populates="messages")
    
    # 创建索引
    __table_args__ = (
        Index('idx_chat_messages_session', 'session_id'),
        Index('idx_chat_messages_role', 'role'),
        Index('idx_chat_messages_created', 'created_at'),
        {'comment': '聊天消息表'}
    )
    
    def __repr__(self):
        return f"<ChatMessage(message_id='{self.message_id}', role='{self.role}', session_id='{self.session_id}')>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'message_id': self.message_id,
            'session_id': self.session_id,
            'role': self.role,
            'content': self.content,
            'metadata': self.message_metadata,
            'created_at': self.created_at
        }
