"""
Open Deep Research 编排器
基于官方文档的完整编排器实现
"""
import asyncio
import logging
import os
from typing import Dict, Any, List, Optional, Callable, AsyncGenerator
from datetime import datetime
from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage

from .odr_main import deep_researcher
from .odr_configuration import Configuration

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


@dataclass
class ResearchResult:
    """研究结果数据类 - 向后兼容的简化版本"""
    question: str
    final_report: Optional[str] = None
    status: str = "initializing"
    key_findings: List[str] = field(default_factory=list)
    raw_notes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    progress: float = 0.0


class ODRResearchOrchestrator:
    """Open Deep Research 编排器 - 基于官方架构"""

    def __init__(self, config: Optional[Configuration] = None):
        self.config = config or Configuration(
            allow_clarification=True,
            search_api="serper"
        )

        # 使用已编译的图
        self.graph = deep_researcher
        self.initialized = False

    async def initialize(self):
        """初始化编排器"""
        try:
            self.initialized = True
            logger.info("Open Deep Research 编排器初始化完成")
        except Exception as e:
            logger.error(f"编排器初始化失败: {e}")
            raise

    async def cleanup(self):
        """清理资源"""
        try:
            self.initialized = False
            logger.info("Open Deep Research 编排器资源清理完成")
        except Exception as e:
            logger.error(f"资源清理失败: {e}")

    async def process_research_request(
        self,
        question: str,
        user_context: Optional[Dict[str, Any]] = None,
        allow_clarification: bool = True,
        progress_callback: Optional[Callable] = None
    ) -> ResearchResult:
        """
        处理研究请求的主要入口

        Args:
            question: 研究问题
            user_context: 用户上下文
            allow_clarification: 是否允许澄清
            progress_callback: 进度回调函数

        Returns:
            ResearchResult: 研究结果
        """
        logger.info("=== 开始处理研究请求 ===")
        
        if not self.initialized:
            logger.info("编排器未初始化，正在初始化...")
            await self.initialize()

        start_time = datetime.now()

        try:
            logger.info(f"研究问题: {question}")
            logger.info(f"允许澄清: {allow_clarification}")

            # 更新配置
            if allow_clarification != self.config.allow_clarification:
                logger.info(f"更新澄清配置: {allow_clarification}")
                self.config.allow_clarification = allow_clarification

            # 创建配置
            config = {
                "configurable": {
                    "thread_id": f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(question) % 10000}",
                    **self.config.model_dump()
                }
            }
            logger.info(f"运行配置: {config}")

            # 更新进度
            if progress_callback:
                logger.info("调用进度回调: 5%")
                progress_callback(5.0)  # 初始化完成

            # 执行研究
            initial_state = {
                "messages": [HumanMessage(content=question)]
            }
            logger.info(f"初始状态: {initial_state}")

            # 执行研究任务
            logger.info("🚀 开始执行研究任务...")
            final_state = await self.graph.ainvoke(initial_state, config)
            logger.info(f"✅ 研究任务执行完成，最终状态: {final_state}")

            # 更新进度
            if progress_callback:
                logger.info("调用进度回调: 100%")
                progress_callback(100.0)  # 完成

            # 转换为简化的ResearchResult格式
            logger.info("转换研究结果...")
            result = self._convert_to_research_result(final_state, start_time)

            logger.info(f"研究请求处理完成，耗时: {result.metadata.get('duration', 0):.2f}秒")
            logger.info("=== 研究请求处理完成 ===")
            return result

        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"研究请求处理失败: {e}")
            logger.error(f"完整错误信息: {error_traceback}")
            return ResearchResult(
                question=question,
                status="failed",
                metadata={
                    "error": str(e),
                    "traceback": error_traceback,
                    "duration": (datetime.now() - start_time).total_seconds()
                }
            )

    async def process_research_request_stream(
        self,
        question: str,
        user_context: Optional[Dict[str, Any]] = None,
        allow_clarification: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式处理研究请求，实时输出每个关键步骤的进度
        
        Args:
            question: 研究问题
            user_context: 用户上下文
            allow_clarification: 是否允许澄清
            
        Yields:
            进度数据字典:
            {
                'type': 'progress',      # 进度更新
                'stage': '当前阶段',
                'progress': 进度百分比,   # 0-100
                'message': '用户可读消息',
                'details': '详细信息',
                'metadata': {
                    'node_name': '节点名称',
                    'event_type': '事件类型'
                }
            }
            或:
            {
                'type': 'result',        # 最终结果
                'final_report': '...',
                'key_findings': [...],
                ...
            }
        """
        logger.info("=== 开始流式处理研究请求 ===")
        
        if not self.initialized:
            logger.info("编排器未初始化，正在初始化...")
            await self.initialize()
        
        start_time = datetime.now()
        
        try:
            logger.info(f"研究问题: {question}")
            logger.info(f"允许澄清: {allow_clarification}")
            
            # 更新配置
            if allow_clarification != self.config.allow_clarification:
                logger.info(f"更新澄清配置: {allow_clarification}")
                self.config.allow_clarification = allow_clarification
            
            # 创建配置
            config = {
                "configurable": {
                    "thread_id": f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(question) % 10000}",
                    **self.config.model_dump()
                }
            }
            
            # 创建初始状态
            initial_state = {
                "messages": [HumanMessage(content=question)]
            }
            
            # 进度追踪器
            progress_tracker = {
                'current_node': None,
                'supervisor_round': 0,
                'researcher_count': 0,
                'base_progress': 0.0,
                'last_progress': 0.0,
                # 消息过滤器
                'last_ai_message_time': 0,
                'ai_message_cooldown': 2.0,  # AI消息冷却时间（秒）
                'search_count': 0,
                'last_message_type': None,
                'start_time': datetime.now().timestamp()
            }
            
            # 保存最终状态
            final_state = None
            
            # ⭐ 核心：使用 astream_events 流式执行
            logger.info("🚀 开始流式执行研究任务...")
            async for event in self.graph.astream_events(
                initial_state, 
                config, 
                version="v2"
            ):
                # 解析事件并生成进度数据
                progress_data = self._parse_event_to_progress(
                    event, 
                    progress_tracker
                )
                
                if progress_data:
                    yield progress_data
                
                # 保存最终状态（从 on_chain_end 的 LangGraph 主节点获取）
                if (event.get("event") == "on_chain_end" and 
                    event.get("name") == "LangGraph" and 
                    "output" in event.get("data", {})):
                    final_state = event["data"]["output"]
            
            # 转换为ResearchResult
            if final_state:
                result = self._convert_to_research_result(final_state, start_time)
                
                # 发送最终结果
                yield {
                    'type': 'result',
                    'stage': 'completed',
                    'progress': 100.0,
                    'message': '✅ 研究任务完成！',
                    'research_id': config["configurable"]["thread_id"],
                    'question': question,
                    'status': result.status,
                    'final_report': result.final_report or "研究未完成",
                    'key_findings': result.key_findings,
                    'metadata': result.metadata,
                    'duration': result.metadata.get('duration', 0)
                }
                
                logger.info(f"流式研究完成，耗时: {result.metadata.get('duration', 0):.2f}秒")
            else:
                logger.warning("未获取到最终状态")
                yield {
                    'type': 'error',
                    'message': '未能获取研究结果',
                    'error': 'No final state'
                }
            
            logger.info("=== 流式研究请求处理完成 ===")
            
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"流式研究失败: {e}")
            logger.error(f"完整错误信息: {error_traceback}")
            
            yield {
                'type': 'error',
                'stage': 'failed',
                'message': f'❌ 研究失败: {str(e)}',
                'error': str(e),
                'traceback': error_traceback
            }

    def _get_stats_summary(self, tracker: Dict[str, Any]) -> str:
        """生成统计摘要"""
        current_time = datetime.now().timestamp()
        elapsed_time = int(current_time - tracker.get('start_time', current_time))
        search_count = tracker.get('search_count', 0)
        researcher_count = tracker.get('researcher_count', 0)
        supervisor_round = tracker.get('supervisor_round', 0)
        
        parts = []
        parts.append(f"已运行 {elapsed_time}秒")
        if supervisor_round > 0:
            parts.append(f"第{supervisor_round}轮规划")
        if researcher_count > 0:
            parts.append(f"{researcher_count}个研究单元")
        if search_count > 0:
            parts.append(f"{search_count}次搜索")
        
        return " | ".join(parts)
    
    def _parse_event_to_progress(
        self, 
        event: Dict[str, Any], 
        tracker: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        将 LangGraph 事件解析为进度数据
        
        Args:
            event: LangGraph 事件
            tracker: 进度追踪器，用于记录状态
            
        Returns:
            进度数据字典，如果不需要输出则返回 None
        """
        event_type = event.get("event")
        event_name = event.get("name", "")
        
        # DEBUG 级别：输出完整事件数据
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"[EVENT] {event_type} | {event_name}")
            # logger.debug(f"[EVENT_DATA] {event}")  # ✅ 已验证功能正常，注释掉以减少日志冗余
        
        # ═══════════════════════════════════════════
        # 节点开始事件
        # ═══════════════════════════════════════════
        if event_type == "on_chain_start":
            tracker['current_node'] = event_name
            
            # 主工作流节点
            if event_name == "clarify_with_user":
                tracker['base_progress'] = 0.0
                return {
                    'type': 'progress',
                    'stage': 'clarifying',
                    'progress': 0.0,
                    'message': '🤔 检查问题是否需要澄清',
                    'details': '分析问题清晰度，决定是否需要用户补充信息',
                    'metadata': {'node': 'clarify_with_user', 'event': 'start'}
                }
            
            elif event_name == "write_research_brief":
                tracker['base_progress'] = 5.0
                return {
                    'type': 'progress',
                    'stage': 'planning',
                    'progress': 5.0,
                    'message': '📝 规划研究策略',
                    'details': '将问题转换为结构化的研究简报',
                    'metadata': {'node': 'write_research_brief', 'event': 'start'}
                }
            
            elif event_name == "research_supervisor":
                tracker['base_progress'] = 15.0
                stats = self._get_stats_summary(tracker)
                return {
                    'type': 'progress',
                    'stage': 'supervising',
                    'progress': 15.0,
                    'message': '🎯 监督者：开始研究编排',
                    'details': f'分析任务，制定研究策略\n{stats}',
                    'metadata': {'node': 'research_supervisor', 'event': 'start'}
                }
            
            # 监督者子图节点
            elif event_name == "supervisor":
                tracker['supervisor_round'] += 1
                round_num = tracker['supervisor_round']
                # 监督者每轮占用一定进度（15%-75%区间，共60%）
                progress = min(15.0 + (round_num - 1) * 10.0, 70.0)
                tracker['base_progress'] = progress
                
                stats = self._get_stats_summary(tracker)
                
                logger.info(f"[SUPERVISOR] 🎯 第{round_num}轮规划开始 | {stats}")
                
                return {
                    'type': 'progress',
                    'stage': 'supervising',
                    'progress': progress,
                    'message': f'🎯 监督者：第{round_num}轮规划',
                    'details': f'分析当前进展，决定下一步行动\n{stats}',
                    'metadata': {
                        'node': 'supervisor',
                        'event': 'start',
                        'round': round_num
                    }
                }
            
            elif event_name == "supervisor_tools":
                progress = tracker['base_progress'] + 2.0
                return {
                    'type': 'progress',
                    'stage': 'executing',
                    'progress': min(progress, 75.0),
                    'message': '⚙️ 执行监督者指令',
                    'details': '处理工具调用，执行研究任务',
                    'metadata': {'node': 'supervisor_tools', 'event': 'start'}
                }
            
            # 研究者节点（不重复计数，已在ConductResearch中计数）
            elif event_name == "researcher":
                count = tracker.get('researcher_count', 0)
                # 研究者在30%-60%区间
                progress = 30.0 + min(count * 5.0, 30.0)
                
                # 计算已用时间
                current_time = datetime.now().timestamp()
                elapsed_time = int(current_time - tracker.get('start_time', current_time))
                
                # 不发送重复的研究者启动消息（已在ConductResearch中发送）
                # 只在researcher节点真正执行时发送一次汇总消息
                return None
            
            elif event_name == "final_report_generation":
                tracker['base_progress'] = 75.0
                stats = self._get_stats_summary(tracker)
                return {
                    'type': 'progress',
                    'stage': 'generating_report',
                    'progress': 75.0,
                    'message': '✍️ 生成最终报告',
                    'details': f'整合所有研究发现，撰写综合报告\n{stats}',
                    'metadata': {'node': 'final_report_generation', 'event': 'start'}
                }
        
        # ═══════════════════════════════════════════
        # 节点完成事件
        # ═══════════════════════════════════════════
        elif event_type == "on_chain_end":
            # 监督者完成：显示决策的工具调用
            if event_name == "supervisor":
                output = event.get("data", {}).get("output")
                
                # 安全提取数据（处理 Command 对象）
                supervisor_messages = []
                if output:
                    # 处理 Command 对象
                    if hasattr(output, 'update') and isinstance(output.update, dict):
                        supervisor_messages = output.update.get("supervisor_messages", [])
                    # 处理普通字典
                    elif isinstance(output, dict):
                        supervisor_messages = output.get("supervisor_messages", [])
                
                # 分析工具调用
                tool_calls_info = []
                if supervisor_messages:
                    # supervisor_messages 可能是单个消息或消息列表
                    msgs = supervisor_messages if isinstance(supervisor_messages, list) else [supervisor_messages]
                    # 获取最后一条消息（AI的响应）
                    for msg in msgs:
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            for tc in msg.tool_calls:
                                tool_name = tc.get("name", "unknown") if isinstance(tc, dict) else getattr(tc, 'name', 'unknown')
                                tool_args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, 'args', {})
                                tool_calls_info.append({
                                    'tool': tool_name,
                                    'args': tool_args
                                })
                
                # 日志：监督者的决策
                if tool_calls_info:
                    logger.info(f"[SUPERVISOR] ✅ 决策完成，计划调用 {len(tool_calls_info)} 个工具:")
                    for i, tc_info in enumerate(tool_calls_info, 1):
                        tool_display = tc_info['tool']
                        logger.info(f"  {i}. {tool_display}")
                        
                        # DEBUG 模式显示完整参数
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f"     参数: {tc_info['args']}")
                        # INFO 模式显示参数摘要
                        else:
                            if tc_info['tool'] == 'ConductResearch':
                                topic = str(tc_info['args'].get('research_topic', ''))[:80]
                                logger.info(f"     主题: {topic}...")
                            elif tc_info['tool'] == 'think_tool':
                                reflection = str(tc_info['args'].get('reflection', ''))[:80]
                                logger.info(f"     反思: {reflection}...")
                else:
                    logger.info(f"[SUPERVISOR] ✅ 决策完成，没有工具调用（可能已结束）")
                
                return None  # 不单独发送进度，避免过多输出
            
            elif event_name == "clarify_with_user":
                return {
                    'type': 'progress',
                    'stage': 'clarifying',
                    'progress': 5.0,
                    'message': '✅ 问题澄清完成',
                    'details': '问题清晰，继续研究',
                    'metadata': {'node': 'clarify_with_user', 'event': 'end'}
                }
            
            elif event_name == "write_research_brief":
                # 提取研究简报内容
                output = event.get("data", {}).get("output")
                
                # 检查 output 类型（可能是 Command 对象或字典）
                research_brief = ""
                if output and isinstance(output, dict):
                    research_brief = output.get("research_brief", "")
                elif output and hasattr(output, 'update'):
                    # Command 对象有 update 属性
                    update_data = output.update if isinstance(output.update, dict) else {}
                    research_brief = update_data.get("research_brief", "")
                
                # DEBUG 日志：打印完整的研究简报
                if research_brief:
                    logger.info(f"[RESEARCH_BRIEF] 研究简报已生成，长度: {len(research_brief)} 字符")
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("=" * 60)
                        logger.debug("[研究简报完整内容]")
                        logger.debug("=" * 60)
                        logger.debug(research_brief)
                        logger.debug("=" * 60)
                    
                    # 生成简报摘要（前300字符）
                    brief_preview = research_brief[:300] + "..." if len(research_brief) > 300 else research_brief
                    
                    return {
                        'type': 'progress',
                        'stage': 'planning',
                        'progress': 15.0,
                        'message': '✅ 研究策略规划完成',
                        'details': f'已生成结构化研究简报\n\n简报预览:\n{brief_preview}',
                        'research_brief': research_brief,
                        'metadata': {
                            'node': 'write_research_brief', 
                            'event': 'end',
                            'brief_length': len(research_brief)
                        }
                    }
                else:
                    # 如果没有提取到简报，返回基本进度
                    return {
                        'type': 'progress',
                        'stage': 'planning',
                        'progress': 15.0,
                        'message': '✅ 研究策略规划完成',
                        'details': '已生成结构化研究简报',
                        'metadata': {'node': 'write_research_brief', 'event': 'end'}
                    }
            
            elif event_name == "research_supervisor":
                # 提取研究结果
                output = event.get("data", {}).get("output")
                
                # 安全提取数据（可能是 dict 或 Command 对象）
                notes = []
                if output and isinstance(output, dict):
                    notes = output.get("notes", [])
                
                if notes:
                    # DEBUG 日志：打印研究发现
                    logger.info(f"[RESEARCH_COMPLETE] 研究执行完成，收集到 {len(notes)} 条关键发现")
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("=" * 60)
                        logger.debug("[研究发现列表]")
                        logger.debug("=" * 60)
                        for i, note in enumerate(notes[:10], 1):  # 最多显示前10条
                            logger.debug(f"{i}. {note}")
                        if len(notes) > 10:
                            logger.debug(f"... 还有 {len(notes) - 10} 条发现")
                        logger.debug("=" * 60)
                    
                    # 生成发现摘要
                    findings_preview = "\n".join([f"{i}. {note[:100]}..." for i, note in enumerate(notes[:3], 1)])
                    stats = self._get_stats_summary(tracker)
                    
                    return {
                        'type': 'progress',
                        'stage': 'supervising',
                        'progress': 75.0,
                        'message': '✅ 研究执行完成',
                        'details': f'收集到 {len(notes)} 条关键发现\n{stats}\n\n关键发现预览:\n{findings_preview}',
                        'findings_count': len(notes),
                        'metadata': {
                            'node': 'research_supervisor', 
                            'event': 'end',
                            'notes_count': len(notes),
                            'total_searches': tracker.get('search_count', 0),
                            'total_researchers': tracker.get('researcher_count', 0)
                        }
                    }
                else:
                    # 没有提取到发现，返回基本进度
                    stats = self._get_stats_summary(tracker)
                    logger.info(f"[RESEARCH_COMPLETE] 研究执行完成 | {stats}")
                    return {
                        'type': 'progress',
                        'stage': 'supervising',
                        'progress': 75.0,
                        'message': '✅ 研究执行完成',
                        'details': f'所有研究任务已完成\n{stats}',
                        'metadata': {
                            'node': 'research_supervisor', 
                            'event': 'end',
                            'total_searches': tracker.get('search_count', 0),
                            'total_researchers': tracker.get('researcher_count', 0)
                        }
                    }
            
            elif event_name == "final_report_generation":
                stats = self._get_stats_summary(tracker)
                return {
                    'type': 'progress',
                    'stage': 'generating_report',
                    'progress': 95.0,
                    'message': '✅ 报告生成完成',
                    'details': f'最终研究报告已生成\n{stats}',
                    'metadata': {
                        'node': 'final_report_generation', 
                        'event': 'end',
                        'total_searches': tracker.get('search_count', 0),
                        'total_researchers': tracker.get('researcher_count', 0),
                        'total_rounds': tracker.get('supervisor_round', 0)
                    }
                }
        
        # ═══════════════════════════════════════════
        # AI模型调用事件（带冷却过滤）
        # ═══════════════════════════════════════════
        elif event_type == "on_chat_model_start":
            current_node = tracker.get('current_node', 'unknown')
            current_time = datetime.now().timestamp()
            last_ai_time = tracker.get('last_ai_message_time', 0)
            cooldown = tracker.get('ai_message_cooldown', 2.0)
            
            # 冷却时间内，跳过重复的AI消息
            if current_time - last_ai_time < cooldown:
                return None
            
            # 更新最后发送时间
            tracker['last_ai_message_time'] = current_time
            
            # 计算已用时间
            elapsed_time = int(current_time - tracker.get('start_time', current_time))
            progress = tracker.get('base_progress', 0) + 1.0
            
            # 生成简化的AI处理消息
            node_display = {
                'researcher': '研究单元分析',
                'supervisor': '监督者决策',
                'supervisor_planner': '制定研究计划',
                'final_report_generation': '生成报告',
                'clarify_with_user': '问题分析'
            }.get(current_node, '处理中')
            
            return {
                'type': 'progress',
                'stage': 'ai_processing',
                'progress': min(progress, 95.0),
                'message': f'🤖 AI分析：{node_display}',
                'details': f'已运行 {elapsed_time}秒 | 搜索 {tracker.get("search_count", 0)}次',
                'metadata': {
                    'model': event_name,
                    'node': current_node,
                    'event': 'ai_start',
                    'elapsed_seconds': elapsed_time,
                    'search_count': tracker.get('search_count', 0)
                }
            }
        
        # ═══════════════════════════════════════════
        # 工具调用事件
        # ═══════════════════════════════════════════
        elif event_type == "on_tool_start":
            tool_name = event_name
            tool_input = event.get("data", {}).get("input", {})
            progress = tracker.get('base_progress', 0) + 1.0
            
            # DEBUG 日志：详细的工具信息
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"[TOOL_START] Tool: {tool_name}")
                logger.debug(f"[TOOL_INPUT] {tool_input}")
            
            # 搜索工具
            if "search" in tool_name.lower():
                # 增加搜索计数
                tracker['search_count'] = tracker.get('search_count', 0) + 1
                search_num = tracker['search_count']
                
                query = tool_input.get("query", str(tool_input)[:100]) if isinstance(tool_input, dict) else str(tool_input)[:100]
                
                # 计算已用时间
                current_time = datetime.now().timestamp()
                elapsed_time = int(current_time - tracker.get('start_time', current_time))
                
                logger.info(f"[TOOL] 🔍 搜索 #{search_num}: {query}")
                
                return {
                    'type': 'progress',
                    'stage': 'searching',
                    'progress': min(progress, 90.0),
                    'message': f'🔍 搜索 #{search_num}',
                    'details': f'查询: {query}\n已运行 {elapsed_time}秒',
                    'current_tool': tool_name,
                    'tool_input': query,
                    'metadata': {
                        'tool': tool_name,
                        'event': 'tool_start',
                        'search_number': search_num,
                        'elapsed_seconds': elapsed_time,
                        'total_searches': search_num,
                        'input': tool_input
                    }
                }
            
            # 研究委托工具
            elif tool_name == "ConductResearch":
                tracker['researcher_count'] = tracker.get('researcher_count', 0) + 1
                unit_num = tracker['researcher_count']
                
                topic = str(tool_input.get("research_topic", ""))[:100] if isinstance(tool_input, dict) else str(tool_input)[:100]
                
                # 计算已用时间
                current_time = datetime.now().timestamp()
                elapsed_time = int(current_time - tracker.get('start_time', current_time))
                
                logger.info(f"[TOOL] 🚀 启动研究单元 #{unit_num}: {topic}")
                
                return {
                    'type': 'progress',
                    'stage': 'delegating',
                    'progress': min(progress, 90.0),
                    'message': f'🚀 启动研究单元 #{unit_num}',
                    'details': f'研究主题: {topic}\n已运行 {elapsed_time}秒 | 已搜索 {tracker.get("search_count", 0)}次',
                    'current_tool': 'ConductResearch',
                    'tool_input': topic,
                    'metadata': {
                        'tool': 'ConductResearch',
                        'event': 'tool_start',
                        'unit_number': unit_num,
                        'elapsed_seconds': elapsed_time,
                        'total_searches': tracker.get('search_count', 0),
                        'topic': topic
                    }
                }
            
            # 其他工具（通用处理）
            else:
                input_str = str(tool_input)[:100]
                
                logger.info(f"[TOOL] 🔧 工具调用: {tool_name} | 输入: {input_str}")
                
                return {
                    'type': 'progress',
                    'stage': 'tool_calling',
                    'progress': min(progress, 90.0),
                    'message': f'🔧 调用工具: {tool_name}',
                    'details': f'输入: {input_str}',
                    'current_tool': tool_name,  # 👈 新增
                    'tool_input': input_str,    # 👈 新增
                    'metadata': {
                        'tool': tool_name,
                        'event': 'tool_start',
                        'input': tool_input
                    }
                }
        
        # 工具完成事件
        elif event_type == "on_tool_end":
            tool_name = event_name
            tool_output = event.get("data", {}).get("output", "")
            
            # DEBUG 日志：工具输出
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"[TOOL_END] Tool: {tool_name}")
                logger.debug(f"[TOOL_OUTPUT] {str(tool_output)[:500]}")
            
            logger.info(f"[TOOL] ✅ 工具完成: {tool_name} | 输出长度: {len(str(tool_output))}")
        
        # 其他事件不处理，避免过多输出
        return None

    def _convert_to_research_result(
        self,
        final_state: Dict[str, Any],
        start_time: datetime
    ) -> ResearchResult:
        """将最终状态转换为ResearchResult"""
        duration = (datetime.now() - start_time).total_seconds()

        # 提取关键发现
        key_findings = []
        notes = final_state.get("notes", [])
        for note in notes:
            if len(note) > 10:
                key_findings.append(note)

        # 提取原始笔记
        raw_notes = final_state.get("raw_notes", [])

        # 状态映射
        status = "completed" if final_state.get("final_report") else "failed"

        # 安全获取问题内容
        messages = final_state.get("messages", [])
        question = ""
        if messages and len(messages) > 0:
            first_message = messages[0]
            if hasattr(first_message, 'content'):
                question = first_message.content
            elif isinstance(first_message, dict):
                question = first_message.get("content", "")

        return ResearchResult(
            question=question,
            final_report=final_state.get("final_report", ""),
            status=status,
            key_findings=key_findings[:20],  # 限制数量
            raw_notes=raw_notes[:50],  # 限制数量
            metadata={
                "duration": duration,
                "research_brief": final_state.get("research_brief", ""),
                "created_at": start_time.isoformat(),
                "completed_at": datetime.now().isoformat()
            }
        )

    async def get_research_status(self, research_id: str) -> Dict[str, Any]:
        """获取研究状态（扩展功能）"""
        # 这里可以实现状态持久化和查询
        return {
            "research_id": research_id,
            "status": "not_implemented",
            "message": "状态持久化功能待实现"
        }

    async def cancel_research(self, research_id: str) -> bool:
        """取消研究（扩展功能）"""
        # 这里可以实现研究取消功能
        logger.info(f"取消研究请求: {research_id}")
        return True

    def update_config(self, **kwargs):
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"配置更新: {key} = {value}")
