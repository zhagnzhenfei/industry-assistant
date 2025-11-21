"""
记忆功能模块

提供统一的记忆管理、装饰器和策略支持
"""
from .custom_memory_service import CustomMemoryService
from .memory_factory import MemoryServiceFactory, get_memory_service
from .decorators import with_memory, research_memory, chat_memory, question_memory
from .manager import MemoryManager
from .strategies import InteractionType

__all__ = [
    # 核心服务
    "CustomMemoryService",
    "MemoryServiceFactory",
    "get_memory_service",

    # 装饰器框架
    "with_memory",           # 通用装饰器
    "research_memory",       # 研究记忆装饰器
    "chat_memory",          # 聊天记忆装饰器
    "question_memory",      # 问答记忆装饰器
    "MemoryManager",         # 记忆管理器
    "InteractionType"        # 交互类型
]
