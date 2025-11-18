"""
研究服务层
处理研究任务的核心业务逻辑
"""
import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator, List

from services.agent_orchestration.odr_orchestrator import ODRResearchOrchestrator, ResearchResult
from services.agent_orchestration.odr_configuration import Configuration

# LangSmith 集成
try:
    from utils.langsmith_integration import (
        get_langsmith_integration,
        trace_research_step,
        log_research_start,
        log_research_complete,
        is_langsmith_enabled,
        get_langsmith_config
    )
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    # 提供空实现
    def trace_research_step(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

    def log_research_start(*args, **kwargs):
        pass

    def log_research_complete(*args, **kwargs):
        pass

    def is_langsmith_enabled():
        return False

    def get_langsmith_config(*args, **kwargs):
        return {}

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv 未安装，跳过

logger = logging.getLogger(__name__)

# 配置日志
if not logger.handlers:
    # 防止日志重复
    logger.propagate = False
    
    # 根据环境变量设置日志级别
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # 添加控制台 handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level, logging.INFO))
    
    # 设置格式
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)

# 全局编排器实例
orchestrator: Optional[ODRResearchOrchestrator] = None

# 研究任务状态管理
research_tasks: Dict[str, ResearchResult] = {}


async def get_orchestrator(research_depth: str = "comprehensive") -> ODRResearchOrchestrator:
    """获取编排器实例（单例模式）"""
    global orchestrator

    if orchestrator is None:
        # 使用 Configuration 的默认值，便于统一管理
        # 默认值在 odr_configuration.py 中定义
        config = Configuration(
            # max_researcher_iterations=3  # 使用默认值
            # max_concurrent_research_units=5  # 使用默认值
            # max_react_tool_calls=10  # 使用默认值
            allow_clarification=True,
            search_api="serper"
        )
        orchestrator = ODRResearchOrchestrator(config)
        # 添加超时保护
        try:
            await asyncio.wait_for(orchestrator.initialize(), timeout=10.0)
            logger.info(f"Open Deep Research 编排器已创建并初始化")
        except asyncio.TimeoutError:
            logger.error("编排器初始化超时")
            raise Exception("编排器初始化超时")

    return orchestrator


@trace_research_step("execute_research_task", ["research", "execution"])
async def execute_research_task(
    research_id: str,
    question: str,
    user_context: Optional[Dict[str, Any]] = None,
    allow_clarification: bool = False,
    research_depth: str = "comprehensive"
):
    """执行研究任务的后台函数"""
    # LangSmith 追踪开始
    user_id = user_context.get("user_id") if user_context else None
    log_research_start(question, user_id)

    logger.info(f"🚀 [TASK_START] 开始执行研究任务 {research_id}")
    logger.info(f"📝 [TASK_INFO] 问题: {question}")
    logger.info(f"⚙️ [TASK_CONFIG] 澄清={allow_clarification}, 深度={research_depth}")
    
    # 立即更新任务状态，表明任务已开始执行
    if research_id in research_tasks:
        research_tasks[research_id].status = "starting"
        research_tasks[research_id].progress = 5.0
        research_tasks[research_id].metadata["updated_at"] = datetime.now().isoformat()
        logger.info(f"🔄 [STATUS_UPDATE] 任务状态更新为: starting (5%)")
    
    try:
        # 步骤1: 获取编排器
        logger.info(f"🔧 [STEP_1] 正在获取编排器实例...")
        enh_orchestrator = await get_orchestrator(research_depth)
        logger.info(f"✅ [STEP_1] 编排器获取成功")

        # 创建进度回调函数
        def progress_callback(state):
            logger.info(f"📊 [PROGRESS] 任务 {research_id} 进度更新: {state.status} ({state.progress:.1f}%)")
            if research_id in research_tasks:
                # 更新研究任务的状态，从ResearchState转换为ResearchResult
                result = research_tasks[research_id]
                old_status = result.status
                old_progress = result.progress
                result.status = state.status.value if hasattr(state.status, 'value') else str(state.status)
                result.progress = state.progress
                result.metadata["updated_at"] = datetime.now().isoformat()
                
                # 详细的状态变化日志
                if old_status != result.status or abs(old_progress - result.progress) >= 5:
                    logger.info(f"🔄 [STATUS_CHANGE] {research_id}: {old_status}({old_progress:.1f}%) → {result.status}({result.progress:.1f}%)")
            else:
                logger.error(f"❌ [ERROR] 研究任务 {research_id} 不存在于 research_tasks 中")

        # 步骤2: 更新状态为研究中
        logger.info(f"🔍 [STEP_2] 开始执行研究流程...")
        research_tasks[research_id].status = "researching"
        research_tasks[research_id].metadata["updated_at"] = datetime.now().isoformat()

        # 步骤3: 执行完整研究流程
        logger.info(f"⚡ [STEP_3] 调用编排器处理研究请求...")
        start_time = datetime.now()
        result = await enh_orchestrator.process_research_request(
            question=question,
            user_context=user_context,
            allow_clarification=allow_clarification,
            progress_callback=progress_callback
        )
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # LangSmith 追踪完成
        log_research_complete(question, duration, len(result.key_findings))

        logger.info(f"✅ [STEP_3] 研究流程执行完成，耗时: {duration:.2f}秒")
        logger.info(f"📋 [RESULT] 最终状态: {result.status}, 进度: {result.progress:.1f}%")

        # 步骤4: 保存最终结果
        logger.info(f"💾 [STEP_4] 保存研究结果...")
        result.metadata["updated_at"] = datetime.now().isoformat()
        result.metadata["execution_duration"] = duration
        research_tasks[research_id] = result

        logger.info(f"🎉 [TASK_COMPLETE] 研究任务 {research_id} 成功完成！")
        logger.info(f"📊 [FINAL_STATS] 状态: {result.status}, 关键发现: {len(result.key_findings)}个, 时长: {duration:.2f}秒")

    except Exception as e:
        logger.error(f"💥 [TASK_FAILED] 研究任务 {research_id} 执行失败: {e}")
        import traceback
        logger.error(f"🔍 [ERROR_DETAILS] 异常堆栈:\n{traceback.format_exc()}")
        
        # 更新失败状态
        if research_id in research_tasks:
            research_tasks[research_id].status = "failed"
            research_tasks[research_id].metadata["error"] = str(e)
            research_tasks[research_id].metadata["error_traceback"] = traceback.format_exc()
            research_tasks[research_id].metadata["updated_at"] = datetime.now().isoformat()
            logger.error(f"❌ [STATUS_UPDATE] 已更新失败状态，research_id={research_id}")
        else:
            logger.error(f"❌ [CRITICAL] 任务 {research_id} 不存在，无法更新失败状态")


def get_research_task(research_id: str) -> Optional[ResearchResult]:
    """获取研究任务状态"""
    return research_tasks.get(research_id)


def get_all_research_tasks() -> Dict[str, ResearchResult]:
    """获取所有研究任务状态"""
    return research_tasks.copy()


def get_active_research_tasks() -> Dict[str, ResearchResult]:
    """获取活跃的研究任务（非完成状态）"""
    return {
        task_id: task 
        for task_id, task in research_tasks.items() 
        if task.status not in ["completed", "failed"]
    }


async def execute_research_task_sync(
    research_id: str,
    question: str,
    user_context: Optional[Dict[str, Any]] = None,
    allow_clarification: bool = False,
    research_depth: str = "comprehensive"
) -> ResearchResult:
    """同步执行研究任务（阻塞式）"""
    logger.info(f"🚀 [SYNC_START] 开始同步执行研究任务 {research_id}")
    logger.info(f"📝 [SYNC_INFO] 问题: {question}")
    logger.info(f"⚙️ [SYNC_CONFIG] 澄清={allow_clarification}, 深度={research_depth}")
    
    # 创建任务记录
    initial_result = ResearchResult(
        question=question,
        status="starting",
        progress=0.0,
        metadata={
            "research_id": research_id,
            "user_id": "test_user",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "request_clarification": allow_clarification,
            "research_depth": research_depth
        }
    )
    research_tasks[research_id] = initial_result
    logger.info(f"📝 [TASK_CREATED] 创建研究任务 {research_id}")
    
    try:
        # 步骤1: 获取编排器
        logger.info(f"🔧 [STEP_1] 正在获取编排器实例...")
        enh_orchestrator = await get_orchestrator(research_depth)
        logger.info(f"✅ [STEP_1] 编排器获取成功")
        
        # 更新进度
        research_tasks[research_id].status = "initializing"
        research_tasks[research_id].progress = 10.0
        research_tasks[research_id].metadata["updated_at"] = datetime.now().isoformat()
        logger.info(f"🔄 [PROGRESS] 初始化完成 (10%)")

        # 步骤2: 开始研究流程
        logger.info(f"🔍 [STEP_2] 开始执行研究流程...")
        research_tasks[research_id].status = "researching"
        research_tasks[research_id].progress = 20.0
        research_tasks[research_id].metadata["updated_at"] = datetime.now().isoformat()

        # 创建简单的进度回调函数（处理浮点数进度）
        def simple_progress_callback(progress_value):
            if isinstance(progress_value, (int, float)):
                logger.info(f"📊 [PROGRESS] 任务 {research_id} 进度更新: {progress_value:.1f}%")
                if research_id in research_tasks:
                    research_tasks[research_id].progress = float(progress_value)
                    research_tasks[research_id].metadata["updated_at"] = datetime.now().isoformat()
            else:
                logger.info(f"📊 [PROGRESS] 任务 {research_id} 状态更新: {progress_value}")

        # 步骤3: 执行完整研究流程
        logger.info(f"⚡ [STEP_3] 调用编排器处理研究请求...")
        start_time = datetime.now()
        result = await enh_orchestrator.process_research_request(
            question=question,
            user_context=user_context,
            allow_clarification=allow_clarification,
            progress_callback=simple_progress_callback
        )
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"✅ [STEP_3] 研究流程执行完成，耗时: {duration:.2f}秒")
        logger.info(f"📋 [RESULT] 最终状态: {result.status}, 进度: {result.progress:.1f}%")

        # 步骤4: 保存最终结果
        logger.info(f"💾 [STEP_4] 保存研究结果...")
        result.metadata["updated_at"] = datetime.now().isoformat()
        result.metadata["execution_duration"] = duration
        research_tasks[research_id] = result

        logger.info(f"🎉 [SYNC_COMPLETE] 研究任务 {research_id} 成功完成！")
        logger.info(f"📊 [FINAL_STATS] 状态: {result.status}, 关键发现: {len(result.key_findings)}个, 时长: {duration:.2f}秒")
        
        return result

    except Exception as e:
        logger.error(f"💥 [SYNC_FAILED] 研究任务 {research_id} 执行失败: {e}")
        import traceback
        logger.error(f"🔍 [ERROR_DETAILS] 异常堆栈:\n{traceback.format_exc()}")
        
        # 更新失败状态
        if research_id in research_tasks:
            research_tasks[research_id].status = "failed"
            research_tasks[research_id].metadata["error"] = str(e)
            research_tasks[research_id].metadata["error_traceback"] = traceback.format_exc()
            research_tasks[research_id].metadata["updated_at"] = datetime.now().isoformat()
            return research_tasks[research_id]
        else:
            # 创建一个失败的结果
            return ResearchResult(
                question=question,
                status="failed",
                progress=0.0,
                metadata={
                    "research_id": research_id,
                    "error": str(e),
                    "error_traceback": traceback.format_exc(),
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
            )


def build_memory_prompt(question: str, memories: List[Dict[str, Any]]) -> str:
    """
    将用户记忆转换为研究提示
    
    Args:
        question: 研究问题
        memories: 用户记忆列表
        
    Returns:
        格式化的记忆提示字符串
    """
    if not memories:
        return ""

    prompt_parts = ["=== 相关历史研究记忆 ==="]

    for i, memory in enumerate(memories[:5], 1):  # 限制5条最相关的
        content = memory.get("memory", "")
        if isinstance(content, dict):
            content = content.get("content", str(content))

        # 提取关键信息
        metadata = memory.get("metadata", {})
        if metadata.get("type") == "research_result":
            # 这是研究类型的记忆
            prompt_parts.append(f"{i}. 研究主题: {metadata.get('question', '未知主题')}")
            if metadata.get("key_findings_count", 0) > 0:
                prompt_parts.append(f"   关键发现数: {metadata['key_findings_count']}")
            if metadata.get("quality_score"):
                prompt_parts.append(f"   研究质量: {metadata['quality_score']:.1f}/10")
        else:
            # 普通记忆
            prompt_parts.append(f"{i}. {content[:200]}...")  # 限制长度

    prompt_parts.append("=== 请基于以上历史研究，避免重复内容，提供新的见解 ===")

    return "\n".join(prompt_parts)


async def save_research_memory(
    user_id: str,
    research_id: str,
    question: str,
    result: ResearchResult,
    memory_service
) -> bool:
    """
    保存研究记忆到 Mem0 系统
    
    Args:
        user_id: 用户ID（已认证用户）
        research_id: 研究任务ID
        question: 研究问题
        result: 研究结果对象
        memory_service: Mem0记忆服务实例
        
    Returns:
        bool: 保存是否成功
    """
    try:
        logger.info(f"💾 [MEMORY_SAVE] 开始保存研究记忆: {research_id}")

        # 构建记忆内容
        content = f"""研究主题: {question}

研究报告:
{result.final_report[:2000] if result.final_report else '报告为空'}...

关键发现:
{chr(10).join(f"- {finding}" for finding in result.key_findings[:10])}

研究质量: {result.metadata.get('quality_score', 0):.1f}/10
研究时长: {result.metadata.get('duration', 0):.1f}秒
完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        # 构建元数据
        metadata = {
            "research_id": research_id,
            "question": question,
            "status": result.status,
            "key_findings_count": len(result.key_findings),
            "quality_score": result.metadata.get("quality_score"),
            "duration": result.metadata.get("duration"),
            "created_at": datetime.now().isoformat(),
            "type": "research_result",
            "word_count": len(result.final_report.split()) if result.final_report else 0,
            "finding_count": len(result.key_findings)
        }

        # 使用LLM智能抽取保存
        save_result = await memory_service.add_memory(
            user_id=user_id,
            content=content,
            metadata=metadata,
            infer=True  # 启用智能抽取
        )

        if save_result.get("success"):
            logger.info(f"✅ [MEMORY_SAVE] 研究记忆保存成功: {research_id}")
            return True
        else:
            logger.error(f"❌ [MEMORY_SAVE] 研究记忆保存失败: {save_result.get('error')}")
            return False

    except Exception as e:
        logger.error(f"💥 [MEMORY_SAVE] 保存研究记忆异常: {e}")
        import traceback
        logger.error(f"🔍 [MEMORY_SAVE_ERROR] 异常堆栈:\n{traceback.format_exc()}")
        return False


async def execute_research_task_stream(
    research_id: str,
    question: str,
    user_context: Optional[Dict[str, Any]] = None,
    allow_clarification: bool = False,
    research_depth: str = "comprehensive",
    memory_mode: str = "smart",
    memory_service=None
) -> AsyncGenerator[Dict[str, Any], None]:
    """流式执行研究任务，支持记忆功能"""
    logger.info(f"🚀 [STREAM_START] 开始流式执行研究任务 {research_id}, 记忆模式: {memory_mode}")

    # 处理记忆增强的上下文
    enhanced_context = user_context or {}

    # 如果有用户记忆，添加到上下文中并构建记忆提示
    if memory_service and memory_mode != "none" and enhanced_context.get("user_memories"):
        memories = enhanced_context["user_memories"]
        # 确保 memories 是列表类型
        if isinstance(memories, list) and memories:
            # 将记忆转换为研究提示（build_memory_prompt函数在上面定义）
            memory_prompt = build_memory_prompt(question, memories)
            enhanced_context["memory_prompt"] = memory_prompt
            enhanced_context["has_memories"] = True
            logger.info(f"🧠 [MEMORY] 已添加记忆提示，长度: {len(memory_prompt)} 字符")
        else:
            enhanced_context["has_memories"] = False
            logger.warning(f"🧠 [MEMORY] 记忆数据格式不正确: {type(memories)}")
    
    try:
        # 步骤1: 发送初始化信息
        init_data = {
            'type': 'progress',
            'stage': 'initializing',
            'progress': 5.0,
            'message': '🔧 正在初始化研究系统...',
            'details': '获取编排器实例，配置研究参数'
        }
        logger.info(f"📤 [STREAM_YIELD] {research_id}: 初始化阶段 (5%)")
        yield init_data
        
        # 创建任务记录
        initial_result = ResearchResult(
            question=question,
            status="initializing",
            progress=5.0,
            metadata={
                "research_id": research_id,
                "user_id": "test_user",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "request_clarification": allow_clarification,
                "research_depth": research_depth
            }
        )
        research_tasks[research_id] = initial_result
        
        # 步骤2: 获取编排器
        setup_data = {
            'type': 'progress',
            'stage': 'setup',
            'progress': 10.0,
            'message': '⚙️ 正在配置研究环境...',
            'details': '初始化Open Deep Research编排器'
        }
        logger.info(f"📤 [STREAM_YIELD] {research_id}: 配置阶段 (10%)")
        yield setup_data
        
        logger.info(f"🔧 [STREAM_STEP] {research_id}: 正在获取编排器实例...")
        enh_orchestrator = await get_orchestrator(research_depth)
        logger.info(f"✅ [STREAM_STEP] {research_id}: 编排器获取成功")
        
        analyze_data = {
            'type': 'progress',
            'stage': 'analyzing',
            'progress': 15.0,
            'message': '🔍 正在分析研究问题...',
            'details': f'问题: {question[:50]}...'
        }
        logger.info(f"📤 [STREAM_YIELD] {research_id}: 分析阶段 (15%)")
        yield analyze_data
        
        # 步骤3: 开始研究流程 (进入 LangGraph 流式执行)
        research_data = {
            'type': 'progress',
            'stage': 'researching',
            'progress': 20.0,
            'message': '🚀 开始执行研究流程',
            'details': '进入LangGraph工作流，实时输出执行进度'
        }
        logger.info(f"📤 [STREAM_YIELD] {research_id}: 研究阶段开始 (20%)")
        yield research_data
        
        logger.info(f"⚡ [STREAM_STEP] {research_id}: 开始调用编排器流式处理...")
        start_time = datetime.now()
        
        final_result_obj = None  # 用于保存最终结果对象
        
        # 流式接收 LangGraph 的执行进度
        # 注意：使用enhanced_context，包含memory_prompt
        async for progress_data in enh_orchestrator.process_research_request_stream(
            question=question,
            user_context=enhanced_context,  # 包含memory_prompt和has_memories
            allow_clarification=allow_clarification
        ):
            # 将内部进度（0-100）映射到外部进度（20-95）
            if progress_data.get('type') == 'progress':
                internal_progress = progress_data.get('progress', 0)
                # 映射到 20-95% 区间（留5%给最后的完成信息）
                mapped_progress = 20 + (internal_progress / 100.0) * 75
                progress_data['progress'] = mapped_progress
                
                # 更新任务状态
                if research_id in research_tasks:
                    research_tasks[research_id].progress = mapped_progress
                    research_tasks[research_id].metadata["updated_at"] = datetime.now().isoformat()
                
                # 记录日志（只记录关键信息，详细信息在 DEBUG 模式）
                message = progress_data.get('message', '')
                stage = progress_data.get('stage', '')
                
                # INFO 级别：简洁信息
                logger.info(f"[{research_id[:20]}...] {mapped_progress:5.1f}% | {message}")
                
                # DEBUG 级别：详细信息
                if logger.isEnabledFor(logging.DEBUG):
                    pass  # ✅ 详细日志已注释，功能已验证正常
                    # logger.debug(f"[PROGRESS_DETAIL] Stage: {stage}")
                    # logger.debug(f"[PROGRESS_DETAIL] Data: {progress_data}")
                
                # 转发给前端
                yield progress_data
            
            elif progress_data.get('type') == 'result':
                # 保存最终结果对象，用于后续记忆保存
                result_data = progress_data.get('result')
                if result_data:
                    # 确保result_data是ResearchResult对象
                    if isinstance(result_data, ResearchResult):
                        final_result_obj = result_data
                    else:
                        # 如果是字典，转换为ResearchResult
                        final_result_obj = ResearchResult(
                            question=result_data.get('question', question),
                            final_report=result_data.get('final_report', ''),
                            status=result_data.get('status', 'completed'),
                            key_findings=result_data.get('key_findings', []),
                            raw_notes=result_data.get('raw_notes', []),
                            metadata=result_data.get('metadata', {}),
                            progress=result_data.get('progress', 100.0)
                        )
                # 将最终结果也加入到进度数据中，方便路由层获取
                progress_data['final_result'] = final_result_obj
                logger.info(f"📋 [STREAM_RESULT] {research_id}: 研究完成")
            
            elif progress_data.get('type') == 'error':
                # 错误直接转发
                logger.error(f"💥 [STREAM_ERROR] {research_id}: {progress_data.get('message', '')}")
                yield progress_data
                return  # 错误时直接返回
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"✅ [STREAM_STEP] {research_id}: 编排器执行完成，耗时 {duration:.1f}秒")
        
        # 如果没有获取到最终结果，创建一个错误结果
        if not final_result_obj:
            logger.warning(f"⚠️ [STREAM_WARN] {research_id}: 未获取到最终结果")
            yield {
                'type': 'error',
                'stage': 'failed',
                'message': '❌ 研究未完成：未获取到最终结果',
                'error': 'No final result received'
            }
            return
        
        # 使用已保存的最终结果对象
        result = final_result_obj
        
        # 步骤4: 发送完成信息
        complete_data = {
            'type': 'progress',
            'stage': 'completed',
            'progress': 95.0,
            'message': '📝 正在生成最终报告...',
            'details': f'研究耗时: {duration:.1f}秒'
        }
        logger.info(f"📤 [STREAM_YIELD] {research_id}: 报告生成阶段 (95%)")
        yield complete_data
        
        # 保存最终结果
        result.metadata["updated_at"] = datetime.now().isoformat()
        result.metadata["execution_duration"] = duration
        research_tasks[research_id] = result
        
        # 计算质量分数
        quality_score = min(100.0, (len(result.key_findings) * 5 + len(result.final_report or "") / 100))
        logger.info(f"📊 [STREAM_STATS] {research_id}: 质量评分 {quality_score:.1f}分，关键发现 {len(result.key_findings)}个")
        
        # 发送最终结果
        result_data = {
            'type': 'result',
            'stage': 'completed',
            'progress': 100.0,
            'message': '✅ 研究任务完成！',
            'details': f'质量评分: {quality_score:.1f}分，关键发现: {len(result.key_findings)}个',
            'research_id': research_id,
            'question': question,
            'status': result.status,
            'final_report': result.final_report or "研究未完成",
            'key_findings': result.key_findings,
            'metadata': result.metadata,
            'quality_score': quality_score,
            'duration': duration,
            'created_at': result.metadata.get("created_at", datetime.now().isoformat()),
            'result': result,  # 添加ResearchResult对象
            'final_result': result  # 同时添加final_result字段，方便路由层获取
        }
        logger.info(f"📤 [STREAM_YIELD] {research_id}: 最终结果 (100%)")
        logger.info(f"📄 [STREAM_REPORT] {research_id}: 报告长度 {len(result.final_report or '')} 字符")
        yield result_data
        
        logger.info(f"🎉 [STREAM_COMPLETE] 流式研究任务 {research_id} 成功完成！")
        
    except Exception as e:
        logger.error(f"💥 [STREAM_FAILED] 流式研究任务 {research_id} 失败: {e}")
        import traceback
        logger.error(f"🔍 [ERROR_DETAILS] 异常堆栈:\n{traceback.format_exc()}")
        
        # 发送错误信息
        error_data = {
            'type': 'error',
            'stage': 'failed',
            'progress': 0.0,
            'message': f'❌ 研究任务失败: {str(e)}',
            'details': '请检查网络连接和参数配置',
            'research_id': research_id,
            'error': str(e)
        }
        logger.error(f"📤 [STREAM_ERROR] {research_id}: 发送错误响应")
        yield error_data


def create_research_task(research_id: str, question: str, **kwargs) -> ResearchResult:
    """创建研究任务"""
    initial_result = ResearchResult(
        question=question,
        status="initializing",
        progress=0.0,  # 初始进度为0
        metadata={
            "research_id": research_id,
            "user_id": "test_user",  # 暂时使用固定用户ID
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            **kwargs
        }
    )
    research_tasks[research_id] = initial_result
    logger.info(f"📝 [TASK_CREATED] 创建研究任务 {research_id}: {question}")
    return initial_result
