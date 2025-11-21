"""
记忆功能装饰器

提供即插即用的记忆功能装饰器
"""
import logging
import asyncio
import inspect
from functools import wraps
from typing import Dict, Any, Optional, Callable, Union

from .manager import MemoryManager
from .strategies import InteractionType

logger = logging.getLogger(__name__)


def with_memory(
    interaction_type: Union[InteractionType, str],
    memory_mode_param: str = "memory_mode",
    user_context_param: Optional[str] = None,
    auto_save: bool = True,
    config_key: Optional[str] = None,
    require_auth: bool = True
):
    """
    记忆功能装饰器 - 即插即用

    Args:
        interaction_type: 交互类型（InteractionType枚举或字符串）
        memory_mode_param: 记忆模式参数名（从请求对象中提取）
        user_context_param: 用户上下文参数名（注入到函数kwargs中）
        auto_save: 是否自动保存记忆
        config_key: 配置键（用于读取特定配置）
        require_auth: 是否需要用户认证

    Examples:
        # 基础用法
        @with_memory("research")
        async def research_endpoint(request):
            # 记忆功能自动启用
            pass

        # 高级用法
        @with_memory(
            interaction_type=InteractionType.CHAT,
            memory_mode_param="memory_mode",
            user_context_param="enhanced_context",
            auto_save=True
        )
        async def chat_endpoint(request, current_user, enhanced_context=None):
            # enhanced_context 包含增强的上下文信息
            pass
    """
    def decorator(func):
        # 检查函数是否是异步函数
        if not inspect.iscoroutinefunction(func):
            raise ValueError("with_memory 装饰器只能用于异步函数")

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 创建记忆管理器
            memory_manager = MemoryManager()
            await memory_manager.initialize()

            # 提取用户信息
            user_info = await _extract_user_info(kwargs, require_auth)
            if not user_info:
                # 如果需要认证但未提供用户信息，直接执行原函数
                if require_auth:
                    logger.warning("⚠️ [MEMORY_DECORATOR] 需要用户认证但未提供，跳过记忆功能")
                return await func(*args, **kwargs)

            user_id = user_info["user_id"]

            # 提取交互数据
            input_data = await _extract_input_data(kwargs)

            # 提取记忆模式
            memory_mode = await _extract_memory_mode(kwargs, memory_mode_param)

            # 处理交互
            memory_result = await memory_manager.process_interaction(
                user_id=user_id,
                interaction_type=_parse_interaction_type(interaction_type),
                input_data=input_data,
                memory_mode=memory_mode
            )

            # 注入增强的上下文
            if memory_result["memory_enabled"] and user_context_param:
                kwargs[user_context_param] = memory_result["context"]

            # 注入记忆相关信息（用于调试和监控）
            kwargs["_memory_result"] = memory_result

            # 执行原函数
            try:
                # 移除可能导致冲突的记忆相关参数
                clean_kwargs = {k: v for k, v in kwargs.items() if not k.startswith('_memory_')}

                result = await func(*args, **clean_kwargs)

                # 自动保存记忆
                if (auto_save and
                    memory_result["memory_enabled"] and
                    memory_result.get("save_hook")):

                    # 准备保存数据
                    save_data = await _prepare_save_data(
                        input_data, result, kwargs, interaction_type
                    )

                    # 异步保存记忆（不阻塞主流程）
                    asyncio.create_task(
                        _safe_save_memory(memory_result["save_hook"], save_data)
                    )

                    logger.info(f"💾 [MEMORY_DECORATOR] 已启动异步记忆保存任务")

                return result

            except Exception as e:
                logger.error(f"💥 [MEMORY_DECORATOR] 函数执行失败: {e}")
                raise

        return wrapper
    return decorator


def _parse_interaction_type(interaction_type: Union[InteractionType, str]) -> InteractionType:
    """解析交互类型"""
    if isinstance(interaction_type, InteractionType):
        return interaction_type

    if isinstance(interaction_type, str):
        try:
            return InteractionType(interaction_type.lower())
        except ValueError:
            logger.warning(f"⚠️ [MEMORY_DECORATOR] 未知的交互类型: {interaction_type}，使用默认值")
            return InteractionType.QUESTION

    logger.warning(f"⚠️ [MEMORY_DECORATOR] 无效的交互类型: {interaction_type}，使用默认值")
    return InteractionType.QUESTION


async def _extract_user_info(kwargs: Dict[str, Any], require_auth: bool) -> Optional[Dict[str, Any]]:
    """提取用户信息"""
    if not require_auth:
        return {"user_id": "anonymous"}

    # 尝试多种可能的用户参数
    user_params = ["current_user", "user", "user_obj"]

    for param in user_params:
        if param in kwargs:
            user_obj = kwargs[param]

            # 尝试多种可能的用户ID字段
            user_id_fields = ["user_id", "id", "username", "email"]

            for field in user_id_fields:
                if hasattr(user_obj, field):
                    user_id = getattr(user_obj, field)
                    if user_id:
                        return {"user_id": str(user_id), "user_obj": user_obj}

            # 如果对象本身是字符串，直接作为用户ID
            if isinstance(user_obj, str):
                return {"user_id": user_obj, "user_obj": user_obj}

    return None


async def _extract_input_data(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """提取输入数据"""
    input_data = {}

    # 尝试从请求对象中提取数据
    if "request" in kwargs:
        request = kwargs["request"]

        # 常见的请求字段
        data_fields = [
            "question", "message", "query", "prompt", "input", "content", "text"
        ]

        for field in data_fields:
            if hasattr(request, field):
                value = getattr(request, field)
                if value:
                    input_data[field] = str(value)

        # 如果request是字典或Pydantic模型
        if hasattr(request, "dict"):
            input_data.update(request.dict(exclude_unset=True))
        elif hasattr(request, "__dict__"):
            for field in data_fields:
                if field in request.__dict__:
                    input_data[field] = str(request.__dict__[field])

    # 直接从kwargs中提取
    direct_fields = ["question", "message", "query", "prompt", "input"]
    for field in direct_fields:
        if field in kwargs and kwargs[field]:
            input_data[field] = str(kwargs[field])

    return input_data


async def _extract_memory_mode(kwargs: Dict[str, Any], memory_mode_param: str) -> str:
    """提取记忆模式"""
    # 优先级：请求对象 > 直接参数 > 默认值

    # 1. 从请求对象中提取
    if "request" in kwargs:
        request = kwargs["request"]
        if hasattr(request, memory_mode_param):
            mode = getattr(request, memory_mode_param)
            if mode and mode in ["none", "short_term", "long_term", "smart"]:
                return mode

    # 2. 从直接参数中提取
    if memory_mode_param in kwargs:
        mode = kwargs[memory_mode_param]
        if mode and mode in ["none", "short_term", "long_term", "smart"]:
            return mode

    # 3. 使用默认值
    return "smart"


async def _prepare_save_data(
    input_data: Dict[str, Any],
    result: Any,
    kwargs: Dict[str, Any],
    interaction_type: Union[InteractionType, str]
) -> Dict[str, Any]:
    """准备保存数据"""
    save_data = {
        "interaction_type": _parse_interaction_type(interaction_type).value,
        "input_data": input_data,
        "result": result,
        "timestamp": str(logger.name)  # 简化的时间戳
    }

    # 添加特定的交互类型数据
    if _parse_interaction_type(interaction_type) == InteractionType.RESEARCH:
        # 研究类接口的特殊处理
        if hasattr(result, "final_report"):
            save_data["final_report"] = result.final_report
        if hasattr(result, "key_findings"):
            save_data["key_findings"] = result.key_findings
        if "research_id" in kwargs:
            save_data["research_id"] = kwargs["research_id"]

    elif _parse_interaction_type(interaction_type) == InteractionType.CHAT:
        # 聊天类接口的特殊处理
        save_data["user_message"] = input_data.get("message", "")
        if isinstance(result, dict):
            save_data["ai_response"] = result.get("response", result.get("answer", ""))
        elif hasattr(result, "response"):
            save_data["ai_response"] = result.response
        else:
            save_data["ai_response"] = str(result)

        # 添加会话信息
        if "session_id" in kwargs:
            save_data["session_id"] = kwargs["session_id"]

    elif _parse_interaction_type(interaction_type) == InteractionType.QUESTION:
        # 问答类接口的特殊处理
        save_data["question"] = input_data.get("question", "")
        if isinstance(result, dict):
            save_data["answer"] = result.get("answer", result.get("response", ""))
        elif hasattr(result, "answer"):
            save_data["answer"] = result.answer
        else:
            save_data["answer"] = str(result)

    # 保留原始输入
    save_data.update(input_data)

    return save_data


async def _safe_save_memory(save_hook: Callable, save_data: Dict[str, Any]):
    """安全的保存记忆"""
    try:
        await save_hook(save_data)
    except Exception as e:
        logger.error(f"💥 [MEMORY_DECORATOR] 异步保存记忆失败: {e}")


# 便捷装饰器
def research_memory(
    memory_mode_param: str = "memory_mode",
    user_context_param: Optional[str] = None,
    auto_save: bool = True
):
    """研究记忆装饰器的便捷版本"""
    return with_memory(
        interaction_type=InteractionType.RESEARCH,
        memory_mode_param=memory_mode_param,
        user_context_param=user_context_param,
        auto_save=auto_save,
        require_auth=True
    )


def chat_memory(
    memory_mode_param: str = "memory_mode",
    user_context_param: Optional[str] = None,
    auto_save: bool = True
):
    """聊天记忆装饰器的便捷版本"""
    return with_memory(
        interaction_type=InteractionType.CHAT,
        memory_mode_param=memory_mode_param,
        user_context_param=user_context_param,
        auto_save=auto_save,
        require_auth=True
    )


def question_memory(
    memory_mode_param: str = "memory_mode",
    user_context_param: Optional[str] = None,
    auto_save: bool = True
):
    """问答记忆装饰器的便捷版本"""
    return with_memory(
        interaction_type=InteractionType.QUESTION,
        memory_mode_param=memory_mode_param,
        user_context_param=user_context_param,
        auto_save=auto_save,
        require_auth=True
    )