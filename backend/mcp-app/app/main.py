"""
重构后的MCP服务主应用
基于标准MCP协议的轻量级实现
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from app.core.config import settings
from app.core.state import app_state
from app.services.mcp_client import MCPClient
from app.services.config_manager import ConfigManager
from app.api.connections import router as connections_router

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 全局服务实例
mcp_client: Optional[MCPClient] = None
config_manager: Optional[ConfigManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    await startup_event()
    yield
    # 关闭时清理
    await shutdown_event()


# 创建FastAPI应用
app = FastAPI(
    title="Standard MCP Gateway",
    version="2.0.0",
    description="基于标准MCP协议的轻量级网关服务",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def startup_event():
    """应用启动时初始化服务"""
    try:
        logger.info("Starting Standard MCP Gateway...")

        # 初始化配置管理器
        logger.info("Initializing config manager...")
        global config_manager
        config_manager = ConfigManager()

        # 初始化MCP客户端
        logger.info("Initializing MCP client...")
        global mcp_client
        mcp_client = MCPClient()
        logger.info(f"✅ MCP客户端初始化完成: {type(mcp_client)}")

        # 使用标准状态管理初始化应用状态
        logger.info("🔧 初始化应用状态...")
        app_state.initialize(mcp_client, config_manager)
        logger.info("✅ 应用状态初始化完成")

        # 加载并连接活跃服务器
        logger.info("Loading and connecting to active servers...")
        active_servers = config_manager.get_active_servers()
        connected_count = 0

        for server_config in active_servers:
            try:
                # 添加到MCP客户端
                await mcp_client.add_server(server_config)
                logger.info(f"Added server: {server_config.id}")

                # 尝试连接 (非阻塞，连接失败不影响服务启动)
                try:
                    success = await mcp_client.connect_server(server_config.id)
                    if success:
                        connected_count += 1
                        logger.info(f"Connected to server: {server_config.id}")
                    else:
                        logger.warning(f"Failed to connect to server: {server_config.id}")
                except Exception as connect_error:
                    logger.warning(f"Connection failed for server {server_config.id}: {connect_error}")
                    # 连接失败不影响服务启动

            except Exception as e:
                logger.error(f"Error adding server {server_config.id}: {e}")
                # 添加服务器失败不影响服务启动

        logger.info(f"Standard MCP Gateway started successfully")
        logger.info(f"Active servers: {len(active_servers)}, Connected: {connected_count}")

    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        raise


async def shutdown_event():
    """应用关闭时清理服务"""
    logger.info("Shutting down Standard MCP Gateway...")

    if mcp_client:
        await mcp_client.close()

    logger.info("Standard MCP Gateway shutdown complete")


# 根端点
@app.get("/")
async def root():
    """根端点"""
    return {
        "message": "Standard MCP Gateway",
        "version": "2.0.0",
        "description": "基于标准MCP协议的轻量级网关服务",
        "docs": "/docs",
        "health": "/health",
        "features": [
            "标准MCP协议支持",
            "多连接类型 (SSE/STDIO/WebSocket)",
            "动态工具发现",
            "轻量级架构",
            "RESTful API接口"
        ]
    }


# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查"""
    if not mcp_client:
        return {
            "status": "unhealthy",
            "service": "Standard MCP Gateway",
            "error": "MCP client not initialized"
        }

    try:
        health_status = await mcp_client.health_check()
        health_status.update({
            "service": "Standard MCP Gateway",
            "version": "2.0.0"
        })
        return health_status

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "Standard MCP Gateway",
            "error": str(e)
        }


# 服务信息端点
@app.get("/info")
async def service_info():
    """服务信息"""
    if not mcp_client or not config_manager:
        return {"error": "Service not fully initialized"}

    stats = mcp_client.get_stats()

    return {
        "service": "Standard MCP Gateway",
        "version": "2.0.0",
        "protocol_version": "2024-11-05",
        "statistics": stats,
        "api_endpoints": {
            "connections": "/api/v1/connections",
            "tools": "/api/v1/connections/tools/all",
            "health": "/health",
            "docs": "/docs"
        }
    }


# 注册路由
app.include_router(
    connections_router,
    prefix="/api/v1/connections",
    tags=["connections"]
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main_new:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )