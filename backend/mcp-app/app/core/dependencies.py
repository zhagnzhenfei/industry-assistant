"""
FastAPI依赖提供者
实现标准的依赖注入模式
"""
import logging
from fastapi import Depends, Request, HTTPException
from typing import Annotated

from app.core.state import app_state
from app.services.mcp_client import MCPClient
from app.services.config_manager import ConfigManager

logger = logging.getLogger(__name__)

async def get_mcp_client() -> MCPClient:
    """获取MCP客户端依赖"""
    try:
        if not app_state.is_initialized():
            logger.error("❌ 应用状态未初始化")
            raise HTTPException(status_code=503, detail="服务未完全启动，请稍后再试")

        client = app_state.get_mcp_client()
        logger.debug("✅ MCP客户端依赖注入成功")
        return client

    except Exception as e:
        logger.error(f"❌ MCP客户端依赖注入失败: {e}")
        raise HTTPException(status_code=500, detail="获取MCP客户端失败")

async def get_config_manager() -> ConfigManager:
    """获取配置管理器依赖"""
    try:
        if not app_state.is_initialized():
            logger.error("❌ 应用状态未初始化")
            raise HTTPException(status_code=503, detail="服务未完全启动，请稍后再试")

        manager = app_state.get_config_manager()
        logger.debug("✅ 配置管理器依赖注入成功")
        return manager

    except Exception as e:
        logger.error(f"❌ 配置管理器依赖注入失败: {e}")
        raise HTTPException(status_code=500, detail="获取配置管理器失败")

# 类型别名，提高可读性
MCPClientDep = Annotated[MCPClient, Depends(get_mcp_client)]
ConfigManagerDep = Annotated[ConfigManager, Depends(get_config_manager)]