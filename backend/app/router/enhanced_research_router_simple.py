"""
简化版增强研究报告API路由
流式输出执行过程，实时展示研究规划、执行步骤和最终结果
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List, AsyncGenerator
from datetime import datetime
import asyncio
import json

from services.research_service import execute_research_task_stream, save_research_memory
from services.agent_orchestration.odr_orchestrator import ResearchResult
from service.auth_service import get_current_user
from models.user_models import User

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
    previous_context_ids: Optional[List[str]] = Field(default=None, description="关联的历史研究ID")


class ResearchReportResponse(BaseModel):
    """研究报告响应模型"""
    research_id: str
    question: str
    status: str
    final_report: str
    key_findings: List[str]
    metadata: Dict[str, Any]
    quality_score: float
    duration: float
    created_at: str


@router.post("/generate")
async def generate_enhanced_research_report(
    request: EnhancedResearchRequest,
    current_user: User = Depends(get_current_user)  # 必须认证
):
    """
    生成增强版深度研究报告（带记忆功能）
    
    注意：此接口需要JWT认证，不支持匿名访问
    """
    research_id = f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(request.question) % 10000}"

    # 获取用户ID（必须认证，所以一定有user_id）
    user_id = current_user.user_id

    logger.info(f"🚀 [REQUEST_START] 开始处理研究请求 {research_id}")
    logger.info(f"📝 [REQUEST_INFO] 问题: {request.question}")
    logger.info(f"⚙️ [REQUEST_CONFIG] 澄清={request.allow_clarification}, 深度={request.research_depth}")
    logger.info(f"🧠 [MEMORY] 记忆模式: {request.memory_mode}, 用户: {user_id}")

    # 记忆服务初始化
    from services.memory.memory_factory import get_memory_service
    memory_service = get_memory_service()

    # 增强用户上下文
    enriched_context = request.user_context or {}
    enriched_context["user_id"] = user_id
    enriched_context["memory_mode"] = request.memory_mode

    # 如果启用记忆且有有效服务，加载用户记忆
    # 注意：这里使用简化实现，第四阶段可以使用 MemoryModeStrategy 类优化
    if request.memory_mode != "none" and memory_service:
        try:
            logger.info(f"🧠 [MEMORY] 正在加载用户记忆，模式: {request.memory_mode}")
            
            if request.memory_mode == "smart":
                # smart 模式：搜索相关记忆（语义搜索）
                user_memories = await memory_service.search_memories(
                    user_id=user_id,
                    query=request.question,
                    limit=10
                )
            elif request.memory_mode == "short_term":
                # short_term 模式：获取最近记忆（简化版，第四阶段可以使用策略类优化）
                all_memories = await memory_service.get_all_memories(user_id, limit=20)
                user_memories = all_memories[:10]  # 简化：取前10条
            elif request.memory_mode == "long_term":
                # long_term 模式：获取所有历史记忆
                user_memories = await memory_service.get_all_memories(user_id, limit=20)
            else:  # none
                user_memories = []
            
            enriched_context["user_memories"] = user_memories
            enriched_context["memory_loaded"] = True
            logger.info(f"✅ [MEMORY] 记忆加载完成，找到 {len(user_memories)} 条记忆")
        except Exception as e:
            logger.warning(f"⚠️ [MEMORY] 记忆加载失败: {e}，继续无记忆执行")
            enriched_context["user_memories"] = []
            enriched_context["memory_loaded"] = False
    
    async def generate_research_stream():
        """生成研究流式响应"""
        try:
            final_result = None  # 用于保存最终研究结果
            
            # 发送初始信息
            initial_data = {
                'type': 'start',
                'research_id': research_id,
                'question': request.question,
                'message': '🚀 开始处理研究请求',
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"📤 [STREAM_SEND] {research_id}: {initial_data['message']}")
            yield f"data: {json.dumps(initial_data, ensure_ascii=False)}\n\n"
            
            # 执行研究任务（流式），使用增强的上下文和记忆模式
            async for progress_data in execute_research_task_stream(
                research_id=research_id,
                question=request.question,
                user_context=enriched_context,
                allow_clarification=request.allow_clarification,
                research_depth=request.research_depth,
                memory_mode=request.memory_mode,
                memory_service=memory_service
            ):
                # 检查是否是最终结果
                if progress_data.get('type') == 'result':
                    # 从进度数据中提取 ResearchResult 对象
                    # execute_research_task_stream 已在 progress_data 中添加 'final_result' 字段
                    final_result = progress_data.get('final_result')
                    if not final_result:
                        # 如果 execute_research_task_stream 没有添加，则从 'result' 字段提取
                        final_result_data = progress_data.get('result')
                        if final_result_data:
                            final_result = final_result_data if isinstance(final_result_data, ResearchResult) else ResearchResult(
                                question=final_result_data.get('question', request.question),
                                final_report=final_result_data.get('final_report', ''),
                                status=final_result_data.get('status', 'completed'),
                                key_findings=final_result_data.get('key_findings', []),
                                raw_notes=final_result_data.get('raw_notes', []),
                                metadata=final_result_data.get('metadata', {}),
                                progress=final_result_data.get('progress', 100.0)
                            )
                
                # 根据数据类型记录不同的日志
                if progress_data.get('type') == 'progress':
                    logger.info(f"📊 [STREAM_PROGRESS] {research_id}: {progress_data.get('message', '')} ({progress_data.get('progress', 0):.1f}%)")
                elif progress_data.get('type') == 'result':
                    logger.info(f"📋 [STREAM_RESULT] {research_id}: 研究完成，质量评分 {progress_data.get('quality_score', 0):.1f}分")
                    logger.info(f"📄 [STREAM_REPORT] {research_id}: 报告长度 {len(progress_data.get('final_report', ''))} 字符")
                else:
                    logger.info(f"📤 [STREAM_SEND] {research_id}: {progress_data.get('message', 'Unknown message')}")
                
                yield f"data: {json.dumps(progress_data, ensure_ascii=False)}\n\n"
            
            # 异步保存研究记忆（不阻塞响应）
            # 注意：只有在有最终结果且启用记忆时才保存
            if request.memory_mode != "none" and memory_service and final_result:
                asyncio.create_task(save_research_memory(
                    user_id=user_id,
                    research_id=research_id,
                    question=request.question,
                    result=final_result,
                    memory_service=memory_service
                ))
                logger.info(f"💾 [MEMORY] 已启动异步记忆保存任务: {research_id}")
            
            # 发送完成信息
            complete_data = {
                'type': 'complete',
                'research_id': research_id,
                'message': '✅ 研究任务完成',
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"✅ [STREAM_COMPLETE] {research_id}: 流式响应完成")
            yield f"data: {json.dumps(complete_data, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            # 错误处理
            logger.error(f"💥 [STREAM_FAILED] {research_id}: 流式响应失败: {e}")
            import traceback
            logger.error(f"🔍 [STREAM_ERROR] {research_id}: 异常堆栈:\n{traceback.format_exc()}")
            
            error_data = {
                'type': 'error',
                'research_id': research_id,
                'message': f'研究请求失败: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
            logger.error(f"📤 [STREAM_ERROR] {research_id}: 发送错误响应")
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_research_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
