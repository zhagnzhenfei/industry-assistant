"""
NoOp记忆提供者 - 记忆功能禁用时使用

所有方法都是空操作，返回空结果，确保零性能开销
"""
import logging
from typing import Dict, List, Optional, Any

from .base import IMemoryProvider, ConversationMemory, UserProfile

logger = logging.getLogger(__name__)


class NoOpMemoryProvider(IMemoryProvider):
    """空实现 - 记忆功能禁用时使用
    
    特点：
    - 所有操作立即返回
    - 不执行任何I/O
    - 零性能开销
    - 对外部系统零依赖
    """
    
    def __init__(self):
        logger.info("📝 记忆功能已禁用，使用NoOp实现")
    
    async def load_memory(self, user_id: str) -> Dict[str, Any]:
        """返回空记忆"""
        return {
            "short_term_memory": [],
            "user_profile": None
        }
    
    async def save_conversation(
        self, 
        user_id: str, 
        conversation: ConversationMemory
    ) -> None:
        """不执行任何操作"""
        pass
    
    async def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """返回空画像"""
        return None
    
    async def update_user_profile(
        self, 
        user_id: str, 
        research_data: Dict[str, Any]
    ) -> None:
        """不执行任何操作"""
        pass
    
    async def search_similar_conversations(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """返回空列表"""
        return []
    
    async def get_recent_conversations(
        self,
        user_id: str,
        limit: int = 5
    ) -> List[ConversationMemory]:
        """返回空列表"""
        return []

