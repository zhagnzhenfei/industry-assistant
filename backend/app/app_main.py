from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from router import document_router, search_router, research_router, user_router, assistant_router, assistant_chat_router, mcp_router, agent_router, memory_router
from router.enhanced_research_router_simple import router as enhanced_research_router
from router.chart_router import router as chart_router
from router.agent_router import startup_agent_system, shutdown_agent_system
import logging
import os

# 加载.env文件（关键！）
from dotenv import load_dotenv
load_dotenv()

# 配置日志
log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# 设置第三方库的日志级别
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化所有系统
    await startup_agent_system()
    logger = logging.getLogger(__name__)
    logger.info("Agent系统启动完成")

    yield

    # 关闭时清理所有系统
    await shutdown_agent_system()
    logger.info("Agent系统已关闭")

app = FastAPI(
    title="AI Application",
    description="AI应用后端服务",
    version="1.0.0",
    lifespan=lifespan
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源，生产环境中应该设置具体的源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头
)

# 包含路由
app.include_router(document_router)
app.include_router(search_router)
app.include_router(research_router)
app.include_router(user_router)
app.include_router(assistant_router)
app.include_router(assistant_chat_router)
app.include_router(mcp_router)
app.include_router(agent_router)
app.include_router(enhanced_research_router)
app.include_router(chart_router)
app.include_router(memory_router)

@app.get("/hello")
async def hello_world():
    """
    Simple hello world endpoint for network verification
    """
    return {
        "status": "success",
        "message": "Hello World! The API is working correctly."
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint for Docker and load balancer
    """
    return {
        "status": "healthy",
        "timestamp": "2025-01-20T21:30:00Z",
        "service": "AI Application Backend",
        "version": "1.0.0"
    }

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
