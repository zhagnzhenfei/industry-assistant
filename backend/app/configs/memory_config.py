"""
自定义记忆功能配置管理
"""
import os
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class MemoryConfig:
    """自定义记忆功能配置管理类"""

    @staticmethod
    def get_memory_config() -> Dict[str, Any]:
        """
        获取记忆功能配置

        Returns:
            配置字典
        """
        config = {
            "enabled": os.getenv("ENABLE_MEMORY", "false").lower() == "true",

            # PostgreSQL配置
            "postgres_host": os.getenv("DB_HOST", "localhost"),
            "postgres_port": int(os.getenv("DB_PORT", "5432")),
            "postgres_db": os.getenv("DB_NAME", "app_db"),
            "postgres_user": os.getenv("DB_USER", "postgres"),
            "postgres_password": os.getenv("DB_PASSWORD", ""),

            # Milvus配置
            "milvus_host": os.getenv("MILVUS_HOST", "localhost"),
            "milvus_port": os.getenv("MILVUS_PORT", "19530"),
            "milvus_collection": os.getenv("MILVUS_COLLECTION", "user_memories"),

            # DashScope API配置
            "llm_api_key": os.getenv("DASHSCOPE_API_KEY", ""),
            "llm_base_url": os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            "embedding_model": os.getenv("EMBEDDING_MODEL", "text-embedding-v4"),
        }

        logger.debug(f"记忆功能配置加载: enabled={config['enabled']}")

        return config

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """
        验证配置是否完整

        Args:
            config: 配置字典

        Returns:
            是否有效
        """
        if not config["enabled"]:
            return True

        required_fields = [
            "postgres_host", "postgres_port", "postgres_db",
            "postgres_user", "postgres_password",
            "milvus_host", "milvus_port",
            "llm_api_key", "llm_base_url"
        ]

        missing_fields = []
        for field in required_fields:
            if not config.get(field):
                missing_fields.append(field)

        if missing_fields:
            logger.error(f"记忆功能配置缺失字段: {', '.join(missing_fields)}")
            return False

        return True