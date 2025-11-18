"""
记忆服务工厂和依赖注入
"""
import logging
from typing import Optional, Union
from configs.memory_config import MemoryConfig
from .custom_memory_service import CustomMemoryService

logger = logging.getLogger(__name__)


class MemoryServiceFactory:
    """记忆服务工厂（单例模式）"""
    
    _instance: Optional[CustomMemoryService] = None
    _initialized: bool = False
    
    @classmethod
    def get_memory_service(cls) -> Optional[CustomMemoryService]:
        """
        获取记忆服务单例（使用自定义实现）
        
        Returns:
            CustomMemoryService实例，如果未启用则返回None
        """
        # 如果已经初始化过，直接返回
        if cls._initialized:
            return cls._instance
        
        try:
            # 获取配置
            config = MemoryConfig.get_memory_config()

            # 检查是否启用
            if not config.get("enabled", False):
                logger.info("记忆功能未启用")
                cls._initialized = True
                cls._instance = None
                return None

            # 验证配置
            if not MemoryConfig.validate_config(config):
                logger.error("配置验证失败，记忆功能将不可用")
                cls._initialized = True
                cls._instance = None
                return None
            
            # 创建自定义服务实例
            logger.info("正在初始化自定义记忆服务...")
            cls._instance = CustomMemoryService(config)
            cls._initialized = True
            
            logger.info("自定义记忆服务初始化成功")
            return cls._instance
            
        except Exception as e:
            logger.error(f"初始化自定义记忆服务失败: {e}")
            import traceback
            logger.error(f"错误详情:\n{traceback.format_exc()}")
            cls._initialized = True
            cls._instance = None
            return None
    
    @classmethod
    def reset(cls):
        """重置工厂（主要用于测试）"""
        cls._instance = None
        cls._initialized = False


def get_memory_service() -> Optional[CustomMemoryService]:
    """
    FastAPI依赖注入函数
    
    Returns:
        CustomMemoryService实例或None
    """
    return MemoryServiceFactory.get_memory_service()

