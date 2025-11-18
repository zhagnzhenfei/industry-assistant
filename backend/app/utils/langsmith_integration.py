"""
LangSmith 集成工具
用于追踪、监控和调试 AI 研究应用
非侵入式设计，可随时启用/禁用
"""
import os
import uuid
import logging
from typing import Dict, Any, Optional, List

try:
    from langsmith import Client, traceable
    from langchain.callbacks.tracers import LangChainTracer
    from langchain.callbacks.manager import CallbackManager
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False

logger = logging.getLogger(__name__)


class LangSmithIntegration:
    """LangSmith 集成管理器 - 非侵入式设计"""

    def __init__(self,
                 project_name: str = "ai-research-platform",
                 enabled: Optional[bool] = None):
        self.project_name = project_name
        self.enabled = enabled if enabled is not None else self._check_enabled()
        self.client = None
        self.tracer = None

        if self.enabled:
            self._initialize()

    def _check_enabled(self) -> bool:
        """检查是否启用 LangSmith"""
        # 检查环境变量
        if not LANGSMITH_AVAILABLE:
            return False

        if os.getenv("LANGCHAIN_TRACING_V2", "false").lower() != "true":
            return False

        if not os.getenv("LANGCHAIN_API_KEY"):
            return False

        return True

    def _initialize(self):
        """初始化 LangSmith 连接"""
        try:
            # 设置环境变量
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_PROJECT"] = self.project_name

            # 创建客户端和追踪器
            api_key = os.getenv("LANGCHAIN_API_KEY")
            self.client = Client(api_key=api_key)
            self.tracer = LangChainTracer(project_name=self.project_name)

            logger.info(f"✅ LangSmith initialized for project: {self.project_name}")

        except Exception as e:
            logger.error(f"❌ Failed to initialize LangSmith: {e}")
            self.enabled = False

    def get_callback_manager(self) -> CallbackManager:
        """获取带有 LangSmith 追踪的回调管理器"""
        if not self.enabled or not self.tracer:
            return CallbackManager([])

        return CallbackManager([self.tracer])

    def get_config(self,
                   tags: Optional[List[str]] = None,
                   metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """获取 LangSmith 配置"""
        if not self.enabled:
            return {}

        config = {
            "callbacks": [self.tracer],
            "tags": tags or [],
            "metadata": metadata or {}
        }
        return config

    def trace_function(self,
                      name: str,
                      tags: Optional[List[str]] = None,
                      metadata: Optional[Dict[str, Any]] = None):
        """函数追踪装饰器"""
        def decorator(func):
            if not self.enabled:
                return func

            # 应用 traceable 装饰器
            traced_func = traceable(
                name=name,
                tags=tags or [],
                metadata=metadata or {}
            )(func)

            return traced_func
        return decorator

    def log_research_event(self, event_type: str, data: Dict[str, Any]):
        """记录研究相关事件"""
        if not self.enabled:
            return

        try:
            logger.info(f"[LANGSMITH] {event_type}: {data}")
        except Exception as e:
            logger.error(f"Failed to log event {event_type}: {e}")

    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self.enabled

    def get_project_name(self) -> str:
        """获取项目名称"""
        return self.project_name


# 全局实例 - 单例模式
_langsmith_instance = None


def get_langsmith_integration() -> LangSmithIntegration:
    """获取 LangSmith 集成实例（单例）"""
    global _langsmith_instance
    if _langsmith_instance is None:
        project_name = os.getenv("LANGSMITH_PROJECT", "ai-research-platform")
        _langsmith_instance = LangSmithIntegration(project_name=project_name)
    return _langsmith_instance


def trace_node(node_name: str, tags: Optional[List[str]] = None):
    """用于追踪 LangGraph 节点的装饰器"""
    integration = get_langsmith_integration()
    return integration.trace_function(
        name=node_name,
        tags=tags or ["langgraph", "node"]
    )


def trace_research_step(step_name: str, tags: Optional[List[str]] = None):
    """用于追踪研究步骤的装饰器"""
    integration = get_langsmith_integration()
    return integration.trace_function(
        name=step_name,
        tags=tags or ["research", "step"]
    )


def get_langsmith_config(tags: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """获取 LangSmith 配置的便捷函数"""
    integration = get_langsmith_integration()
    return integration.get_config(tags=tags, metadata=metadata)


def is_langsmith_enabled() -> bool:
    """检查 LangSmith 是否启用"""
    integration = get_langsmith_integration()
    return integration.is_enabled()


def log_research_start(question: str, user_id: Optional[str] = None):
    """记录研究开始"""
    integration = get_langsmith_integration()
    integration.log_research_event("research_start", {
        "question": question[:100] + "..." if len(question) > 100 else question,
        "user_id": user_id or "anonymous"
    })


def log_research_complete(question: str, duration: float, findings_count: int):
    """记录研究完成"""
    integration = get_langsmith_integration()
    integration.log_research_event("research_complete", {
        "question": question[:100] + "..." if len(question) > 100 else question,
        "duration_seconds": round(duration, 2),
        "findings_count": findings_count
    })


def log_node_execution(node_name: str, duration: float, success: bool = True):
    """记录节点执行"""
    integration = get_langsmith_integration()
    integration.log_research_event("node_execution", {
        "node": node_name,
        "duration_seconds": round(duration, 2),
        "success": success
    })