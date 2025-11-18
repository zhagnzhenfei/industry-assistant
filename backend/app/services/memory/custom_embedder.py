"""
自定义 Embedder 类，使用项目中的 generate_embedding 函数
"""
import logging
from typing import List, Optional
from service.core.rag.nlp.model import generate_embedding

logger = logging.getLogger(__name__)


class CustomDashScopeEmbedder:
    """
    自定义 DashScope Embedder
    使用项目中的 generate_embedding 函数生成向量
    """
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model_name: Optional[str] = None):
        """
        初始化自定义 Embedder
        
        Args:
            api_key: DashScope API Key
            base_url: DashScope API Base URL
            model_name: 模型名称，默认 text-embedding-v1
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name or "text-embedding-v1"
        logger.info(f"初始化自定义 DashScope Embedder，模型: {self.model_name}")
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        生成文本的向量表示
        
        Args:
            texts: 文本列表
            
        Returns:
            向量列表
        """
        embeddings = []
        for text in texts:
            try:
                embedding = generate_embedding(
                    text=text,
                    api_key=self.api_key,
                    base_url=self.base_url,
                    model_name=self.model_name
                )
                embeddings.append(embedding)
            except Exception as e:
                logger.error(f"生成向量失败: {e}")
                raise
        
        return embeddings
    
    def embed_query(self, query: str) -> List[float]:
        """
        生成查询文本的向量表示
        
        Args:
            query: 查询文本
            
        Returns:
            向量
        """
        return self.embed([query])[0]
