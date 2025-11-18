"""
Agent系统API路由
基于新架构的深度研究系统
"""
import asyncio
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime

from services.agent_orchestration import ODRResearchOrchestrator as EnhancedResearchOrchestrator
from service.auth_service import get_current_user
from models.user_models import User

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/agents", tags=["agents"])

# 全局编排器实例
orchestrator_instance: Optional[EnhancedResearchOrchestrator] = None


class TaskRequest(BaseModel):
    """任务请求模型"""
    query: str = Field(..., description="研究问题")
    context: Optional[Dict[str, Any]] = Field(default=None, description="任务上下文信息")
    research_depth: str = Field(default="comprehensive", description="研究深度: basic/standard/comprehensive")
    allow_clarification: bool = Field(default=False, description="是否允许澄清")


class TaskResponse(BaseModel):
    """任务响应模型"""
    task_id: str
    status: str
    query: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    timestamp: str


class AgentInfo(BaseModel):
    """Agent信息模型"""
    name: str
    description: str
    status: str
    capabilities: List[str]


class SystemStatus(BaseModel):
    """系统状态模型"""
    orchestrator_status: Dict[str, Any]
    available_agents: Dict[str, AgentInfo]
    system_metrics: Optional[Dict[str, Any]] = None


async def get_orchestrator() -> EnhancedResearchOrchestrator:
    """获取编排器实例（单例模式）"""
    global orchestrator_instance

    if orchestrator_instance is None:
        orchestrator_instance = EnhancedResearchOrchestrator()
        await orchestrator_instance.initialize()
        logger.info("增强版研究编排器实例已创建并初始化")

    return orchestrator_instance


@router.post("/tasks", response_model=TaskResponse)
async def create_task(
    request: TaskRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    创建研究任务
    """
    try:
        # 生成任务ID
        task_id = f"agent_task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(request.query) % 10000}"

        logger.info(f"创建Agent任务 {task_id}: {request.query}")

        # 获取编排器并执行任务
        async def execute_task():
            try:
                orchestrator = await get_orchestrator()

                result = await orchestrator.process_research_request(
                    question=request.query,
                    user_context={
                        **(request.context or {}),
                        "user_id": current_user.user_id if current_user else "anonymous",
                        "task_id": task_id
                    },
                    allow_clarification=request.allow_clarification
                )

                # 这里可以保存任务结果到数据库或缓存
                logger.info(f"Agent任务 {task_id} 完成")

            except Exception as e:
                logger.error(f"Agent任务 {task_id} 失败: {e}")

        # 后台执行任务
        background_tasks.add_task(execute_task)

        return TaskResponse(
            task_id=task_id,
            status="started",
            query=request.query,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"创建Agent任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_status(
    task_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    获取任务状态
    """
    # 这里可以从数据库或缓存查询任务状态
    # 目前返回一个简单的状态
    return TaskResponse(
        task_id=task_id,
        status="not_implemented",
        query="状态查询功能待实现",
        timestamp=datetime.now().isoformat()
    )


@router.get("/status", response_model=SystemStatus)
async def get_system_status(
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    获取系统状态
    """
    try:
        orchestrator = await get_orchestrator()

        # Agent信息
        agents = {
            "clarification_agent": AgentInfo(
                name="用户澄清代理",
                description="分析用户问题，判断是否需要澄清",
                status="active",
                capabilities=["问题分析", "澄清需求判断"]
            ),
            "planning_agent": AgentInfo(
                name="研究规划代理",
                description="制定结构化研究计划",
                status="active",
                capabilities=["研究规划", "任务分解", "时间估算"]
            ),
            "supervisor_subgraph": AgentInfo(
                name="监督者子图",
                description="管理研究任务分配和协调",
                status="active",
                capabilities=["任务分配", "进度监控", "并行协调"]
            ),
            "researcher_subgraph": AgentInfo(
                name="研究者子图",
                description="执行具体的研究任务",
                status="active",
                capabilities=["信息收集", "数据分析", "结果整合"]
            ),
            "final_report_generator": AgentInfo(
                name="报告生成器",
                description="生成最终研究报告",
                status="active",
                capabilities=["报告生成", "格式化输出", "质量检查"]
            )
        }

        # 编排器状态
        orchestrator_status = {
            "status": "active" if orchestrator.initialized else "inactive",
            "initialized": orchestrator.initialized,
            "config": orchestrator.config.__dict__ if hasattr(orchestrator, 'config') else {}
        }

        return SystemStatus(
            orchestrator_status=orchestrator_status,
            available_agents=agents,
            system_metrics={
                "active_tasks": 0,  # 这里可以实现实际的任务计数
                "total_completed": 0,
                "uptime": "unknown"
            }
        )

    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.post("/research", response_model=Dict[str, Any])
async def direct_research(
    request: TaskRequest,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    直接执行研究任务（同步方式）
    """
    try:
        logger.info(f"直接执行研究: {request.query}")

        orchestrator = await get_orchestrator()

        # 执行研究
        result = await orchestrator.process_research_request(
            question=request.query,
            user_context={
                **(request.context or {}),
                "user_id": current_user.user_id if current_user else "anonymous"
            },
            allow_clarification=request.allow_clarification
        )

        return {
            "success": True,
            "task_id": f"direct_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "status": result.status,
            "question": result.question,
            "key_findings_count": len(result.key_findings),
            "final_report": result.final_report,
            "metadata": result.metadata
        }

    except Exception as e:
        logger.error(f"直接研究失败: {e}")
        raise HTTPException(status_code=500, detail=f"研究失败: {str(e)}")


@router.get("/health")
async def health_check():
    """
    健康检查
    """
    return {
        "status": "healthy",
        "service": "Enhanced Research Agent System",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    }


# 启动和关闭函数
async def startup_agent_system():
    """启动Agent系统"""
    try:
        logger.info("启动Agent系统...")
        # 全局编排器会在第一次使用时初始化
        logger.info("Agent系统启动完成")
    except Exception as e:
        logger.error(f"Agent系统启动失败: {e}")


async def shutdown_agent_system():
    """关闭Agent系统"""
    try:
        global orchestrator_instance
        if orchestrator_instance:
            await orchestrator_instance.cleanup()
            orchestrator_instance = None
        logger.info("Agent系统已关闭")
    except Exception as e:
        logger.error(f"Agent系统关闭失败: {e}")