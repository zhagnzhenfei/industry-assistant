import time
import uuid
from sqlalchemy import Column, String, Boolean, BigInteger, Text, Index, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from utils.database import Base


class Assistant(Base):
    """智能体数据模型"""
    
    __tablename__ = "assistants"
    
    # 主键
    assistant_id = Column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        comment="智能体唯一标识"
    )
    
    # 用户外键
    user_id = Column(
        String(36), 
        ForeignKey('users.user_id'),
        nullable=False,
        comment="创建者用户ID"
    )
    
    # 基本信息
    name = Column(
        String(100), 
        nullable=False,
        comment="智能体名称"
    )
    
    original_prompt = Column(
        Text,
        nullable=False,
        comment="用户原始提示词"
    )
    
    prompt = Column(
        Text,
        nullable=False,
        comment="增强版提示词/系统消息（包含MCP工具信息）"
    )
    
    description = Column(
        Text,
        nullable=True,
        comment="智能体描述"
    )
    
    # 状态
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否启用"
    )
    
    # 知识库配置
    enable_knowledge_base = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否启用知识库"
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
    knowledge_base = relationship("AssistantKnowledgeBase", back_populates="assistant", cascade="all, delete-orphan")
    mcp_services = relationship("AssistantMCPService", back_populates="assistant", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="assistant", cascade="all, delete-orphan")
    
    # 创建索引
    __table_args__ = (
        Index('idx_assistant_user_created', 'user_id', 'created_at'),
        Index('idx_assistant_active', 'is_active'),
        {'comment': '智能体信息表'}
    )
    
    def __repr__(self):
        return f"<Assistant(assistant_id='{self.assistant_id}', name='{self.name}', user_id='{self.user_id}')>"
    
    def to_dict(self):
        """转换为字典格式（返回用户原始提示词）"""
        return {
            'assistant_id': self.assistant_id,
            'user_id': self.user_id,
            'name': self.name,
            'prompt': self.original_prompt,  # 返回用户原始提示词
            'description': self.description,
            'is_active': self.is_active,
            'enable_knowledge_base': self.enable_knowledge_base,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def get_enhanced_prompt(self):
        """获取增强版提示词（用于大模型调用）"""
        # 基础提示词
        base_prompt = self.prompt
        
        # 如果有MCP服务配置，需要动态构建增强提示词
        # 这里返回基础提示词，具体的MCP工具信息会在service层动态添加
        return base_prompt


class AssistantKnowledgeBase(Base):
    """智能体-知识库关联模型"""
    
    __tablename__ = "assistant_knowledge_base"
    
    # 主键
    id = Column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        comment="关联记录唯一标识"
    )
    
    # 外键
    assistant_id = Column(
        String(36), 
        ForeignKey('assistants.assistant_id'),
        nullable=False,
        comment="智能体ID"
    )
    
    document_id = Column(
        String(36), 
        ForeignKey('documents.document_id'),
        nullable=False,
        comment="文档ID"
    )
    
    # 时间戳
    created_at = Column(
        BigInteger, 
        default=lambda: int(time.time()), 
        nullable=False,
        comment="创建时间戳"
    )
    
    # 关系
    assistant = relationship("Assistant", back_populates="knowledge_base")
    
    # 创建索引
    __table_args__ = (
        Index('idx_assistant_kb_assistant', 'assistant_id'),
        Index('idx_assistant_kb_document', 'document_id'),
        {'comment': '智能体-知识库关联表'}
    )
    
    def __repr__(self):
        return f"<AssistantKnowledgeBase(id='{self.id}', assistant_id='{self.assistant_id}', document_id='{self.document_id}')>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'assistant_id': self.assistant_id,
            'document_id': self.document_id,
            'created_at': self.created_at
        }


class AssistantMCPService(Base):
    """智能体-MCP服务关联模型"""
    
    __tablename__ = "assistant_mcp_services"
    
    # 主键
    id = Column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        comment="关联记录唯一标识"
    )
    
    # 外键
    assistant_id = Column(
        String(36), 
        ForeignKey('assistants.assistant_id'),
        nullable=False,
        comment="智能体ID"
    )
    
    # MCP服务信息
    mcp_server_id = Column(
        String(100),
        nullable=False,
        comment="MCP服务ID"
    )
    
    # 时间戳
    created_at = Column(
        BigInteger, 
        default=lambda: int(time.time()), 
        nullable=False,
        comment="创建时间戳"
    )
    
    # 关系
    assistant = relationship("Assistant", back_populates="mcp_services")
    
    # 创建索引
    __table_args__ = (
        Index('idx_assistant_mcp_assistant', 'assistant_id'),
        Index('idx_assistant_mcp_server', 'mcp_server_id'),
        {'comment': '智能体-MCP服务关联表'}
    )
    
    def __repr__(self):
        return f"<AssistantMCPService(id='{self.id}', assistant_id='{self.assistant_id}', mcp_server_id='{self.mcp_server_id}')>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'assistant_id': self.assistant_id,
            'mcp_server_id': self.mcp_server_id,
            'created_at': self.created_at
        }
