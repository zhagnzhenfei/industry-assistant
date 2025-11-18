"""
Qwen模型集成
支持阿里云通义千问模型
"""
import os
import logging
from typing import Any, Dict, Optional
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.callbacks import CallbackManagerForLLMRun
import openai
from openai import OpenAI

logger = logging.getLogger(__name__)

class QwenChatModel(BaseChatModel):
    """通用聊天模型包装器（支持OpenAI兼容API）
    
    支持多种服务：
    - 阿里云通义千问
    - 硅基流动（SiliconFlow）
    - 其他OpenAI兼容服务
    """
    
    model_name: str = "qwen-plus"
    api_key: Optional[str] = None
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    max_tokens: int = 1000000
    temperature: float = 0.7
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 从环境变量读取配置（优先级：参数 > 环境变量 > 默认值）
        api_key = self.api_key or os.getenv("DASHSCOPE_API_KEY")
        base_url = os.getenv("DASHSCOPE_BASE_URL") or self.base_url
        
        # 日志记录实际使用的配置
        logger.info(f"🔧 模型配置: model={self.model_name}, base_url={base_url}")
        logger.info(f"🔑 API Key: {api_key[:10] if api_key else 'NOT SET'}...")
        
        # 在__init__中初始化client
        object.__setattr__(self, 'client', OpenAI(
            api_key=api_key,
            base_url=base_url,
        ))
    
    @property
    def _llm_type(self) -> str:
        return "qwen"
    
    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """生成聊天响应"""
        
        # 转换消息格式
        openai_messages = []
        for message in messages:
            if isinstance(message, SystemMessage):
                openai_messages.append({"role": "system", "content": message.content})
            elif isinstance(message, HumanMessage):
                openai_messages.append({"role": "user", "content": message.content})
            elif isinstance(message, AIMessage):
                openai_messages.append({"role": "assistant", "content": message.content})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=openai_messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                **kwargs
            )
            
            message = response.choices[0].message
            ai_message = AIMessage(content=message.content)
            
            # 处理工具调用
            if hasattr(message, 'tool_calls') and message.tool_calls:
                ai_message.tool_calls = []
                for tool_call in message.tool_calls:
                    if hasattr(tool_call, 'function'):
                        # OpenAI 格式的工具调用
                        # 解析 arguments 字符串为字典
                        import json
                        try:
                            args_dict = json.loads(tool_call.function.arguments)
                        except (json.JSONDecodeError, TypeError):
                            args_dict = {}
                        
                        ai_message.tool_calls.append({
                            "name": tool_call.function.name,
                            "args": args_dict,
                            "id": tool_call.id
                        })
                    else:
                        # 其他格式的工具调用
                        ai_message.tool_calls.append(tool_call)
            
            return ChatResult(generations=[ChatGeneration(message=ai_message)])
            
        except Exception as e:
            raise Exception(f"Qwen API调用失败: {e}")
    
    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """异步生成聊天响应"""
        # 对于简单的实现，我们使用同步版本
        return self._generate(messages, stop, run_manager, **kwargs)
    
    def with_structured_output(self, schema, **kwargs):
        """支持结构化输出的包装器"""
        from langchain_core.runnables import RunnableLambda

        def extract_json_from_markdown(content: str) -> str:
            """
            从markdown代码块中提取JSON内容
            如果没有markdown标记，直接返回原内容
            """
            import re

            # 匹配 ```json 或 ``` 包裹的内容
            pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)

            if matches:
                return matches[0].strip()

            return content.strip()

        def parse_output(messages):
            """解析输出为结构化格式"""
            try:
                # 调用模型生成响应
                response = self._generate(messages)
                content = response.generations[0].message.content

                # 首先清理markdown格式的JSON
                content = extract_json_from_markdown(content)

                # 然后尝试直接解析为JSON
                try:
                    import json
                    data = json.loads(content)
                    return schema(**data)
                except:
                    pass
                
                # 如果JSON解析失败，尝试Pydantic的model_validate_json
                try:
                    return schema.model_validate_json(content)
                except:
                    pass
                
                # 如果都失败了，尝试从文本中提取信息
                try:
                    # 对于不同的schema类型，使用不同的解析策略
                    if schema.__name__ == "ClarifyWithUser":
                        # 解析澄清请求
                        need_clarification = "clarification" in content.lower() or "clarify" in content.lower()
                        question = content if need_clarification else ""
                        verification = "我们将开始研究" if not need_clarification else "请提供更多信息"
                        return schema(
                            need_clarification=need_clarification,
                            question=question,
                            verification=verification
                        )
                    elif schema.__name__ == "ResearchQuestion":
                        # 解析研究问题
                        return schema(research_brief=content)
                    elif schema.__name__ == "Summary":
                        # 解析摘要
                        return schema(
                            summary=content,
                            key_excerpts=content
                        )
                    elif schema.__name__ == "ConductResearch":
                        # 解析研究主题
                        return schema(research_topic=content)
                    elif schema.__name__ == "ResearchComplete":
                        # 研究完成
                        return schema()
                    else:
                        # 默认处理
                        if hasattr(schema, '__fields__'):
                            fields = schema.__fields__
                            result = {}
                            for field_name in fields.keys():
                                result[field_name] = content
                            return schema(**result)
                        return content
                except Exception as e:
                    # 最后的兜底策略
                    print(f"结构化输出解析失败: {e}")
                    if schema.__name__ == "ClarifyWithUser":
                        return schema(need_clarification=False, question="", verification="开始研究")
                    elif schema.__name__ == "ResearchQuestion":
                        return schema(research_brief=content)
                    elif schema.__name__ == "Summary":
                        return schema(summary=content, key_excerpts=content)
                    elif schema.__name__ == "ConductResearch":
                        return schema(research_topic=content)
                    elif schema.__name__ == "ResearchComplete":
                        return schema()
                    else:
                        return content
            except Exception as e:
                print(f"结构化输出完全失败: {e}")
                # 返回默认值
                if schema.__name__ == "ClarifyWithUser":
                    return schema(need_clarification=False, question="", verification="开始研究")
                elif schema.__name__ == "ResearchQuestion":
                    return schema(research_brief="默认研究简报")
                elif schema.__name__ == "Summary":
                    return schema(summary="默认摘要", key_excerpts="默认摘录")
                elif schema.__name__ == "ConductResearch":
                    return schema(research_topic="默认研究主题")
                elif schema.__name__ == "ResearchComplete":
                    return schema()
                else:
                    return "解析失败"
        
        # 返回一个包装了解析逻辑的runnable
        return RunnableLambda(lambda x: parse_output(x))
    
    def with_retry(self, **kwargs):
        """支持重试的包装器"""
        # 简单的重试实现
        return self
    
    def bind_tools(self, tools, **kwargs):
        """绑定工具到模型"""
        # 如果有工具，将工具信息添加到API调用中
        if tools:
            # 转换工具为OpenAI格式
            openai_tools = []
            for tool in tools:
                try:
                    # 获取工具信息
                    if hasattr(tool, 'name'):
                        tool_name = tool.name
                    elif hasattr(tool, 'tool_name'):
                        tool_name = tool.tool_name
                    elif hasattr(tool, '__name__'):
                        tool_name = tool.__name__
                    else:
                        tool_name = str(tool)
                    
                    if hasattr(tool, 'description'):
                        tool_desc = tool.description
                    elif hasattr(tool, 'desc'):
                        tool_desc = tool.desc
                    else:
                        tool_desc = "无描述"
                    
                    # 获取参数schema
                    tool_schema = {}
                    if hasattr(tool, 'args_schema'):
                        tool_schema = tool.args_schema.model_json_schema()
                    elif hasattr(tool, 'parameters'):
                        tool_schema = tool.parameters
                    
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "description": tool_desc,
                            "parameters": tool_schema
                        }
                    })
                except Exception as e:
                    logger.warning(f"Tool binding error: {e}, tool type: {type(tool)}")
                    continue
            
            # 创建一个包装器，将工具信息传递给API
            from langchain_core.runnables import RunnableLambda
            
            def tool_wrapper(messages):
                return self._generate(messages, tools=openai_tools, **kwargs)
            
            return RunnableLambda(lambda x: tool_wrapper(x))
        else:
            # 没有工具时，直接返回模型
            return self

def init_qwen_model(
    model: str = None,
    api_key: Optional[str] = None,
    max_tokens: int = 4000,
    temperature: float = 0.7,
    **kwargs
) -> QwenChatModel:
    """
    初始化聊天模型（支持OpenAI兼容API）
    
    Args:
        model: 模型名称，默认从环境变量TEXT2SQL_MODEL或LLM_MODEL读取
        api_key: API密钥，默认从环境变量读取
        max_tokens: 最大token数
        temperature: 温度参数
    
    环境变量：
        - TEXT2SQL_MODEL: Text2SQL专用模型名称
        - LLM_MODEL: 通用模型名称
        - DASHSCOPE_API_KEY: API密钥
        - DASHSCOPE_BASE_URL: API基础URL
    
    Examples:
        # 使用阿里云通义千问
        export DASHSCOPE_API_KEY=sk-xxx
        export DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
        export TEXT2SQL_MODEL=qwen-plus
        
        # 使用硅基流动
        export DASHSCOPE_API_KEY=sk-xxx
        export DASHSCOPE_BASE_URL=https://api.siliconflow.cn/v1
        export TEXT2SQL_MODEL=Qwen/Qwen2.5-7B-Instruct
    """
    # 模型名称优先级：参数 > TEXT2SQL_MODEL > LLM_MODEL > 默认值
    if model is None:
        model = os.getenv("TEXT2SQL_MODEL") or os.getenv("LLM_MODEL") or "qwen-plus"
        logger.info(f"📝 模型名称选择: TEXT2SQL_MODEL={os.getenv('TEXT2SQL_MODEL')}, LLM_MODEL={os.getenv('LLM_MODEL')}, 最终={model}")
    
    return QwenChatModel(
        model_name=model,
        api_key=api_key,
        max_tokens=max_tokens,
        temperature=temperature,
        **kwargs
    )

def get_api_key_for_qwen() -> str:
    """获取Qwen API密钥"""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("请设置环境变量 DASHSCOPE_API_KEY")
    return api_key
