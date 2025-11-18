"""
基础Agent类
定义所有Researcher Agent的通用接口和行为
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

from .mcp_client import MCPClient

logger = logging.getLogger(__name__)

class BaseResearcher(ABC):
    """Researcher Agent基类"""

    def __init__(self, mcp_client: MCPClient, name: str):
        self.mcp_client = mcp_client
        self.name = name
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    @abstractmethod
    async def research(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行研究任务 - 子类必须实现

        Args:
            query: 用户查询
            context: 上下文信息（工作目录、用户信息等）

        Returns:
            Dict[str, Any]: 研究结果
        """
        pass

    async def execute_with_logging(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        带日志记录的任务执行
        """
        self.start_time = datetime.now()
        logger.info(f"开始执行 {self.name} 任务: {query}")

        try:
            result = await self.research(query, context)
            self.end_time = datetime.now()

            duration = (self.end_time - self.start_time).total_seconds()
            logger.info(f"{self.name} 任务完成，耗时: {duration:.2f}秒")

            return {
                "agent": self.name,
                "query": query,
                "result": result,
                "execution_time": duration,
                "status": "success",
                "timestamp": self.end_time.isoformat()
            }

        except Exception as e:
            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()
            logger.error(f"{self.name} 任务失败: {e}, 耗时: {duration:.2f}秒")

            return {
                "agent": self.name,
                "query": query,
                "error": str(e),
                "execution_time": duration,
                "status": "failed",
                "timestamp": self.end_time.isoformat()
            }

    def can_handle(self, query: str) -> bool:
        """
        判断是否能处理该查询 - 子类可以重写

        Args:
            query: 用户查询

        Returns:
            bool: 是否能处理
        """
        return True

    def get_description(self) -> str:
        """获取Agent描述 - 子类应该重写"""
        return f"{self.name} - 基础研究Agent"

    async def validate_input(self, query: str, context: Dict[str, Any]) -> bool:
        """
        验证输入参数 - 子类可以重写

        Args:
            query: 用户查询
            context: 上下文信息

        Returns:
            bool: 输入是否有效
        """
        if not query or not query.strip():
            return False

        if not isinstance(context, dict):
            return False

        return True

    async def cleanup(self):
        """清理资源 - 子类可以重写"""
        pass


class TaskResult:
    """任务结果封装类"""

    def __init__(self, agent_name: str, query: str, result: Any,
                 execution_time: float, status: str = "success"):
        self.agent_name = agent_name
        self.query = query
        self.result = result
        self.execution_time = execution_time
        self.status = status
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "agent": self.agent_name,
            "query": self.query,
            "result": self.result,
            "execution_time": self.execution_time,
            "status": self.status,
            "timestamp": self.timestamp.isoformat()
        }

    def is_success(self) -> bool:
        """是否执行成功"""
        return self.status == "success"

    def get_error(self) -> Optional[str]:
        """获取错误信息"""
        return self.result.get("error") if not self.is_success() else None


class ResearchMetrics:
    """研究任务指标统计"""

    def __init__(self):
        self.total_tasks = 0
        self.successful_tasks = 0
        self.failed_tasks = 0
        self.total_execution_time = 0.0
        self.agent_performance = {}

    def add_result(self, result: TaskResult):
        """添加任务结果"""
        self.total_tasks += 1
        self.total_execution_time += result.execution_time

        if result.is_success():
            self.successful_tasks += 1
        else:
            self.failed_tasks += 1

        # 按Agent统计
        agent_name = result.agent_name
        if agent_name not in self.agent_performance:
            self.agent_performance[agent_name] = {
                "tasks": 0,
                "success": 0,
                "failed": 0,
                "total_time": 0.0
            }

        self.agent_performance[agent_name]["tasks"] += 1
        self.agent_performance[agent_name]["total_time"] += result.execution_time

        if result.is_success():
            self.agent_performance[agent_name]["success"] += 1
        else:
            self.agent_performance[agent_name]["failed"] += 1

    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks

    def get_average_execution_time(self) -> float:
        """获取平均执行时间"""
        if self.total_tasks == 0:
            return 0.0
        return self.total_execution_time / self.total_tasks

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": self.get_success_rate(),
            "average_execution_time": self.get_average_execution_time(),
            "total_execution_time": self.total_execution_time,
            "agent_performance": self.agent_performance
        }