import time
from sqlalchemy import Column, String, Boolean, BigInteger, Text, Index, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from utils.database import Base


class Document(Base):
    """用户文档数据模型"""
    
    __tablename__ = "documents"
    
    # 主键
    document_id = Column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        comment="文档唯一标识"
    )
    
    # 用户外键
    user_id = Column(
        String(36), 
        ForeignKey('users.user_id'),
        nullable=False,
        comment="用户ID"
    )
    
    # 文档基本信息
    file_name = Column(
        String(255), 
        nullable=False,
        comment="原始文件名"
    )
    
    file_path = Column(
        String(500), 
        nullable=False,
        comment="文件存储路径"
    )
    
    file_size = Column(
        BigInteger,
        nullable=True,
        comment="文件大小（字节）"
    )
    
    file_type = Column(
        String(50),
        nullable=True,
        comment="文件类型"
    )
    
    # 文件哈希，用于防止重复上传
    file_hash = Column(
        String(64),
        nullable=True,
        comment="文件名的SHA256哈希值"
    )
    
    # 处理状态
    status = Column(
        String(20),
        default='uploading',
        nullable=False,
        comment="处理状态：uploading, processing, completed, failed"
    )
    
    # 处理结果
    chunk_count = Column(
        BigInteger,
        default=0,
        nullable=False,
        comment="文档分块数量"
    )
    
    error_message = Column(
        Text,
        nullable=True,
        comment="错误信息"
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
    
    # 创建索引
    __table_args__ = (
        Index('idx_document_user_created', 'user_id', 'created_at'),
        Index('idx_document_status', 'status'),
        {'comment': '用户文档信息表'}
    )
    
    def __repr__(self):
        return f"<Document(document_id='{self.document_id}', file_name='{self.file_name}', user_id='{self.user_id}')>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'document_id': self.document_id,
            'user_id': self.user_id,
            'file_name': self.file_name,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'file_hash': self.file_hash,
            'status': self.status,
            'chunk_count': self.chunk_count,
            'error_message': self.error_message,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
