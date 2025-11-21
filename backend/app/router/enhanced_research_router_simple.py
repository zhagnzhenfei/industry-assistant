"""
优化版增强研究报告API路由

使用记忆装饰器框架，大幅简化记忆处理逻辑
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime
import asyncio
import json

from services.research_service import execute_research_task_stream
from services.agent_orchestration.odr_orchestrator import ResearchResult
from service.auth_service import get_current_user
from models.user_models import User

# 记忆装饰器框架（新增）
from services.memory.decorators import research_memory

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/enhanced-research", tags=["enhanced-research"])


class EnhancedResearchRequest(BaseModel):
    """增强版研究报告请求模型"""
    question: str = Field(..., description="研究问题", min_length=5, max_length=500)
    user_context: Optional[Dict[str, Any]] = Field(default=None, description="用户上下文信息")
    allow_clarification: bool = Field(default=False, description="是否允许请求澄清")
    research_depth: str = Field(default="comprehensive", description="研究深度: basic/standard/comprehensive")
    memory_mode: str = Field(default="smart", description="记忆模式: none/short_term/long_term/smart")

    class Config:
        schema_extra = {
            "example": {
                "question": "Python高级编程技巧和设计模式的应用",
                "allow_clarification": False,
                "research_depth": "standard",
                "memory_mode": "smart"
            }
        }


class ResearchReportResponse(BaseModel):
    """研究报告响应模型"""
    research_id: str
    question: str
    status: str
    final_report: str
    key_findings: list
    metadata: Dict[str, Any]
    quality_score: float
    duration: float
    created_at: str


@router.post("/generate")
@research_memory(
    memory_mode_param="memory_mode",
    user_context_param="enhanced_context",
    auto_save=True
)
async def generate_enhanced_research_report(
    request: EnhancedResearchRequest,
    current_user: User = Depends(get_current_user),
    enhanced_context: Optional[Dict[str, Any]] = None
):
    """
    生成优化版增强研究报告 - 使用记忆装饰器框架

    特性：
    - 🧠 自动记忆功能：智能加载历史研究记忆
    - 🚀 即插即用：装饰器自动处理所有记忆逻辑
    - 📊 上下文增强：基于历史记忆提供更相关的研究结果
    - 💾 自动保存：研究完成后自动保存到记忆系统
    - 🔄 向后兼容：与原接口格式完全一致

    Args:
        request: 研究请求，包含问题、配置和记忆模式
        current_user: 当前认证用户
        enhanced_context: 由记忆装饰器注入的增强上下文

    Returns:
        流式响应，包含研究过程和最终结果
    """
    research_id = f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(request.question) % 10000}"
    user_id = current_user.user_id

    logger.info(f"🚀 [OPTIMIZED_RESEARCH] 开始处理研究请求 {research_id}")
    logger.info(f"📝 [OPTIMIZED_RESEARCH] 问题: {request.question}")
    logger.info(f"⚙️ [OPTIMIZED_RESEARCH] 深度: {request.research_depth}, 澄清: {request.allow_clarification}")

    # 记忆信息日志
    if enhanced_context:
        memory_count = enhanced_context.get("memory_count", 0)
        logger.info(f"🧠 [OPTIMIZED_RESEARCH] 记忆状态: 已启用，找到 {memory_count} 条相关记忆")
        if memory_count > 0:
            logger.info(f"📋 [OPTIMIZED_RESEARCH] 记忆预览: {enhanced_context.get('memory_context', '')[:100]}...")
    else:
        logger.info(f"🧠 [OPTIMIZED_RESEARCH] 记忆状态: 未启用或无相关记忆")

    # 增强用户上下文
    final_context = request.user_context or {}

    # 合并记忆上下文（如果有的话）
    if enhanced_context and enhanced_context.get("has_memories"):
        final_context.update({
            "memory_enabled": True,
            "memory_count": enhanced_context.get("memory_count", 0),
            "memory_context": enhanced_context.get("memory_context", ""),
            "historical_memories": enhanced_context.get("memories", [])
        })

        # 为研究任务添加记忆提示
        memory_prompt = f"""
=== 历史研究记忆 ===
用户之前有相关的研究背景：
{enhanced_context.get('memory_context', '无历史记忆')}

=== 研究建议 ===
基于以上历史记忆，请：
1. 避免重复已知的信息
2. 重点关注新的发现和进展
3. 在适当的时候引用历史研究成果
4. 提供更有针对性的深度分析
"""

        final_context["memory_prompt"] = memory_prompt
        logger.info(f"🎯 [OPTIMIZED_RESEARCH] 已添加记忆提示，长度: {len(memory_prompt)} 字符")

    async def generate_stream():
        """生成流式响应"""
        try:
            final_result = None

            # 发送初始信息
            initial_data = {
                'type': 'start',
                'research_id': research_id,
                'question': request.question,
                'message': '🚀 开始处理优化版研究请求（支持记忆功能）',
                'memory_info': {
                    'enabled': enhanced_context is not None,
                    'memory_count': enhanced_context.get('memory_count', 0) if enhanced_context else 0
                } if enhanced_context else None,
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"📤 [STREAM_START] {research_id}: {initial_data['message']}")
            yield f"data: {json.dumps(initial_data, ensure_ascii=False)}\n\n"

            # 执行研究任务（使用增强的上下文）
            async for progress_data in execute_research_task_stream(
                research_id=research_id,
                question=request.question,
                user_context=final_context,
                allow_clarification=request.allow_clarification,
                research_depth=request.research_depth,
                memory_mode=request.memory_mode,
                memory_service=None  # 装饰器已处理记忆服务
            ):
                # 检查是否是最终结果
                if progress_data.get('type') == 'result':
                    final_result = progress_data.get('result') or progress_data.get('final_result')
                    if final_result and not isinstance(final_result, ResearchResult):
                        final_result = ResearchResult(
                            question=final_result.get('question', request.question),
                            final_report=final_result.get('final_report', ''),
                            status=final_result.get('status', 'completed'),
                            key_findings=final_result.get('key_findings', []),
                            raw_notes=final_result.get('raw_notes', []),
                            metadata=final_result.get('metadata', {}),
                            progress=final_result.get('progress', 100.0)
                        )

                # 添加记忆信息到进度数据
                if enhanced_context and enhanced_context.get("has_memories"):
                    progress_data['memory_enhanced'] = True
                    progress_data['memory_count'] = enhanced_context.get('memory_count', 0)

                # 发送进度数据
                progress_type = progress_data.get('type')
                if progress_type == 'progress':
                    logger.info(f"📊 [STREAM_PROGRESS] {research_id}: {progress_data.get('message', '')} ({progress_data.get('progress', 0):.1f}%)")
                elif progress_type == 'result':
                    quality_score = progress_data.get('quality_score', 0)
                    logger.info(f"📋 [STREAM_RESULT] {research_id}: 研究完成，质量评分 {quality_score:.1f}分")

                yield f"data: {json.dumps(progress_data, ensure_ascii=False)}\n\n"

            # 发送完成信息
            complete_data = {
                'type': 'complete',
                'research_id': research_id,
                'message': '✅ 优化版研究任务完成（记忆功能已自动保存）',
                'memory_saved': enhanced_context is not None if enhanced_context else False,
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"✅ [STREAM_COMPLETE] {research_id}: 流式响应完成")
            yield f"data: {json.dumps(complete_data, ensure_ascii=False)}\n\n"

        except Exception as e:
            error_message = f'优化版研究请求失败: {str(e)}'
            logger.error(f"💥 [STREAM_ERROR] {research_id}: {error_message}")

            error_data = {
                'type': 'error',
                'research_id': research_id,
                'message': error_message,
                'timestamp': datetime.now().isoformat()
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Research-Version": "v2-optimized-with-memory"
        }
    )


@router.get("/memory-status")
async def get_memory_status(current_user: User = Depends(get_current_user)):
    """
    获取用户记忆状态

    Args:
        current_user: 当前认证用户

    Returns:
        记忆状态信息
    """
    try:
        from services.memory.manager import MemoryManager

        memory_manager = MemoryManager()
        await memory_manager.initialize()

        stats = await memory_manager.get_memory_stats(current_user.user_id)

        return {
            "status": "success",
            "memory_enabled": stats.get("enabled", False),
            "total_memories": stats.get("total_memories", 0),
            "memories_by_type": stats.get("by_type", {}),
            "available_strategies": stats.get("strategies_available", [])
        }

    except Exception as e:
        logger.error(f"获取记忆状态失败: {e}")
        return {
            "status": "error",
            "message": str(e),
            "memory_enabled": False
        }


@router.post("/test-memory")
@research_memory(memory_mode_param="memory_mode")
async def test_memory_functionality(
    request: EnhancedResearchRequest,
    current_user: User = Depends(get_current_user),
    enhanced_context: Optional[Dict[str, Any]] = None
):
    """
    测试记忆功能

    Args:
        request: 测试请求
        current_user: 当前用户
        enhanced_context: 增强上下文

    Returns:
        测试结果
    """
    return {
        "status": "success",
        "message": "记忆功能测试成功",
        "memory_enabled": enhanced_context is not None,
        "memory_count": enhanced_context.get("memory_count", 0) if enhanced_context else 0,
        "question": request.question,
        "memory_mode": request.memory_mode,
        "user_id": current_user.user_id
    }