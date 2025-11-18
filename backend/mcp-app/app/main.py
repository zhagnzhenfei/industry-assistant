"""
通用MCP服务主应用
专注于工具管理功能
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from app.core.config import settings
from app.services.tool_manager import ToolManager
from app.services.execution_service import ToolExecutionService
from app.services.server_manager import ServerManager
from app.api import execution, servers, tools

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 全局服务实例
tool_manager: Optional[ToolManager] = None
execution_service: Optional[ToolExecutionService] = None
server_manager: Optional[ServerManager] = None

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
    title="Generic MCP Service",
    version="1.0.0",
    description="通用MCP工具管理服务",
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
    global tool_manager, execution_service, server_manager
    
    try:
        logger.info("Starting Generic MCP Service...")
        
        # 初始化服务器管理器
        logger.info("Initializing server manager...")
        server_manager = ServerManager()
        
        # 初始化PostgreSQL服务器（如果配置了）
        logger.info("Initializing PostgreSQL server...")
        try:
            await server_manager.initialize_postgres_server()
        except Exception as e:
            logger.warning(f"PostgreSQL server initialization failed: {e}")
        
        # 初始化工具管理器
        logger.info("Initializing tool manager...")
        tool_manager = ToolManager()
        
        # 设置工具管理器对服务器管理器的引用
        tool_manager.server_manager = server_manager
        
        # 从PostgreSQL服务器发现工具（同步执行，确保工具可用）
        logger.info("Discovering tools from PostgreSQL server...")
        try:
            await tool_manager.discover_tools_from_server("postgres-server")
        except Exception as e:
            logger.warning(f"PostgreSQL tool discovery failed: {e}")
        
        # 从MCP服务器动态发现工具（异步执行，不阻塞启动）
        logger.info("Starting tool discovery from MCP servers...")
        asyncio.create_task(tool_manager.discover_tools_from_servers())
        
        # 初始化执行服务
        logger.info("Initializing execution service...")
        execution_service = ToolExecutionService(tool_manager)
        
        # 设置API路由的依赖
        execution.execution_service = execution_service
        servers.server_manager = server_manager
        servers.tool_manager = tool_manager
        tools.tool_manager = tool_manager
        
        logger.info("Generic MCP Service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        raise

async def shutdown_event():
    """应用关闭时清理服务"""
    logger.info("Shutting down Generic MCP Service...")

# 根端点
@app.get("/")
async def root():
    """根端点"""
    return {
        "message": "Generic MCP Service",
        "version": "1.0.0",
        "description": "专注于工具管理的通用MCP服务",
        "docs": "/docs",
        "health": "/health",
        "features": [
            "工具注册和管理",
            "工具执行和监控",
            "配置驱动的工具定义",
            "支持多种工具类型",
            "RESTful API接口"
        ]
    }

# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        health_status = {
            "status": "healthy",
            "service": "Generic MCP Service",
            "tools_count": len(tool_manager.get_all_tools()) if tool_manager else 0,
            "active_tools": len(tool_manager.get_active_tools()) if tool_manager else 0,
            "servers_count": len(server_manager.get_all_servers()) if server_manager else 0,
            "active_servers": len(server_manager.get_active_servers()) if server_manager else 0
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

# 服务信息端点
@app.get("/info")
async def service_info():
    """服务信息"""
    if not tool_manager:
        return {"error": "Tool manager not initialized"}
    
    stats = tool_manager.get_tool_stats()
    categories = tool_manager.get_tool_categories()
    tags = tool_manager.get_tool_tags()
    
    return {
        "service": "Generic MCP Service",
        "version": "1.0.0",
        "statistics": stats,
        "categories": categories,
        "tags": tags,
        "api_endpoints": {
            "tools": "/api/v1/tools",
            "execution": "/api/v1/execution",
            "docs": "/docs"
        }
    }

# 注册路由
app.include_router(
    execution.router, 
    prefix="/api/v1/execution", 
    tags=["execution"]
)
app.include_router(
    servers.router, 
    prefix="/api/v1/servers", 
    tags=["servers"]
)
app.include_router(
    tools.router, 
    prefix="/api/v1/tools", 
    tags=["tools"]
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
