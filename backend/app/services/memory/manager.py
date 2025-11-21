"""
统一记忆管理器

提供即插即用的记忆功能接入点
"""
import logging
import os
from typing import Dict, Any, Optional, List, Callable
from .strategies import InteractionType, InteractionStrategy
from .strategies.research import ResearchInteractionStrategy
from .strategies.chat import ChatInteractionStrategy
from .strategies.question import QuestionInteractionStrategy

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    统一记忆管理器 - 即插即用的记忆接入点

    功能：
    1. 策略管理：根据交互类型选择合适的策略
    2. 记忆加载：从记忆服务中加载相关记忆
    3. 上下文增强：为业务逻辑提供增强的上下文
    4. 自动保存：提供记忆保存的钩子函数
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化记忆管理器

        Args:
            config: 配置字典，如果为None则使用默认配置
        """
        self.config = config or self._load_default_config()
        self.memory_service = None
        self._strategies: Dict[InteractionType, InteractionStrategy] = {}
        self._initialized = False

        logger.info(f"🧠 [MEMORY_MANAGER] 初始化记忆管理器")

    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "enabled": os.getenv("MEMORY_ENABLED", "true").lower() == "true",
            "default_mode": os.getenv("MEMORY_DEFAULT_MODE", "smart"),
            "auto_save": os.getenv("MEMORY_AUTO_SAVE", "true").lower() == "true",
            "debug": os.getenv("MEMORY_DEBUG", "false").lower() == "true"
        }

    async def initialize(self):
        """异步初始化"""
        if self._initialized:
            return

        if not self.config.get("enabled", True):
            logger.info("🔴 [MEMORY_MANAGER] 记忆功能已禁用")
            self._initialized = True
            return

        try:
            # 初始化记忆服务
            from .memory_factory import get_memory_service
            self.memory_service = get_memory_service()

            if not self.memory_service:
                logger.warning("⚠️ [MEMORY_MANAGER] 记忆服务未初始化，记忆功能不可用")
                self._initialized = True
                return

            # 初始化策略
            await self._initialize_strategies()

            self._initialized = True
            logger.info("✅ [MEMORY_MANAGER] 记忆管理器初始化成功")

        except Exception as e:
            logger.error(f"❌ [MEMORY_MANAGER] 初始化失败: {e}")
            self._initialized = True  # 标记为已初始化，避免重复尝试

    async def _initialize_strategies(self):
        """初始化所有策略"""
        # 创建策略实例
        strategies = {
            InteractionType.RESEARCH: ResearchInteractionStrategy(self.memory_service),
            InteractionType.CHAT: ChatInteractionStrategy(self.memory_service),
            InteractionType.QUESTION: QuestionInteractionStrategy(self.memory_service)
        }

        # 配置策略
        for interaction_type, strategy in strategies.items():
            strategy_config = self.config.get(f"{interaction_type.value}_strategy", {})
            strategy.set_config(strategy_config)

        self._strategies = strategies

        logger.info(f"✅ [MEMORY_MANAGER] 已初始化 {len(strategies)} 个交互策略")

    async def process_interaction(
        self,
        user_id: str,
        interaction_type: InteractionType,
        input_data: Dict[str, Any],
        memory_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        统一处理交互，自动管理记忆

        Args:
            user_id: 用户ID
            interaction_type: 交互类型
            input_data: 输入数据（问题、消息等）
            memory_mode: 记忆模式，如果为None则使用默认模式

        Returns:
            处理结果，包含增强的上下文和保存钩子
        """
        if not self._initialized:
            await self.initialize()

        if not self._is_memory_available():
            return self._create_disabled_result(input_data)

        memory_mode = memory_mode or self.config.get("default_mode", "smart")

        logger.info(f"🔄 [MEMORY_MANAGER] 处理交互，类型: {interaction_type.value}, 模式: {memory_mode}")

        try:
            # 1. 加载相关记忆
            memories = await self._load_memories(
                user_id, interaction_type, input_data, memory_mode
            )

            # 2. 构建增强上下文
            enhanced_context = self._build_enhanced_context(
                input_data, memories, interaction_type
            )

            # 3. 设置自动保存钩子
            save_hook = self._create_save_hook(
                user_id, interaction_type, memory_mode
            ) if self.config.get("auto_save", True) else None

            result = {
                "memory_enabled": True,
                "context": enhanced_context,
                "memories": memories,
                "memory_count": len(memories),
                "memory_mode": memory_mode,
                "save_hook": save_hook,
                "interaction_type": interaction_type.value
            }

            logger.info(f"✅ [MEMORY_MANAGER] 交互处理完成，找到 {len(memories)} 条记忆")
            return result

        except Exception as e:
            logger.warning(f"⚠️ [MEMORY_MANAGER] 记忆处理失败: {e}")
            return self._create_disabled_result(input_data)

    def _is_memory_available(self) -> bool:
        """检查记忆服务是否可用"""
        return (
            self.config.get("enabled", True) and
            self.memory_service is not None
        )

    def _create_disabled_result(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建记忆禁用时的结果"""
        return {
            "memory_enabled": False,
            "context": input_data,
            "memories": [],
            "memory_count": 0,
            "memory_mode": "none",
            "save_hook": None,
            "interaction_type": "unknown"
        }

    async def _load_memories(
        self,
        user_id: str,
        interaction_type: InteractionType,
        input_data: Dict[str, Any],
        memory_mode: str
    ) -> List[Dict[str, Any]]:
        """加载记忆"""
        strategy = self._strategies.get(interaction_type)
        if not strategy:
            logger.warning(f"⚠️ [MEMORY_MANAGER] 未找到 {interaction_type.value} 的策略")
            return []

        try:
            memories = await strategy.load_memories(user_id, input_data, memory_mode)

            if self.config.get("debug", False):
                logger.debug(f"🔍 [MEMORY_MANAGER] 加载了 {len(memories)} 条记忆")
                for i, memory in enumerate(memories[:3]):  # 只显示前3条
                    logger.debug(f"   {i+1}. {memory.get('memory', {}).get('content', '')[:100]}...")

            return memories

        except Exception as e:
            logger.warning(f"⚠️ [MEMORY_MANAGER] 策略加载记忆失败: {e}")
            return []

    def _build_enhanced_context(
        self,
        input_data: Dict[str, Any],
        memories: List[Dict[str, Any]],
        interaction_type: InteractionType
    ) -> Dict[str, Any]:
        """构建增强的上下文"""
        # 基础上下文
        enhanced_context = input_data.copy()

        if not memories:
            enhanced_context.update({
                "has_memories": False,
                "memory_context": ""
            })
            return enhanced_context

        # 构建记忆上下文
        memory_context = self._build_memory_context(memories, interaction_type)

        # 添加记忆相关信息
        enhanced_context.update({
            "has_memories": True,
            "memory_count": len(memories),
            "memory_context": memory_context,
            "user_memories": memories,  # 向后兼容
            "memories_loaded_at": str(logger.name)  # 调试用
        })

        return enhanced_context

    def _build_memory_context(
        self,
        memories: List[Dict[str, Any]],
        interaction_type: InteractionType
    ) -> str:
        """构建记忆上下文字符串"""
        if not memories:
            return ""

        context_parts = [f"=== 相关历史{self._get_type_name(interaction_type)}记录 ==="]

        for i, memory in enumerate(memories, 1):
            content = memory.get("memory", {}).get("content", "")
            metadata = memory.get("metadata", {})

            # 格式化单个记忆
            memory_text = f"{i}. {content}"

            # 添加时间信息（如果有）
            created_at = metadata.get("created_at", "")
            if created_at:
                memory_text += f" (时间: {created_at[:10]})"  # 只显示日期部分

            context_parts.append(memory_text)

        context_parts.append("=== 基于以上历史记录，提供更相关的回答 ===")

        return "\n".join(context_parts)

    def _get_type_name(self, interaction_type: InteractionType) -> str:
        """获取交互类型的中文名称"""
        type_names = {
            InteractionType.RESEARCH: "研究",
            InteractionType.CHAT: "对话",
            InteractionType.QUESTION: "问答",
            InteractionType.DOCUMENT: "文档",
            InteractionType.SEARCH: "搜索",
            InteractionType.ASSISTANT: "助手"
        }
        return type_names.get(interaction_type, "交互")

    def _create_save_hook(
        self,
        user_id: str,
        interaction_type: InteractionType,
        memory_mode: str
    ) -> Optional[Callable]:
        """创建保存钩子函数"""
        strategy = self._strategies.get(interaction_type)
        if not strategy:
            logger.warning(f"⚠️ [MEMORY_MANAGER] 未找到 {interaction_type.value} 的保存策略")
            return None

        async def save_hook(result_data: Dict[str, Any]):
            """
            保存记忆的钩子函数

            Args:
                result_data: 结果数据，包含响应、元数据等
            """
            if memory_mode == "none":
                return

            try:
                success = await strategy.save_memory(user_id, result_data, memory_mode)

                if success:
                    logger.info(f"✅ [MEMORY_MANAGER] 记忆保存成功: {interaction_type.value}")
                else:
                    logger.warning(f"⚠️ [MEMORY_MANAGER] 记忆保存失败: {interaction_type.value}")

            except Exception as e:
                logger.error(f"💥 [MEMORY_MANAGER] 记忆保存异常: {e}")

        return save_hook

    async def get_memory_stats(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户的记忆统计信息

        Args:
            user_id: 用户ID

        Returns:
            记忆统计信息
        """
        if not self._is_memory_available():
            return {
                "enabled": False,
                "total_memories": 0,
                "by_type": {}
            }

        try:
            all_memories = await self.memory_service.get_all_memories(user_id, limit=1000)

            # 按类型统计
            by_type = {}
            for memory in all_memories:
                mem_type = memory.get("metadata", {}).get("type", "unknown")
                by_type[mem_type] = by_type.get(mem_type, 0) + 1

            return {
                "enabled": True,
                "total_memories": len(all_memories),
                "by_type": by_type,
                "strategies_available": list(self._strategies.keys())
            }

        except Exception as e:
            logger.warning(f"⚠️ [MEMORY_MANAGER] 获取记忆统计失败: {e}")
            return {
                "enabled": True,
                "total_memories": 0,
                "by_type": {},
                "error": str(e)
            }

    def get_available_strategies(self) -> List[str]:
        """获取可用的策略列表"""
        return [strategy.value for strategy in self._strategies.keys()]

    async def cleanup(self):
        """清理资源"""
        self.memory_service = None
        self._strategies.clear()
        self._initialized = False
        logger.info("🧹 [MEMORY_MANAGER] 资源清理完成")