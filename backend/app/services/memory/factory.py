"""
记忆提供者工厂 - 根据配置创建合适的实现

支持：
- NoOp实现（禁用时）
- Milvus实现（MVP版本）
- Full实现（Redis + PostgreSQL + Milvus）
"""
import logging
from typing import Optional

from .base import IMemoryProvider
from .noop_provider import NoOpMemoryProvider

logger = logging.getLogger(__name__)


class MemoryProviderFactory:
    """记忆提供者工厂
    
    职责：
    1. 根据配置决定使用哪种实现
    2. 处理初始化失败（降级到NoOp）
    3. 单例模式管理实例
    """
    
    _instance: Optional[IMemoryProvider] = None
    
    @classmethod
    async def create(cls, config: dict) -> IMemoryProvider:
        """根据配置创建记忆提供者
        
        Args:
            config: 配置字典，包含enable_memory等参数
            
        Returns:
            IMemoryProvider实例
        """
        
        # 检查是否启用记忆功能
        if not config.get("enable_memory", False):
            logger.info("📝 记忆功能已禁用（ENABLE_MEMORY=false），使用NoOp实现")
            return NoOpMemoryProvider()
        
        logger.info("🧠 记忆功能已启用，初始化记忆提供者...")
        
        # 尝试初始化实际的记忆提供者
        provider_type = config.get("memory_provider_type", "milvus")
        
        try:
            if provider_type == "milvus":
                # Milvus MVP实现
                logger.info("📊 使用Milvus记忆提供者（MVP版本）")
                from .milvus_provider import MilvusMemoryProvider
                
                provider = MilvusMemoryProvider(
                    milvus_host=config.get("milvus_host", "localhost"),
                    milvus_port=config.get("milvus_port", 19530),
                    collection_name=config.get("milvus_collection", "research_memory"),
                    embedding_model_name=config.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2")
                )
                
                # 初始化（连接Milvus等）
                await provider.initialize()
                
                logger.info("🎉 Milvus记忆提供者初始化成功")
                return provider
                
            elif provider_type == "full":
                # 完整实现（Redis + PostgreSQL + Milvus）
                logger.info("🏗️ 使用完整记忆提供者（Redis + PostgreSQL + Milvus）")
                from .full_provider import FullMemoryProvider
                
                provider = FullMemoryProvider(
                    redis_url=config.get("redis_url"),
                    database_url=config.get("database_url"),
                    milvus_host=config.get("milvus_host"),
                    milvus_port=config.get("milvus_port"),
                    embedding_model_name=config.get("embedding_model")
                )
                
                await provider.initialize()
                
                logger.info("🎉 完整记忆提供者初始化成功")
                return provider
                
            else:
                logger.warning(f"⚠️ 未知的记忆提供者类型: {provider_type}，降级为NoOp")
                return NoOpMemoryProvider()
                
        except ImportError as e:
            logger.error(f"❌ 记忆提供者导入失败: {e}")
            logger.warning("⚠️ 降级使用NoOp实现")
            return NoOpMemoryProvider()
            
        except Exception as e:
            logger.error(f"❌ 记忆提供者初始化失败: {e}")
            logger.warning("⚠️ 降级使用NoOp实现")
            import traceback
            logger.debug(traceback.format_exc())
            return NoOpMemoryProvider()
    
    @classmethod
    async def get_instance(cls, config: dict = None) -> IMemoryProvider:
        """获取单例实例
        
        Args:
            config: 配置字典（首次调用时必需）
            
        Returns:
            IMemoryProvider实例
        """
        if cls._instance is None and config:
            cls._instance = await cls.create(config)
        
        if cls._instance is None:
            # 如果还是None，返回NoOp
            logger.warning("⚠️ 未初始化记忆提供者，返回NoOp实现")
            cls._instance = NoOpMemoryProvider()
        
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """重置实例（主要用于测试）"""
        cls._instance = None

