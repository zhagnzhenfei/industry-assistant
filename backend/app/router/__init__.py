# 导入所有路由模块
from .document_router import router as document_router
from .search_router import router as search_router
from .research_router import router as research_router
from .user_router import router as user_router
from .assistant_router import router as assistant_router
from .assistant_chat_router import router as assistant_chat_router
from .mcp_router import router as mcp_router
from .agent_router import router as agent_router
from .memory_router import router as memory_router

# 导出路由实例
__all__ = [
    "document_router",
    "search_router",
    "research_router",
    "user_router",
    "assistant_router",
    "assistant_chat_router",
    "mcp_router",
    "agent_router",
    "memory_router"
] 