"""
交互策略基类

定义所有记忆策略的通用接口和基础功能
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class InteractionStrategy(ABC):
    """交互策略基类"""

    def __init__(self, memory_service=None):
        """
        初始化策略

        Args:
            memory_service: 记忆服务实例
        """
        self.memory_service = memory_service
        self.config = {}

    def set_memory_service(self, memory_service):
        """设置记忆服务"""
        self.memory_service = memory_service

    def set_config(self, config: Dict[str, Any]):
        """设置配置"""
        self.config.update(config)

    @abstractmethod
    async def load_memories(
        self,
        user_id: str,
        input_data: Dict[str, Any],
        memory_mode: str
    ) -> List[Dict[str, Any]]:
        """
        加载相关记忆

        Args:
            user_id: 用户ID
            input_data: 输入数据（包含用户问题、消息等）
            memory_mode: 记忆模式（none/short_term/long_term/smart）

        Returns:
            记忆列表
        """
        pass

    @abstractmethod
    async def save_memory(
        self,
        user_id: str,
        result_data: Dict[str, Any],
        memory_mode: str
    ) -> bool:
        """
        保存记忆

        Args:
            user_id: 用户ID
            result_data: 结果数据（包含响应、元数据等）
            memory_mode: 记忆模式

        Returns:
            是否保存成功
        """
        pass

    @abstractmethod
    def build_context_query(self, input_data: Dict[str, Any]) -> str:
        """
        构建用于记忆搜索的查询

        Args:
            input_data: 输入数据

        Returns:
            查询字符串
        """
        pass

    def should_save_memory(self, input_data: Dict[str, Any], result_data: Dict[str, Any]) -> bool:
        """
        判断是否应该保存记忆

        Args:
            input_data: 输入数据
            result_data: 结果数据

        Returns:
            是否应该保存
        """
        # 默认实现：基本过滤
        user_input = self._extract_user_input(input_data)

        # 过滤太短的输入
        if len(user_input) < 5:
            return False

        # 过滤常见无意义输入
        meaningless_inputs = ["你好", "hello", "hi", "ok", "谢谢", "thanks"]
        if user_input.lower().strip() in meaningless_inputs:
            return False

        return True

    def _extract_user_input(self, input_data: Dict[str, Any]) -> str:
        """提取用户输入"""
        # 尝试多种可能的字段名
        for field in ['question', 'message', 'query', 'prompt', 'input']:
            if field in input_data and input_data[field]:
                return str(input_data[field]).strip()

        return ""

    def _extract_user_response(self, result_data: Dict[str, Any]) -> str:
        """提取系统响应"""
        # 尝试多种可能的字段名
        for field in ['response', 'answer', 'result', 'output', 'final_report', 'content']:
            if field in result_data and result_data[field]:
                return str(result_data[field]).strip()

        return ""

    def _build_metadata(
        self,
        input_data: Dict[str, Any],
        result_data: Dict[str, Any],
        interaction_type: str
    ) -> Dict[str, Any]:
        """
        构建记忆元数据

        Args:
            input_data: 输入数据
            result_data: 结果数据
            interaction_type: 交互类型

        Returns:
            元数据字典
        """
        user_input = self._extract_user_input(input_data)
        response = self._extract_user_response(result_data)

        metadata = {
            "type": interaction_type,
            "timestamp": datetime.now().isoformat(),
            "input_length": len(user_input),
            "output_length": len(response),
            "created_at": datetime.now().isoformat()
        }

        # 添加额外的元数据
        if "research_id" in result_data:
            metadata["research_id"] = result_data["research_id"]

        if "session_id" in input_data:
            metadata["session_id"] = input_data["session_id"]

        if "quality_score" in result_data:
            metadata["quality_score"] = result_data["quality_score"]

        return metadata

    async def _safe_search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """安全的记忆搜索"""
        if not self.memory_service or not query.strip():
            return []

        try:
            result = await self.memory_service.search_memories(
                user_id=user_id,
                query=query.strip(),
                limit=limit
            )
            return result.get("memories", []) if result.get("success") else []

        except Exception as e:
            logger.warning(f"记忆搜索失败: {e}")
            return []

    async def _safe_get_all_memories(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """安全的获取所有记忆"""
        if not self.memory_service:
            return []

        try:
            return await self.memory_service.get_all_memories(user_id, limit)
        except Exception as e:
            logger.warning(f"获取记忆失败: {e}")
            return []

    async def _safe_add_memory(
        self,
        user_id: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """安全的添加记忆"""
        if not self.memory_service or not content.strip():
            return False

        try:
            result = await self.memory_service.add_memory(
                user_id=user_id,
                content=content.strip(),
                metadata=metadata,
                infer=True
            )
            return result.get("success", False)

        except Exception as e:
            logger.warning(f"添加记忆失败: {e}")
            return False