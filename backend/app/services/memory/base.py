"""
记忆服务基础接口和数据结构
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ConversationMemory:
    """对话记忆数据结构"""
    conversation_id: str
    user_id: str
    question: str
    research_brief: str
    final_report: str
    key_findings: List[str]
    quality_score: float
    duration: float
    created_at: str
    metadata: Dict[str, Any]


@dataclass
class UserProfile:
    """用户画像数据结构"""
    user_id: str
    expertise: List[str]  # 专业领域
    research_interests: List[str]  # 研究兴趣
    preferred_depth: str  # 偏好的研究深度
    preferred_data_sources: List[str]  # 偏好的数据源
    statistics: Dict[str, Any]  # 统计数据（总研究数、平均质量等）
    created_at: str
    updated_at: str


class IMemoryProvider(ABC):
    """记忆服务抽象接口
    
    所有记忆提供者（NoOp、Milvus、Full等）都必须实现此接口
    """
    
    @abstractmethod
    async def load_memory(self, user_id: str) -> Dict[str, Any]:
        """加载用户记忆（短期+长期）
        
        Args:
            user_id: 用户ID
            
        Returns:
            包含short_term_memory和user_profile的字典
        """
        pass
    
    @abstractmethod
    async def save_conversation(
        self, 
        user_id: str, 
        conversation: ConversationMemory
    ) -> None:
        """保存对话到记忆系统
        
        Args:
            user_id: 用户ID
            conversation: 对话记忆对象
        """
        pass
    
    @abstractmethod
    async def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """获取用户画像
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户画像对象，如果不存在则返回None
        """
        pass
    
    @abstractmethod
    async def update_user_profile(
        self, 
        user_id: str, 
        research_data: Dict[str, Any]
    ) -> None:
        """根据研究数据更新用户画像
        
        Args:
            user_id: 用户ID
            research_data: 研究数据（包含主题、质量等）
        """
        pass
    
    @abstractmethod
    async def search_similar_conversations(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """语义搜索相似的历史对话
        
        Args:
            user_id: 用户ID
            query: 查询文本
            limit: 返回数量限制
            
        Returns:
            相似对话列表
        """
        pass
    
    @abstractmethod
    async def get_recent_conversations(
        self,
        user_id: str,
        limit: int = 5
    ) -> List[ConversationMemory]:
        """获取最近的对话记录
        
        Args:
            user_id: 用户ID
            limit: 返回数量限制
            
        Returns:
            最近对话列表
        """
        pass

