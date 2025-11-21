"""
应用状态管理
提供标准的依赖注入方式
"""
import logging
from typing import Optional

from app.services.mcp_client import MCPClient
from app.services.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class AppState:
    """应用状态管理类"""

    def __init__(self):
        self.mcp_client: Optional[MCPClient] = None
        self.config_manager: Optional[ConfigManager] = None
        self._initialized = False

    def initialize(self, mcp_client: MCPClient, config_manager: ConfigManager):
        """初始化应用状态"""
        self.mcp_client = mcp_client
        self.config_manager = config_manager
        self._initialized = True
        logger.info("✅ 应用状态初始化完成")

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized

    def get_mcp_client(self) -> MCPClient:
        """获取MCP客户端实例"""
        if not self.mcp_client:
            raise RuntimeError("MCP客户端未初始化")
        return self.mcp_client

    def get_config_manager(self) -> ConfigManager:
        """获取配置管理器实例"""
        if not self.config_manager:
            raise RuntimeError("配置管理器未初始化")
        return self.config_manager

# 全局应用状态实例
app_state = AppState()