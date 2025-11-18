"""
自定义记忆服务实现
使用 PostgreSQL + Milvus + generate_embedding
完全自主实现，不依赖 Mem0
"""
import logging
import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncpg
from pymilvus import connections, Collection, utility
import asyncio

from service.core.rag.nlp.model import generate_embedding

logger = logging.getLogger(__name__)


class CustomMemoryService:
    """
    自定义记忆服务
    
    架构：
    - PostgreSQL: 存储记忆的完整数据和元数据
    - Milvus: 存储向量，用于语义搜索
    - generate_embedding: 使用项目中的 DashScope API 生成向量
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化自定义记忆服务
        
        Args:
            config: 配置字典，包含 PostgreSQL 和 Milvus 配置
        """
        self.config = config
        self.pg_pool: Optional[asyncpg.Pool] = None
        self.milvus_collection: Optional[Collection] = None
        self.collection_name = config.get("milvus_collection", "user_memories")
        self._initialized = False
        self._init_lock: Optional[asyncio.Lock] = None
    
    async def _ensure_initialized(self):
        """确保服务已初始化"""
        if self._initialized:
            return
        
        if self._init_lock is None:
            self._init_lock = asyncio.Lock()
        
        async with self._init_lock:
            if self._initialized:
                return
            await self._initialize()
    
    async def _initialize(self):
        """初始化数据库连接"""
        try:
            # 初始化 PostgreSQL 连接池
            self.pg_pool = await asyncpg.create_pool(
                host=self.config["postgres_host"],
                port=self.config["postgres_port"],
                database=self.config["postgres_db"],
                user=self.config["postgres_user"],
                password=self.config["postgres_password"],
                min_size=1,
                max_size=10
            )
            
            # 确保表存在
            await self._ensure_tables()
            
            # 初始化 Milvus 连接
            connections.connect(
                alias="default",
                host=self.config["milvus_host"],
                port=str(self.config["milvus_port"])
            )
            
            # 确保 collection 存在
            await self._ensure_collection()
            
            self._initialized = True
            logger.info("✅ 自定义记忆服务初始化成功")
            
        except Exception as e:
            logger.error(f"❌ 自定义记忆服务初始化失败: {e}")
            raise
    
    async def _ensure_tables(self):
        """确保 PostgreSQL 表存在"""
        async with self.pg_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);
                CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at DESC);
            """)
            logger.info("✅ PostgreSQL 表已就绪")
    
    async def _ensure_collection(self):
        """确保 Milvus collection 存在"""
        from pymilvus import CollectionSchema, FieldSchema, DataType
        
        if utility.has_collection(self.collection_name):
            logger.info(f"📊 Collection '{self.collection_name}' 已存在")
            self.milvus_collection = Collection(self.collection_name)
            # 检查现有collection的向量维度是否正确
            schema = self.milvus_collection.schema
            vector_field = None
            for field in schema.fields:
                if field.name == "vector":
                    vector_field = field
                    break
            
            if vector_field and vector_field.params.get("dim") != 1024:
                logger.warning(f"⚠️ 现有Collection的向量维度是 {vector_field.params.get('dim')}，需要1024维")
                logger.warning("⚠️ 建议删除现有Collection后重新创建，或使用匹配的embedding模型")
        else:
            logger.info(f"📊 创建新 Collection: {self.collection_name}")
            
            # 定义 schema
            # 注意：text-embedding-v4 的维度是 1024
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
                FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=50),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=1024),  # DashScope text-embedding-v4 维度是 1024
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
            ]
            
            schema = CollectionSchema(fields, "用户记忆向量集合")
            self.milvus_collection = Collection(self.collection_name, schema)
            
            # 创建索引
            index_params = {
                "metric_type": "L2",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 1024}
            }
            self.milvus_collection.create_index("vector", index_params)
        
        # 加载 collection
        self.milvus_collection.load()
        logger.info(f"✅ Milvus Collection 已就绪")
    
    async def add_memory(
        self,
        user_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        infer: bool = True
    ) -> Dict[str, Any]:
        """
        添加记忆
        
        Args:
            user_id: 用户ID
            content: 记忆内容
            metadata: 元数据
            infer: 是否使用LLM智能抽取（暂时忽略，后续可实现）
            
        Returns:
            添加结果
        """
        await self._ensure_initialized()
        try:
            memory_id = str(uuid.uuid4())
            
            # 生成向量
            logger.info(f"生成向量 - 内容长度: {len(content)}")
            embedding = generate_embedding(
                text=content,
                api_key=self.config.get("llm_api_key"),
                base_url=self.config.get("llm_base_url"),
                model_name=self.config.get("embedding_model", "text-embedding-v4")
            )
            
            # 保存到 PostgreSQL
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO memories (id, user_id, content, metadata, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, NOW(), NOW())
                """, memory_id, user_id, content, json.dumps(metadata or {}))
            
            # 保存向量到 Milvus
            # Milvus insert 需要按照字段顺序提供列表数据
            # 注意：每个字段都是一个列表，即使只有一条数据
            self.milvus_collection.insert([
                [memory_id],           # id 字段
                [user_id],             # user_id 字段
                [embedding],           # vector 字段
                [content[:65535]]      # content 字段（限制长度）
            ])
            
            logger.info(f"✅ 记忆添加成功 - ID: {memory_id}, 用户: {user_id}")
            
            return {
                "success": True,
                "result": {
                    "id": memory_id,
                    "user_id": user_id,
                    "content": content[:200] + "..." if len(content) > 200 else content,
                    "metadata": metadata
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 添加记忆失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        搜索记忆
        
        Args:
            user_id: 用户ID
            query: 查询文本
            limit: 返回数量
            
        Returns:
            搜索结果
        """
        await self._ensure_initialized()
        try:
            # 生成查询向量
            query_embedding = generate_embedding(
                text=query,
                api_key=self.config.get("llm_api_key"),
                base_url=self.config.get("llm_base_url"),
                model_name=self.config.get("embedding_model", "text-embedding-v4")
            )
            
            # 在 Milvus 中搜索
            search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
            results = self.milvus_collection.search(
                data=[query_embedding],
                anns_field="vector",
                param=search_params,
                limit=limit,
                expr=f'user_id == "{user_id}"'  # 过滤用户
            )
            
            # 获取匹配的记忆ID
            memory_ids = []
            scores = []
            for hits in results:
                for hit in hits:
                    memory_ids.append(hit.id)
                    scores.append(hit.score)
            
            # 从 PostgreSQL 获取完整数据
            memories = []
            if memory_ids:
                async with self.pg_pool.acquire() as conn:
                    rows = await conn.fetch("""
                        SELECT id, content, metadata, created_at
                        FROM memories
                        WHERE id = ANY($1::text[])
                        ORDER BY created_at DESC
                    """, memory_ids)
                    
                    for i, row in enumerate(rows):
                        memories.append({
                            "id": row["id"],
                            "memory": {
                                "content": row["content"],
                                "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
                            },
                            "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                            "score": float(scores[i]) if i < len(scores) else 0.0
                        })
            
            return {
                "success": True,
                "memories": memories,
                "total": len(memories)
            }
            
        except Exception as e:
            logger.error(f"❌ 搜索记忆失败: {e}")
            return {
                "success": False,
                "memories": [],
                "total": 0,
                "error": str(e)
            }
    
    async def get_all_memories(
        self,
        user_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取用户的所有记忆
        
        Args:
            user_id: 用户ID
            limit: 返回数量
            
        Returns:
            记忆列表
        """
        await self._ensure_initialized()
        try:
            async with self.pg_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, content, metadata, created_at
                    FROM memories
                    WHERE user_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                """, user_id, limit)
                
                memories = []
                for row in rows:
                    memories.append({
                        "id": row["id"],
                        "memory": {
                            "content": row["content"],
                            "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
                        },
                        "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
                    })
                
                return memories
                
        except Exception as e:
            logger.error(f"❌ 获取记忆失败: {e}")
            return []
    
    async def get_context(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> str:
        """
        获取用户上下文（用于提示词增强）
        
        Args:
            user_id: 用户ID
            query: 查询文本
            limit: 返回数量
            
        Returns:
            格式化的上下文字符串
        """
        await self._ensure_initialized()
        try:
            result = await self.search_memories(user_id, query, limit)
            
            if not result.get("success") or not result.get("memories"):
                return ""
            
            context_parts = ["=== 相关历史记忆 ==="]
            for i, memory in enumerate(result["memories"], 1):
                content = memory.get("memory", {}).get("content", "")
                context_parts.append(f"{i}. {content[:200]}...")
            
            context_parts.append("=== 请基于以上历史记忆，提供更相关的回答 ===")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"❌ 获取上下文失败: {e}")
            return ""
    
    async def delete_memory(
        self,
        user_id: str,
        memory_id: str
    ) -> Dict[str, Any]:
        """
        删除记忆
        
        Args:
            user_id: 用户ID
            memory_id: 记忆ID
            
        Returns:
            删除结果
        """
        await self._ensure_initialized()
        try:
            # 从 PostgreSQL 删除
            async with self.pg_pool.acquire() as conn:
                result = await conn.execute("""
                    DELETE FROM memories
                    WHERE id = $1 AND user_id = $2
                """, memory_id, user_id)
            
            # 从 Milvus 删除
            self.milvus_collection.delete(expr=f'id == "{memory_id}"')
            
            return {
                "success": True,
                "message": "记忆删除成功"
            }
            
        except Exception as e:
            logger.error(f"❌ 删除记忆失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

