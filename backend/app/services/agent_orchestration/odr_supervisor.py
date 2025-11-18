"""
Open Deep Research 监督者子图 - 简化架构
合并supervisor和decision_executor为单一supervisor_planner节点，消除嵌套子图
"""
import asyncio
import logging
import re
from typing import Literal, TypedDict
from pydantic import BaseModel, Field
from typing import List

logger = logging.getLogger(__name__)


class ResearchTopicsResponse(BaseModel):
    """研究主题生成响应模型"""
    analysis: str = Field(description="对研究简报的分析，识别的关键维度")
    research_topics: List[str] = Field(description="生成的研究主题列表")
    reasoning: str = Field(description="为什么选择这些主题，它们如何互补")

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    get_buffer_string,
)
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from .qwen_model import init_qwen_model
from .odr_configuration import Configuration
from .odr_prompts import lead_researcher_prompt, generate_research_topics_prompt
from .odr_state import SupervisorState
from .odr_utils import (
    get_api_key_for_model,
    get_notes_from_tool_calls,
    is_token_limit_exceeded,
)

# LangSmith 集成
try:
    from ..utils.langsmith_integration import (
        trace_node,
        log_node_execution,
        get_langsmith_config,
        is_langsmith_enabled
    )
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    # 提供空实现
    def trace_node(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

    def log_node_execution(*args, **kwargs):
        pass

    def get_langsmith_config(*args, **kwargs):
        return {}

    def is_langsmith_enabled():
        return False


# ═══════════════════════════════════════════════════════════════
# 控制器类 - 防止无限研究
# ═══════════════════════════════════════════════════════════════

class ResearchQualityController:
    """研究质量控制器 - 防止低效重复研究"""

    def __init__(self):
        self.quality_history = []
        self.recent_improvements = []

    def should_continue_research(self, current_findings, previous_findings, iteration):
        """严格的继续研究判断"""

        # 1. 信息增益评估
        information_gain = self.calculate_information_gain(current_findings, previous_findings)
        if information_gain < 0.05:  # 新信息少于5%
            return False, "信息增益过低"

        # 2. 质量改善趋势
        quality_trend = self.analyze_quality_trend(self.quality_history)
        if quality_trend < 0 and iteration > 2:  # 质量连续下降
            return False, "研究质量呈下降趋势"

        # 3. 饱和度检测
        saturation_score = self.calculate_saturation_score(current_findings)
        if saturation_score > 0.8:  # 研究饱和度过高
            return False, "研究领域已基本饱和"

        # 4. 效率评估
        efficiency = self.calculate_research_efficiency(current_findings, iteration)
        if efficiency < 0.3 and iteration > 1:  # 效率太低
            return False, "研究效率过低"

        return True, "继续研究有价值"

    def calculate_information_gain(self, current_findings, previous_findings):
        """计算信息增益"""
        if not previous_findings:
            return 1.0

        # 简化的新信息比例计算
        current_text = " ".join(current_findings).lower()
        previous_text = " ".join(previous_findings).lower()

        # 计算重复内容的比例
        common_words = set(current_text.split()) & set(previous_text.split())
        total_words = set(current_text.split())

        if not total_words:
            return 1.0

        overlap_ratio = len(common_words) / len(total_words)
        return 1.0 - overlap_ratio  # 新信息越多，增益越大

    def analyze_quality_trend(self, quality_history):
        """分析质量趋势"""
        if len(quality_history) < 2:
            return 1.0

        # 计算最近的趋势
        recent_scores = quality_history[-3:]  # 最近3次
        if len(recent_scores) < 2:
            return 1.0

        # 简单的线性趋势
        return (recent_scores[-1] - recent_scores[0]) / len(recent_scores)

    def calculate_saturation_score(self, findings):
        """计算研究饱和度"""
        if not findings:
            return 0.0

        # 基于发现数量和内容重复度的饱和度评估
        total_words = sum(len(f.split()) for f in findings)
        unique_words = len(set(" ".join(findings).lower().split()))

        if total_words == 0:
            return 0.0

        # 重复度越高，饱和度越高
        return 1.0 - (unique_words / total_words)

    def calculate_research_efficiency(self, findings, iteration):
        """计算研究效率"""
        if not findings or iteration == 0:
            return 1.0

        # 基于平均发现长度和质量
        avg_length = sum(len(f) for f in findings) / len(findings)

        # 效率评分（简单的启发式方法）
        if avg_length > 200:  # 详细的发现
            return 0.8
        elif avg_length > 100:
            return 0.6
        else:
            return 0.4


class ProgressiveCompletionStrategy:
    """渐进式完成策略 - 动态调整完成标准"""

    def get_completion_threshold(self, iteration, max_iterations):
        """渐进式完成阈值"""

        # 早期阶段：高质量要求
        if iteration <= max_iterations * 0.3:
            return 0.85  # 需要85%的完成度

        # 中期阶段：中等质量要求
        elif iteration <= max_iterations * 0.7:
            return 0.70  # 需要70%的完成度

        # 后期阶段：较低质量要求（避免无限研究）
        else:
            return max(0.50, 0.85 - (iteration / max_iterations) * 0.35)

    def should_force_complete(self, state, config):
        """强制完成判断"""

        iteration = state.get("research_iterations", 0)
        # 处理config可能是字典的情况
        if isinstance(config, dict):
            max_iterations = config.get("max_researcher_iterations", 5)
        else:
            max_iterations = config.max_researcher_iterations

        # 1. 接近限制时强制考虑完成
        if iteration >= max_iterations - 1:
            return True, "接近迭代限制"

        # 2. 连续三轮无显著改善（简化实现）
        recent_notes_count = len(state.get("notes", []))
        if iteration > 3 and recent_notes_count < iteration * 2:  # 平均每轮少于2个发现
            return True, "研究发现增长缓慢"

        # 3. 资源效率过低
        used_units = state.get("used_research_units", 0)
        if used_units > 0 and recent_notes_count / used_units < 0.5:  # 每个研究单元平均少于0.5个发现
            return True, "资源使用效率过低"

        return False, ""


class SmartExitController:
    """智能退出控制器 - 多维度评估退出时机"""

    def should_force_complete(self, state, config):
        """强制完成判断"""

        iteration = state.get("research_iterations", 0)
        # 处理config可能是字典的情况
        if isinstance(config, dict):
            max_iterations = config.get("max_researcher_iterations", 5)
        else:
            max_iterations = config.max_researcher_iterations

        # 1. 接近限制时强制考虑完成
        if iteration >= max_iterations - 1:
            return True, "接近迭代限制"

        # 2. 研究发现增长缓慢
        notes = state.get("notes", [])
        if iteration > 2 and len(notes) < iteration:
            return True, "研究发现增长缓慢"

        return False, ""

    def evaluate_exit_conditions(self, state, config):
        """多维度退出条件评估"""

        notes = state.get("notes", [])
        research_brief = state.get("research_brief", "")

        # 1. 检查发现充分性
        findings_sufficiency = self.check_findings_sufficiency(notes, research_brief)

        # 2. 检查信息密度
        information_density = self.check_information_density(notes)

        # 3. 计算总体评分
        conditions = {
            "findings_sufficiency": findings_sufficiency,
            "information_density": information_density
        }

        exit_strength = sum(conditions.values()) / len(conditions)

        # 退出建议
        if exit_strength > 0.7:
            return "strong_complete", f"强烈建议完成: 发现充分({findings_sufficiency:.2f}), 信息密度({information_density:.2f})"
        elif exit_strength > 0.4:
            return "consider_complete", f"考虑完成: 发现充分({findings_sufficiency:.2f}), 信息密度({information_density:.2f})"
        else:
            return "continue", "建议继续研究"

    def check_findings_sufficiency(self, notes, research_brief):
        """检查发现充分性"""
        if not notes:
            return 0.0

        # 基于发现数量和质量的简单评估
        findings_count = len(notes)
        avg_length = sum(len(note) for note in notes) / findings_count if findings_count > 0 else 0

        # 数量评分 (0-0.5)
        count_score = min(0.5, findings_count / 10)  # 10个发现得满分

        # 质量评分 (0-0.5)
        quality_score = min(0.5, avg_length / 400)  # 400字符得满分

        return count_score + quality_score

    def check_information_density(self, notes):
        """检查信息密度"""
        if not notes:
            return 0.0

        total_text = " ".join(notes)
        words = total_text.split()
        unique_words = set(word.lower() for word in words)

        if not words:
            return 0.0

        # 信息密度：独特词汇比例
        density = len(unique_words) / len(words)

        # 归一化到0-1范围
        return min(1.0, density * 2)


class ResearchStateAnalyzer:
    """研究状态分析器 - 深度分析并给出行动建议"""

    async def analyze_research_state(self, state: SupervisorState, config) -> dict:
        """深度分析研究状态，给出最优行动建议"""

        # 1. 质量评估
        quality_metrics = self.assess_quality(state)

        # 2. 覆盖度分析
        coverage_analysis = self.analyze_coverage(state)

        # 3. 资源状态
        resource_status = self.check_resource_status(state, config)

        # 4. 综合决策
        action = self.make_intelligent_decision(
            quality_metrics, coverage_analysis, resource_status
        )

        return {
            "action": action,  # "research", "complete", "refine"
            "research_topics": await self.generate_research_topics(state, action, config),
            "strategy": self.determine_strategy(state, action),
            "confidence": self.calculate_decision_confidence(),
            "reasoning": self.explain_decision(quality_metrics, coverage_analysis),
            "quality_metrics": quality_metrics,
            "coverage_analysis": coverage_analysis,
            "resource_status": resource_status
        }

    def assess_quality(self, state):
        """评估研究质量"""
        notes = state.get("notes", [])
        if not notes:
            return {"score": 0.0, "breadth": 0.0, "depth": 0.0}

        # 质量指标
        findings_count = len(notes)
        avg_length = sum(len(note) for note in notes) / findings_count

        breadth_score = min(1.0, findings_count / 5)  # 5个发现为满分
        depth_score = min(1.0, avg_length / 200)     # 200字符为满分

        overall_score = (breadth_score + depth_score) / 2

        return {
            "score": overall_score,
            "breadth": breadth_score,
            "depth": depth_score,
            "count": findings_count,
            "avg_length": avg_length
        }

    def analyze_coverage(self, state):
        """分析覆盖度"""
        research_brief = state.get("research_brief", "")
        notes = state.get("notes", [])

        if not research_brief:
            return {"score": 0.0}

        # 简化的关键词覆盖度分析
        brief_keywords = set(research_brief.lower().split())
        notes_text = " ".join(notes).lower()

        covered_keywords = sum(1 for keyword in brief_keywords if keyword in notes_text)

        coverage_score = covered_keywords / len(brief_keywords) if brief_keywords else 0.0

        return {
            "score": coverage_score,
            "covered_keywords": covered_keywords,
            "total_keywords": len(brief_keywords)
        }

    def check_resource_status(self, state, config):
        """检查资源状态"""
        iterations = state.get("research_iterations", 0)
        used_units = state.get("used_research_units", 0)

        # 处理config可能是字典的情况
        if isinstance(config, dict):
            max_iterations = config.get("max_researcher_iterations", 5)
            max_units = config.get("max_concurrent_research_units", 3)
        else:
            max_iterations = config.max_researcher_iterations
            max_units = config.max_concurrent_research_units

        return {
            "iterations_remaining": max_iterations - iterations,
            "units_remaining": max_units - used_units,
            "iterations_used": iterations,
            "units_used": used_units,
            "progress_ratio": iterations / max_iterations
        }

    def make_intelligent_decision(self, quality, coverage, resources):
        """多因子智能决策"""

        # 基础评分
        quality_score = quality["score"]
        coverage_score = coverage["score"]
        progress_ratio = resources["progress_ratio"]

        # 完成倾向评分
        completion_score = (quality_score + coverage_score) / 2

        # 研究倾向评分
        research_score = (1 - completion_score) * (1 - progress_ratio * 0.5)

        # 决策逻辑
        if completion_score > 0.75 or progress_ratio > 0.8:
            return "complete"
        elif research_score > 0.4 and resources["iterations_remaining"] > 0:
            return "research"
        else:
            return "complete"  # 默认倾向完成

    async def generate_research_topics(self, state, action, config):
        """使用AI模型智能生成多个互补的研究主题"""
        if action != "research":
            return []

        research_brief = state.get("research_brief", "")
        notes = state.get("notes", [])
        
        # 获取配置
        configurable = Configuration.from_runnable_config(config)
        target_count = min(configurable.max_concurrent_research_units, 5)
        
        # 构建提示词 - 传递所有已有发现，避免重复研究
        if notes:
            # 传递所有notes，但限制总长度避免token超限
            all_notes = "\n\n".join(notes)
            if len(all_notes) > 3000:  # 如果太长，截断但保留完整条目
                # 尽可能多地包含完整的notes
                existing_notes_text = "\n\n".join(notes[:10]) + "\n\n...(还有更多发现)"
            else:
                existing_notes_text = all_notes
        else:
            existing_notes_text = "暂无"
        
        prompt_content = generate_research_topics_prompt.format(
            research_brief=research_brief,
            existing_notes=existing_notes_text,
            target_count=target_count
        )
        
        # 配置AI模型
        model_config = {
            "model": configurable.research_model,
            "max_tokens": 2000,
            "api_key": get_api_key_for_model(configurable.research_model, config),
            "tags": ["langsmith:nostream"]
        }
        
        # 调用AI模型生成主题
        try:
            from .qwen_model import init_qwen_model
            
            # 使用结构化输出
            topic_model = (
                init_qwen_model(
                    model=configurable.research_model,
                    max_tokens=2000
                )
                .with_structured_output(ResearchTopicsResponse)
                .with_config(model_config)
            )
            
            response = await topic_model.ainvoke([HumanMessage(content=prompt_content)])
            
            research_topics = response.research_topics
            
            logger.info(f"[RESEARCH_TOPICS] AI分析: {response.analysis}")
            logger.info(f"[RESEARCH_TOPICS] 生成 {len(research_topics)} 个研究主题")
            for i, topic in enumerate(research_topics, 1):
                logger.info(f"  主题{i}: {topic[:100]}...")
            logger.info(f"[RESEARCH_TOPICS] 推理: {response.reasoning}")
            
            return research_topics[:target_count]
        
        except Exception as e:
            logger.error(f"[RESEARCH_TOPICS] AI生成失败: {e}")
            # 降级策略：返回基础主题
            return [research_brief]

    def determine_strategy(self, state, action):
        """确定研究策略"""
        if action == "research":
            resources = self.check_resource_status(state, Configuration())
            if resources["iterations_remaining"] > 3:
                return "exploratory"
            else:
                return "focused"
        elif action == "complete":
            return "comprehensive"
        else:
            return "refined"

    def calculate_decision_confidence(self):
        """计算决策置信度"""
        # 简化实现
        return 0.8

    def explain_decision(self, quality, coverage):
        """解释决策原因"""
        return f"质量评分: {quality['score']:.2f}, 覆盖度: {coverage['score']:.2f}"

# 初始化可配置模型
# 模型名称从环境变量读取
import logging
logger = logging.getLogger(__name__)

configurable_model = init_qwen_model(
    model=None,  # 从环境变量LLM_MODEL读取  
    max_tokens=4000
)

logger.info(f"🤖 监督者模型初始化: model={configurable_model.model_name}")


# ═══════════════════════════════════════════════════════════════
# 核心节点：supervisor_planner（合并原supervisor和decision_executor）
# ═══════════════════════════════════════════════════════════════

@trace_node("supervisor_planner", ["supervisor", "planning", "decision"])
async def supervisor_planner(state: SupervisorState, config: RunnableConfig) -> dict:
    """统一的监督者规划节点 - 整合进度计算、LLM决策和智能控制
    
    此节点合并了原来的supervisor和decision_executor功能：
    1. 计算当前进度（迭代次数、研究单元使用）
    2. 构建带进度信息的系统提示词
    3. 执行智能决策分析
    4. 返回决策结果（研究主题列表 或 完成信号）
    
    Args:
        state: 当前监督者状态
        config: 运行时配置
        
    Returns:
        包含决策结果和更新状态的字典
    """
    configurable = Configuration.from_runnable_config(config)
    research_iterations = state.get("research_iterations", 0)
    used_research_units = state.get("used_research_units", 0)

    # 步骤1：计算进度参数
    current_iteration = research_iterations + 1
    remaining_iterations = configurable.max_researcher_iterations - research_iterations
    remaining_units = configurable.max_concurrent_research_units - used_research_units

    logger.info(f"[SUPERVISOR_PLANNER] 🎯 第 {current_iteration} 轮规划开始")
    logger.info(f"[SUPERVISOR_PLANNER] 📊 进度: {current_iteration}/{configurable.max_researcher_iterations} 迭代, {used_research_units}/{configurable.max_concurrent_research_units} 研究单元")

    # 步骤2：初始化控制器
    quality_controller = ResearchQualityController()
    exit_controller = SmartExitController()
    progressive_strategy = ProgressiveCompletionStrategy()
    state_analyzer = ResearchStateAnalyzer()

    current_findings = state.get("notes", [])

    # 步骤3：强制退出检查
    force_exit, exit_reason = exit_controller.should_force_complete(state, config)
    if force_exit:
        logger.info(f"[SUPERVISOR_PLANNER] 🛑 强制完成: {exit_reason}")
        return {
            "decision": {
                "reflection": f"强制完成研究: {exit_reason}",
                "should_conduct_research": False,
                "research_topics": [],
                "is_complete": True,
                "reasoning": exit_reason
            },
            "last_action": "complete",
            "completion_reason": f"强制完成: {exit_reason}",
            "exit_type": "forced"
        }

    # 步骤4：质量控制检查
    if current_findings:
        previous_findings = state.get("previous_notes", [])
        should_continue, quality_reason = quality_controller.should_continue_research(
            current_findings, previous_findings, research_iterations
        )

        if not should_continue:
            logger.info(f"[SUPERVISOR_PLANNER] 🛑 质量控制阻止继续研究: {quality_reason}")
            return {
                "decision": {
                    "reflection": f"质量控制阻止继续研究: {quality_reason}",
                    "should_conduct_research": False,
                    "research_topics": [],
                    "is_complete": True,
                    "reasoning": quality_reason
                },
                "last_action": "complete",
                "completion_reason": f"质量控制: {quality_reason}",
                "exit_type": "quality_control"
            }

    # 步骤5：智能退出评估
    exit_recommendation, exit_reason = exit_controller.evaluate_exit_conditions(state, config)

    completion_threshold = progressive_strategy.get_completion_threshold(
        research_iterations, configurable.max_researcher_iterations
    )

    # 步骤6：状态分析和决策
    logger.info(f"[SUPERVISOR_PLANNER] 🤔 开始深度分析研究状态...")
    analysis = await state_analyzer.analyze_research_state(state, config)
    logger.info(f"[SUPERVISOR_PLANNER] 📈 分析结果: 行动={analysis['action']}, 质量={analysis['quality_metrics']['score']:.2f}, 覆盖={analysis['coverage_analysis']['score']:.2f}")

    # 步骤7：基于退出建议调整决策
    if exit_recommendation in ["strong_complete", "consider_complete"]:
        completion_score = (analysis["quality_metrics"]["score"] + analysis["coverage_analysis"]["score"]) / 2
        if completion_score >= completion_threshold:
            analysis["action"] = "complete"
            analysis["reasoning"] += f" | 退出建议: {exit_reason}"
            logger.info(f"[SUPERVISOR_PLANNER] ✅ 智能退出评估建议完成: {exit_reason}")

    # 步骤8：执行最终决策
    if analysis["action"] == "research":
        # 执行研究
        research_topics = analysis["research_topics"]
        if not research_topics:
            # 如果没有生成研究主题，强制完成
            logger.warning("[SUPERVISOR_PLANNER] ⚠️ 未生成研究主题，强制完成")
            return {
                "decision": {
                    "reflection": "无法生成有效研究主题，强制完成",
                    "should_conduct_research": False,
                    "research_topics": [],
                    "is_complete": True,
                    "reasoning": "无法生成有效研究主题"
                },
                "last_action": "complete",
                "completion_reason": "无法生成研究主题",
                "exit_type": "no_topics"
            }

        # 限制研究主题数量
        research_topics = research_topics[:configurable.max_concurrent_research_units]

        logger.info(f"[SUPERVISOR_PLANNER] 🔍 决定执行研究: {len(research_topics)} 个主题")
        for i, topic in enumerate(research_topics, 1):
            logger.info(f"  主题{i}: {topic[:80]}...")

        # 返回决策，让路由系统转到 conduct_research
        return {
            "decision": {
                "reflection": f"准备执行研究: {', '.join(t[:30] for t in research_topics[:2])}{'...' if len(research_topics) > 2 else ''}",
                "should_conduct_research": True,
                "research_topics": research_topics,
                "is_complete": False,
                "reasoning": analysis["reasoning"]
            },
            "last_action": "research",
            "exit_recommendation": exit_recommendation
        }

    elif analysis["action"] == "complete":
        logger.info(f"[SUPERVISOR_PLANNER] ✅ 决定完成研究: {analysis['reasoning']}")
        return {
            "decision": {
                "reflection": f"决定完成研究: {analysis['reasoning']}",
                "should_conduct_research": False,
                "research_topics": [],
                "is_complete": True,
                "reasoning": analysis["reasoning"]
            },
            "last_action": "complete",
            "completion_reason": analysis["reasoning"],
            "exit_type": "decision",
            "final_quality_score": (analysis["quality_metrics"]["score"] + analysis["coverage_analysis"]["score"]) / 2
        }

    else:
        # 默认完成
        logger.warning(f"[SUPERVISOR_PLANNER] ⚠️ 未知行动类型，默认完成: {analysis['action']}")
        return {
            "decision": {
                "reflection": f"未知行动类型，默认完成: {analysis['action']}",
                "should_conduct_research": False,
                "research_topics": [],
                "is_complete": True,
                "reasoning": f"未知行动类型: {analysis['action']}"
            },
            "last_action": "complete",
            "completion_reason": f"未知行动类型: {analysis['action']}",
            "exit_type": "fallback"
        }


# ═══════════════════════════════════════════════════════════════
# 研究执行节点
# ═══════════════════════════════════════════════════════════════

@trace_node("conduct_research", ["research", "tools", "search"])
async def conduct_research(state: SupervisorState, config: RunnableConfig) -> dict:
    """执行研究节点 - 调用 researcher_subgraph 执行实际研究
    
    此节点会：
    1. 从决策中提取研究主题
    2. 并行调用多个 researcher_subgraph
    3. 收集研究结果并聚合
    4. 返回研究发现
    
    Args:
        state: 当前监督者状态
        config: 运行时配置
        
    Returns:
        包含研究结果的字典
    """
    logger.info("[CONDUCT_RESEARCH] 🔍 开始执行研究...")
    
    configurable = Configuration.from_runnable_config(config)
    decision = state.get("decision")
    
    if not decision:
        logger.warning("[CONDUCT_RESEARCH] ⚠️ 没有决策信息，跳过")
        return {}
    
    research_topics = decision.get("research_topics", [])
    if not research_topics:
        logger.warning("[CONDUCT_RESEARCH] ⚠️ 没有研究主题，跳过")
        return {}
    
    # 限制并发研究单元数
    research_topics = research_topics[:configurable.max_concurrent_research_units]
    overflow_topics = decision.get("research_topics", [])[configurable.max_concurrent_research_units:]
    
    if overflow_topics:
        logger.warning(f"[CONDUCT_RESEARCH] ⚠️ 超出并发限制，忽略 {len(overflow_topics)} 个主题")
    
    logger.info(f"[CONDUCT_RESEARCH] 📋 并行执行 {len(research_topics)} 个研究任务")
    
    try:
        # 导入 researcher_subgraph（延迟导入避免循环依赖）
        from .odr_researcher import researcher_subgraph
        
        # 并行执行研究任务
        research_tasks = [
            researcher_subgraph.ainvoke({
                "researcher_messages": [HumanMessage(content=topic)],
                "research_topic": topic,
                "tool_call_iterations": 0,
                "total_searches": 0
            }, config)
            for topic in research_topics
        ]
        
        tool_results = await asyncio.gather(*research_tasks)
        
        # 聚合研究结果
        all_findings = []
        raw_notes_list = []
        
        for i, (result, topic) in enumerate(zip(tool_results, research_topics), 1):
            compressed = result.get("compressed_research", "Error: No research output")
            all_findings.append(f"### Research {i}: {topic[:50]}...\n\n{compressed}")
            
            raw_notes = result.get("raw_notes", [])
            if raw_notes:
                raw_notes_list.extend(raw_notes)
        
        # 创建消息记录
        findings_message = AIMessage(content="\n\n".join(all_findings))
        
        logger.info(f"[CONDUCT_RESEARCH] ✅ 研究完成，共 {len(all_findings)} 个主题")

        # 更新研究单元计数器
        current_used_units = state.get("used_research_units", 0)
        new_used_units = current_used_units + len(research_topics)

        logger.info(f"[CONDUCT_RESEARCH] 📊 研究单元更新: {current_used_units} + {len(research_topics)} = {new_used_units}")

        return {
            "supervisor_messages": [findings_message],
            "notes": all_findings,
            "raw_notes": raw_notes_list,
            "used_research_units": new_used_units,
            "last_action": "research_completed",
            "research_iterations": state.get("research_iterations", 0) + 1
        }
        
    except Exception as e:
        logger.error(f"[CONDUCT_RESEARCH] ❌ 研究执行失败: {e}")
        error_message = AIMessage(content=f"Research execution failed: {str(e)}")
        return {
            "supervisor_messages": [error_message]
        }


# ═══════════════════════════════════════════════════════════════
# 完成节点
# ═══════════════════════════════════════════════════════════════

@trace_node("final_complete", ["supervisor", "completion", "summary"])
async def final_complete(state: SupervisorState, config: RunnableConfig) -> dict:
    """最终完成节点 - 整理和优化所有发现"""

    logger.info("[FINAL_COMPLETE] 📋 整理最终研究发现...")

    # 1. 收集所有发现
    all_notes = state.get("notes", [])

    # 2. 质量优化和去重
    optimized_findings = []
    seen_content = set()

    for note in all_notes:
        # 简单的去重逻辑
        note_hash = hash(note[:100])  # 使用前100字符作为哈希
        if note_hash not in seen_content:
            optimized_findings.append(note)
            seen_content.add(note_hash)

    # 3. 生成研究总结
    research_summary = f"研究总结: 共收集 {len(optimized_findings)} 条研究发现"

    # 4. 评估完成质量
    completion_quality = {
        "overall_score": min(1.0, len(optimized_findings) / 5),  # 5个发现为满分
        "findings_count": len(optimized_findings),
        "avg_quality": sum(len(note) for note in optimized_findings) / len(optimized_findings) if optimized_findings else 0
    }

    logger.info(f"[FINAL_COMPLETE] ✅ 研究完成，收集 {len(optimized_findings)} 条高质量发现")

    return {
        "notes": optimized_findings,
        "research_summary": research_summary,
        "completion_quality": completion_quality,
        "final_statistics": {
            "total_findings": len(optimized_findings),
            "research_iterations": state.get("research_iterations", 0),
            "research_units_used": state.get("used_research_units", 0),
            "quality_score": completion_quality["overall_score"]
        }
    }


# ═══════════════════════════════════════════════════════════════
# 路由函数
# ═══════════════════════════════════════════════════════════════

def route_after_planner(state: SupervisorState) -> Literal["conduct_research", "final_complete", "supervisor_planner"]:
    """基于 supervisor_planner 的决策结果进行路由
    
    流程：
    - 如果决定完成 → "final_complete"
    - 如果决定研究 → "conduct_research"
    - 如果研究完成 → "supervisor_planner"（继续下一轮）
    
    Args:
        state: 当前监督者状态
        
    Returns:
        下一个节点的名称
    """
    last_action = state.get("last_action", "")
    decision = state.get("decision", {})

    # 1. 研究完成后，回到planner开始下一轮
    if last_action == "research_completed":
        logger.info("[ROUTE] 🔄 研究完成，回到supervisor_planner开始下一轮")
        return "supervisor_planner"

    # 2. 决定完成研究
    if last_action == "complete" or decision.get("is_complete"):
        logger.info("[ROUTE] ✅ 决定完成研究，进入final_complete节点")
        return "final_complete"

    # 3. 决定执行研究
    elif last_action == "research" and decision.get("should_conduct_research"):
        logger.info("[ROUTE] 🔍 转到conduct_research节点")
        return "conduct_research"

    # 4. 异常情况，直接完成
    else:
        logger.warning(f"[ROUTE] ⚠️ 异常状态，直接完成: last_action={last_action}")
        return "final_complete"


def route_after_complete(state: SupervisorState) -> Literal["supervisor_planner", "__end__"]:
    """决定 final_complete 执行后是继续还是结束
    
    如果 decision.is_complete=True，说明应该结束
    否则，继续回到 supervisor_planner 进行下一轮
    """
    decision = state.get("decision", {})
    
    if decision and decision.get("is_complete"):
        logger.info("[ROUTE] ✅ 研究完成，结束 supervisor 子图")
        return END
    
    logger.info("[ROUTE] 🔄 继续下一轮规划")
    return "supervisor_planner"


# ═══════════════════════════════════════════════════════════════
# 构建简化的 supervisor 子图（单层架构）
# ═══════════════════════════════════════════════════════════════

supervisor_builder = StateGraph(SupervisorState, config_schema=Configuration)

# 添加三个主要节点
supervisor_builder.add_node("supervisor_planner", supervisor_planner)
supervisor_builder.add_node("conduct_research", conduct_research)
supervisor_builder.add_node("final_complete", final_complete)

# 定义流程
supervisor_builder.add_edge(START, "supervisor_planner")

# 条件边：supervisor_planner → 根据决策路由
supervisor_builder.add_conditional_edges(
    "supervisor_planner",
    route_after_planner,
    {
        "conduct_research": "conduct_research",
        "final_complete": "final_complete",
        "supervisor_planner": "supervisor_planner"
    }
)

# conduct_research 完成后路由
supervisor_builder.add_conditional_edges(
    "conduct_research",
    route_after_planner,
    {
        "supervisor_planner": "supervisor_planner",
        "final_complete": "final_complete",
        "conduct_research": "conduct_research"
    }
)

# final_complete 完成后直接结束
supervisor_builder.add_edge("final_complete", END)

# 编译简化的子图
supervisor_subgraph = supervisor_builder.compile()

logger.info("✅ Simplified supervisor subgraph initialized (3-node architecture)")
