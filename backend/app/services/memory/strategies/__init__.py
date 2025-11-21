"""
记忆策略模块

提供不同类型的交互策略实现
"""
from enum import Enum
from .base import InteractionStrategy
from .research import ResearchInteractionStrategy
from .chat import ChatInteractionStrategy
from .question import QuestionInteractionStrategy

class InteractionType(Enum):
    """交互类型枚举"""
    RESEARCH = "research"
    CHAT = "chat"
    QUESTION = "question"
    DOCUMENT = "document"
    SEARCH = "search"
    ASSISTANT = "assistant"

__all__ = [
    'InteractionType',
    'InteractionStrategy',
    'ResearchInteractionStrategy',
    'ChatInteractionStrategy',
    'QuestionInteractionStrategy'
]