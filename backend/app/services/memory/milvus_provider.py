"""
Milvus记忆提供者 - MVP版本

使用Milvus作为单一存储，支持：
1. 短期记忆（基于时间过滤）
2. 长期记忆（全量存储）
3. 语义检索（向量搜索）
4. 简单用户画像（metadata存储）
"""
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .base import IMemoryProvider, ConversationMemory, UserProfile

logger = logging.getLogger(__name__)


class MilvusMemoryProvider(IMemoryProvider):
    """Milvus记忆提供者
    
    Collection设计:
    - conversation_id (VARCHAR, primary_key)
    - user_id (VARCHAR, 支持过滤)
    - vector (FLOAT_VECTOR, 用于语义检索)
    - question (VARCHAR)
    - research_brief (VARCHAR)
    - final_report (VARCHAR)
    - key_findings (VARCHAR, JSON string)
    - quality_score (FLOAT)
    - duration (FLOAT)
    - created_at (VARCHAR, ISO格式)
    - metadata (VARCHAR, JSON string)
    """
    
    def __init__(
        self,
        milvus_host: str = "localhost",
        milvus_port: int = 19530,
        collection_name: str = "research_memory",
        embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        self.host = milvus_host
        self.port = milvus_port
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model_name
        
        self.client = None
        self.collection = None
        self.embedding_model = None
    
    async def initialize(self):
        """初始化Milvus连接和collection"""
        try:
            from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility
            
            # 连接Milvus
            logger.info(f"🔗 连接Milvus: {self.host}:{self.port}")
            connections.connect(
                alias="default",
                host=self.host,
                port=str(self.port)
            )
            logger.info("✅ Milvus连接成功")
            
            # 检查collection是否存在
            if utility.has_collection(self.collection_name):
                logger.info(f"📊 Collection '{self.collection_name}' 已存在，直接使用")
                self.collection = Collection(self.collection_name)
            else:
                logger.info(f"📊 创建新Collection: {self.collection_name}")
                self._create_collection()
            
            # 加载collection到内存
            self.collection.load()
            logger.info(f"✅ Collection已加载到内存")
            
            # 初始化embedding模型
            logger.info(f"🤖 加载Embedding模型: {self.embedding_model_name}")
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            logger.info("✅ Embedding模型加载成功")
            
        except ImportError as e:
            logger.error(f"❌ 缺少必要的库: {e}")
            logger.error("请安装: pip install pymilvus sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"❌ Milvus初始化失败: {e}")
            raise
    
    def _create_collection(self):
        """创建Milvus collection"""
        from pymilvus import Collection, CollectionSchema, FieldSchema, DataType
        
        # 定义schema
        fields = [
            FieldSchema(name="conversation_id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
            FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=50),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=384),  # all-MiniLM-L6-v2的维度
            FieldSchema(name="question", dtype=DataType.VARCHAR, max_length=1000),
            FieldSchema(name="research_brief", dtype=DataType.VARCHAR, max_length=2000),
            FieldSchema(name="final_report", dtype=DataType.VARCHAR, max_length=10000),
            FieldSchema(name="key_findings", dtype=DataType.VARCHAR, max_length=5000),  # JSON string
            FieldSchema(name="quality_score", dtype=DataType.FLOAT),
            FieldSchema(name="duration", dtype=DataType.FLOAT),
            FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=50),
            FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=5000),  # JSON string
        ]
        
        schema = CollectionSchema(
            fields=fields,
            description="Research conversation memory storage"
        )
        
        # 创建collection
        self.collection = Collection(
            name=self.collection_name,
            schema=schema
        )
        
        # 创建索引（用于向量检索）
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "L2",
            "params": {"nlist": 128}
        }
        self.collection.create_index(
            field_name="vector",
            index_params=index_params
        )
        
        logger.info(f"✅ Collection '{self.collection_name}' 创建成功")
    
    async def load_memory(self, user_id: str) -> Dict[str, Any]:
        """加载用户记忆（短期+长期）"""
        try:
            # 并行获取短期记忆和用户画像
            recent_conversations = await self.get_recent_conversations(user_id, limit=5)
            user_profile = await self.get_user_profile(user_id)
            
            return {
                "short_term_memory": [
                    {
                        "question": conv.question,
                        "research_brief": conv.research_brief,
                        "created_at": conv.created_at,
                        "quality_score": conv.quality_score
                    }
                    for conv in recent_conversations
                ],
                "user_profile": user_profile.__dict__ if user_profile else None
            }
        except Exception as e:
            logger.error(f"❌ 加载记忆失败: {e}")
            return {
                "short_term_memory": [],
                "user_profile": None
            }
    
    async def save_conversation(
        self, 
        user_id: str, 
        conversation: ConversationMemory
    ) -> None:
        """保存对话到Milvus"""
        try:
            # 生成embedding
            text = f"{conversation.question} {conversation.research_brief}"
            embedding = self.embedding_model.encode(text).tolist()
            
            # 准备数据
            entities = [
                [conversation.conversation_id],  # conversation_id
                [user_id],  # user_id
                [embedding],  # vector
                [conversation.question[:1000]],  # question (截断)
                [conversation.research_brief[:2000]],  # research_brief (截断)
                [conversation.final_report[:10000]],  # final_report (截断)
                [json.dumps(conversation.key_findings)[:5000]],  # key_findings (JSON)
                [conversation.quality_score],  # quality_score
                [conversation.duration],  # duration
                [conversation.created_at],  # created_at
                [json.dumps(conversation.metadata)[:5000]]  # metadata (JSON)
            ]
            
            # 插入Milvus
            self.collection.insert(entities)
            self.collection.flush()
            
            logger.info(f"✅ 对话已保存到Milvus: {conversation.conversation_id}")
            
            # 更新用户画像
            await self.update_user_profile(user_id, conversation.__dict__)
            
        except Exception as e:
            logger.error(f"❌ 保存对话失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    async def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """从Milvus获取用户画像
        
        MVP实现：基于历史对话统计生成简单画像
        """
        try:
            # 查询用户的所有对话
            expr = f'user_id == "{user_id}"'
            results = self.collection.query(
                expr=expr,
                output_fields=["question", "research_brief", "quality_score", "created_at", "key_findings"],
                limit=100
            )
            
            if not results:
                return None
            
            # 统计数据
            total_researches = len(results)
            avg_quality = sum(r["quality_score"] for r in results) / total_researches if total_researches > 0 else 0
            
            # 提取研究主题（简化：从question中提取关键词）
            all_questions = " ".join(r["question"] for r in results)
            research_interests = self._extract_topics(all_questions)[:10]  # 取前10个主题
            
            # 创建用户画像
            profile = UserProfile(
                user_id=user_id,
                expertise=[],  # MVP版本暂时为空
                research_interests=research_interests,
                preferred_depth="comprehensive",  # MVP版本默认值
                preferred_data_sources=["web"],  # MVP版本默认值
                statistics={
                    "total_researches": total_researches,
                    "avg_quality_score": avg_quality
                },
                created_at=results[0]["created_at"] if results else datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            
            return profile
            
        except Exception as e:
            logger.error(f"❌ 获取用户画像失败: {e}")
            return None
    
    async def update_user_profile(
        self, 
        user_id: str, 
        research_data: Dict[str, Any]
    ) -> None:
        """更新用户画像
        
        MVP实现：画像是动态生成的，无需显式更新
        """
        # MVP版本：画像基于历史数据动态生成，此方法可为空
        pass
    
    async def search_similar_conversations(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """使用Milvus进行语义搜索"""
        try:
            # 生成查询向量
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # 向量搜索
            search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
            results = self.collection.search(
                data=[query_embedding],
                anns_field="vector",
                param=search_params,
                limit=limit,
                expr=f'user_id == "{user_id}"',
                output_fields=["conversation_id", "question", "research_brief", "created_at", "quality_score"]
            )
            
            # 格式化结果
            similar = []
            for hits in results:
                for hit in hits:
                    similar.append({
                        "conversation_id": hit.entity.get("conversation_id"),
                        "question": hit.entity.get("question"),
                        "research_brief": hit.entity.get("research_brief"),
                        "score": hit.distance,
                        "created_at": hit.entity.get("created_at"),
                        "quality_score": hit.entity.get("quality_score")
                    })
            
            return similar
            
        except Exception as e:
            logger.error(f"❌ 语义搜索失败: {e}")
            return []
    
    async def get_recent_conversations(
        self,
        user_id: str,
        limit: int = 5
    ) -> List[ConversationMemory]:
        """获取最近的对话记录"""
        try:
            # 查询最近N天的对话
            days_ago = (datetime.now() - timedelta(days=7)).isoformat()
            
            expr = f'user_id == "{user_id}"'
            results = self.collection.query(
                expr=expr,
                output_fields=[
                    "conversation_id", "question", "research_brief", 
                    "final_report", "key_findings", "quality_score", 
                    "duration", "created_at", "metadata"
                ],
                limit=limit
            )
            
            # 转换为ConversationMemory对象
            conversations = []
            for r in results:
                conv = ConversationMemory(
                    conversation_id=r["conversation_id"],
                    user_id=user_id,
                    question=r["question"],
                    research_brief=r["research_brief"],
                    final_report=r.get("final_report", ""),
                    key_findings=json.loads(r.get("key_findings", "[]")),
                    quality_score=r.get("quality_score", 0.0),
                    duration=r.get("duration", 0.0),
                    created_at=r["created_at"],
                    metadata=json.loads(r.get("metadata", "{}"))
                )
                conversations.append(conv)
            
            # 按创建时间倒序排列
            conversations.sort(key=lambda x: x.created_at, reverse=True)
            
            return conversations[:limit]
            
        except Exception as e:
            logger.error(f"❌ 获取最近对话失败: {e}")
            return []
    
    def _extract_topics(self, text: str) -> List[str]:
        """从文本中提取主题（简化实现）
        
        MVP版本：使用简单的关键词提取
        """
        # TODO: 使用NLP或LLM提取更准确的主题
        # 简化版本：分词+去重+取高频词
        words = text.lower().split()
        word_counts = {}
        for word in words:
            if len(word) > 3:  # 过滤短词
                word_counts[word] = word_counts.get(word, 0) + 1
        
        # 按频率排序
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:10]]

