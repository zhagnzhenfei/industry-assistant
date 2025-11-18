"""
记忆辅助工具类
"""
import logging
from typing import List, Dict, Any, Optional
import re
from datetime import datetime

logger = logging.getLogger(__name__)


class MemoryHelper:
    """记忆辅助工具类"""
    
    @staticmethod
    def format_memories_for_prompt(memories: List[Dict[str, Any]]) -> str:
        """
        格式化记忆为提示词
        
        Args:
            memories: 记忆列表
            
        Returns:
            格式化的字符串
        """
        if not memories:
            return ""
        
        formatted_parts = []
        
        for i, memory in enumerate(memories, 1):
            # 提取记忆内容
            memory_content = memory.get("memory", "")
            if isinstance(memory_content, dict):
                memory_content = memory_content.get("content", str(memory_content))
            
            # 提取元数据
            metadata = memory.get("metadata", {})
            created_at = metadata.get("created_at", "")
            memory_type = metadata.get("category", "")
            
            # 构建格式化字符串
            parts = [f"[记忆 {i}]"]
            if memory_type:
                parts.append(f"类型: {memory_type}")
            if memory_content:
                parts.append(f"内容: {memory_content}")
            if created_at:
                parts.append(f"时间: {created_at}")
            
            formatted_parts.append(" | ".join(parts))
        
        return "\n".join(formatted_parts)
    
    @staticmethod
    def extract_conversation_metadata(
        message: str, 
        response: str,
        conversation_type: str = "general"
    ) -> Dict[str, Any]:
        """
        提取对话元数据
        
        Args:
            message: 用户消息
            response: AI回复
            conversation_type: 对话类型
            
        Returns:
            元数据字典
        """
        metadata = {
            "conversation_type": conversation_type,
            "timestamp": datetime.now().isoformat(),
            "message_length": len(message),
            "response_length": len(response)
        }
        
        # 提取关键词
        keywords = MemoryHelper.extract_keywords(message)
        if keywords:
            metadata["keywords"] = keywords
        
        # 判断重要性
        importance = MemoryHelper.calculate_memory_importance(message, response)
        metadata["importance"] = importance
        
        return metadata
    
    @staticmethod
    def extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
        """
        提取文本关键词
        
        Args:
            text: 文本
            max_keywords: 最大关键词数
            
        Returns:
            关键词列表
        """
        # 简单的关键词提取（可以使用更复杂的NLP方法）
        # 移除标点符号
        text = re.sub(r'[^\w\s]', '', text)
        
        # 分词
        words = text.split()
        
        # 过滤停用词（简化版）
        stop_words = {"的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一", "这", "个"}
        keywords = [w for w in words if w not in stop_words and len(w) > 1]
        
        # 返回前N个关键词
        return keywords[:max_keywords]
    
    @staticmethod
    def calculate_memory_importance(
        message: str, 
        response: Optional[str] = None
    ) -> int:
        """
        计算记忆重要性（1-10）
        
        Args:
            message: 用户消息
            response: AI回复（可选）
            
        Returns:
            重要性评分（1-10）
        """
        importance = 5  # 默认中等重要性
        
        # 包含特定关键词增加重要性
        high_importance_keywords = ["重要", "记住", "务必", "关键", "必须", "永远", "一定"]
        for keyword in high_importance_keywords:
            if keyword in message:
                importance += 1
        
        # 包含偏好关键词增加重要性
        preference_keywords = ["我喜欢", "我偏好", "我习惯", "我希望", "我想要"]
        for keyword in preference_keywords:
            if keyword in message:
                importance += 2
        
        # 包含事实关键词增加重要性
        fact_keywords = ["事实", "数据", "信息", "资料", "证据"]
        for keyword in fact_keywords:
            if keyword in message:
                importance += 1
        
        # 长消息可能更重要
        if len(message) > 200:
            importance += 1
        
        # 限制在1-10范围内
        importance = max(1, min(10, importance))
        
        return importance
    
    @staticmethod
    def is_worth_remembering(
        message: str,
        response: Optional[str] = None,
        min_importance: int = 3
    ) -> bool:
        """
        判断对话是否值得记忆
        
        Args:
            message: 用户消息
            response: AI回复
            min_importance: 最小重要性阈值
            
        Returns:
            是否值得记忆
        """
        # 太短的消息可能不值得记忆
        if len(message) < 10:
            return False
        
        # 计算重要性
        importance = MemoryHelper.calculate_memory_importance(message, response)
        
        return importance >= min_importance
    
    @staticmethod
    def format_conversation_for_memory(
        message: str,
        response: str,
        include_response: bool = True
    ) -> str:
        """
        格式化对话为记忆内容
        
        Args:
            message: 用户消息
            response: AI回复
            include_response: 是否包含回复
            
        Returns:
            格式化的字符串
        """
        if include_response:
            return f"用户: {message}\nAI: {response}"
        else:
            return message
    
    @staticmethod
    def extract_user_preferences(message: str) -> Optional[str]:
        """
        从消息中提取用户偏好
        
        Args:
            message: 用户消息
            
        Returns:
            提取的偏好描述，如果没有则返回None
        """
        preference_patterns = [
            r"我喜欢(.+)",
            r"我偏好(.+)",
            r"我习惯(.+)",
            r"我希望(.+)",
            r"我想要(.+)"
        ]
        
        for pattern in preference_patterns:
            match = re.search(pattern, message)
            if match:
                preference = match.group(1).strip()
                return f"用户偏好: {preference}"
        
        return None
    
    @staticmethod
    def extract_important_facts(message: str) -> Optional[str]:
        """
        从消息中提取重要事实
        
        Args:
            message: 用户消息
            
        Returns:
            提取的事实描述，如果没有则返回None
        """
        fact_patterns = [
            r"记住(.+)",
            r"重要的是(.+)",
            r"事实是(.+)",
            r"数据显示(.+)"
        ]
        
        for pattern in fact_patterns:
            match = re.search(pattern, message)
            if match:
                fact = match.group(1).strip()
                return f"重要事实: {fact}"
        
        return None
    
    @staticmethod
    def categorize_conversation(message: str, response: str = "") -> str:
        """
        对对话进行分类
        
        Args:
            message: 用户消息
            response: AI回复
            
        Returns:
            对话类型
        """
        # 检查是否是研究相关
        if any(keyword in message for keyword in ["研究", "分析", "调查", "报告"]):
            return "research"
        
        # 检查是否是偏好相关
        if any(keyword in message for keyword in ["喜欢", "偏好", "习惯"]):
            return "preference"
        
        # 检查是否是事实相关
        if any(keyword in message for keyword in ["记住", "重要", "事实"]):
            return "fact"
        
        # 默认为一般对话
        return "general"
    
    @staticmethod
    def summarize_memories(memories: List[Dict[str, Any]]) -> str:
        """
        总结多条记忆
        
        Args:
            memories: 记忆列表
            
        Returns:
            总结字符串
        """
        if not memories:
            return "无相关记忆"
        
        summary_parts = [
            f"找到 {len(memories)} 条相关记忆:",
            ""
        ]
        
        # 按类型分组
        by_type = {}
        for memory in memories:
            metadata = memory.get("metadata", {})
            mem_type = metadata.get("conversation_type", "general")
            if mem_type not in by_type:
                by_type[mem_type] = []
            by_type[mem_type].append(memory)
        
        # 添加分组信息
        for mem_type, mems in by_type.items():
            summary_parts.append(f"- {mem_type}: {len(mems)} 条")
        
        return "\n".join(summary_parts)

