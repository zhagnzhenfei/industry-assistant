"""
记忆模块配置

通过环境变量控制记忆功能的启用/禁用和具体实现
"""
import os
from typing import Dict, Any


def get_memory_config() -> Dict[str, Any]:
    """获取记忆模块配置
    
    Returns:
        配置字典
    """
    return {
        # 🔌 主开关 - 控制记忆功能是否启用
        "enable_memory": os.getenv("ENABLE_MEMORY", "false").lower() == "true",
        
        # 记忆提供者类型: "noop", "milvus", "full"
        "memory_provider_type": os.getenv("MEMORY_PROVIDER_TYPE", "milvus"),
        
        # Milvus配置
        "milvus_host": os.getenv("MILVUS_HOST", "localhost"),
        "milvus_port": int(os.getenv("MILVUS_PORT", 19530)),
        "milvus_collection": os.getenv("MILVUS_COLLECTION", "research_memory"),
        
        # Embedding模型配置
        "embedding_model": os.getenv(
            "EMBEDDING_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2"
        ),
        
        # Redis配置（仅full模式需要）
        "redis_url": os.getenv(
            "REDIS_URL", 
            "redis://localhost:6379/0"
        ),
        
        # PostgreSQL配置（仅full模式需要）
        "database_url": os.getenv(
            "DATABASE_URL",
            "postgresql://user:pass@localhost/research_db"
        ),
        
        # 记忆策略配置
        "short_term_window": int(os.getenv("SHORT_TERM_WINDOW", 5)),  # 短期记忆保留最近N条
        "short_term_ttl_days": int(os.getenv("SHORT_TERM_TTL_DAYS", 7)),  # 短期记忆过期天数
    }


def is_memory_enabled() -> bool:
    """检查记忆功能是否启用
    
    Returns:
        bool: True表示启用，False表示禁用
    """
    return os.getenv("ENABLE_MEMORY", "false").lower() == "true"

