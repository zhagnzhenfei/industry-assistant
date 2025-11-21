"""
Milvus核心服务类
提供专业的向量存储和检索功能
"""

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import numpy as np
from pymilvus import (
    connections, Collection, utility, FieldSchema, CollectionSchema, DataType,
    SearchResult, SearchFuture
)

from .models import (
    DocumentChunk, SearchResult, SearchRequest, SearchResponse,
    CollectionConfig, IndexType, MetricType,
    DEFAULT_COLLECTION_CONFIGS, DEFAULT_SEARCH_PARAMS,
    PERFORMANCE_BASELINES, ERROR_CODES, LOGGING_CONFIG
)

# 配置日志
logging.basicConfig(**LOGGING_CONFIG)
logger = logging.getLogger(__name__)


class MilvusService:
    """Milvus向量存储核心服务"""

    def __init__(self,
                 host: str = "127.0.0.1",
                 port: str = "19530",
                 user: str = "",
                 password: str = "",
                 db_name: str = "default",
                 consistency_level: str = "Strong"):
        """
        初始化Milvus服务

        Args:
            host: Milvus服务器地址
            port: Milvus服务器端口
            user: 用户名（可选）
            password: 密码（可选）
            db_name: 数据库名称
            consistency_level: 一致性级别
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db_name = db_name
        self.consistency_level = consistency_level
        self.collections = {}  # 缓存集合实例
        self._connected = False

    async def connect(self) -> bool:
        """连接到Milvus服务器"""
        try:
            logger.info(f"正在连接到Milvus服务器: {self.host}:{self.port}")

            # 构建连接参数
            connect_params = {
                "alias": "default",
                "host": self.host,
                "port": self.port,
                "user": self.user,
                "password": self.password,
                "db_name": self.db_name,
                "consistency_level": self.consistency_level
            }

            # 移除空值参数
            connect_params = {k: v for k, v in connect_params.items() if v}

            # 建立连接
            connections.connect(**connect_params)

            # 验证连接
            server_version = utility.get_server_version()
            logger.info(f"✅ 成功连接到Milvus，版本: {server_version}")

            self._connected = True
            return True

        except Exception as e:
            logger.error(f"❌ 连接Milvus失败: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> bool:
        """断开与Milvus服务器的连接"""
        try:
            logger.info("正在断开与Milvus的连接")
            connections.disconnect("default")
            self._connected = False
            self.collections.clear()
            logger.info("✅ 已断开与Milvus的连接")
            return True
        except Exception as e:
            logger.error(f"❌ 断开连接失败: {e}")
            return False

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected

    async def create_collection(self,
                              collection_name: str,
                              config: Optional[CollectionConfig] = None) -> bool:
        """创建集合"""
        try:
            logger.info(f"正在创建集合: {collection_name}")

            # 使用默认配置或自定义配置
            if config is None:
                config = DEFAULT_COLLECTION_CONFIGS.get("documents")
                if config is None:
                    # 如果没有找到默认配置，创建基础配置
                    config = CollectionConfig(collection_name=collection_name)

            # 如果集合已存在，先删除
            if utility.has_collection(collection_name):
                logger.warning(f"集合 {collection_name} 已存在，将先删除")
                utility.drop_collection(collection_name)

            # 创建字段schema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=config.vector_dim),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=config.max_length),
                FieldSchema(name="content_ltks", dtype=DataType.VARCHAR, max_length=config.max_length),
                FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="doc_name", dtype=DataType.VARCHAR, max_length=500),
                FieldSchema(name="kb_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=200),
                FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="timestamp", dtype=DataType.INT64),
                FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=200),
                FieldSchema(name="keywords", dtype=DataType.VARCHAR, max_length=1000),
                FieldSchema(name="metadata", dtype=DataType.JSON)
            ]

            # 创建集合schema
            schema = CollectionSchema(
                fields=fields,
                description=config.description,
                enable_dynamic_field=config.enable_dynamic_field
            )

            # 创建集合
            collection = Collection(name=collection_name, schema=schema)

            # 缓存集合实例
            self.collections[collection_name] = collection

            logger.info(f"✅ 成功创建集合: {collection_name}")
            logger.info(f"📋 集合描述: {config.description}")
            logger.info(f"📏 向量维度: {config.vector_dim}")
            logger.info(f"📊 是否支持动态字段: {config.enable_dynamic_field}")

            return True

        except Exception as e:
            logger.error(f"❌ 创建集合失败: {e}")
            return False

    async def create_index(self,
                         collection_name: str,
                         field_name: str = "vector",
                         index_params: Optional[Dict[str, Any]] = None) -> bool:
        """创建索引"""
        try:
            logger.info(f"正在创建索引: {collection_name}.{field_name}")

            # 获取集合
            collection = self._get_collection(collection_name)
            if not collection:
                return False

            # 默认索引参数
            if index_params is None:
                if field_name == "vector":
                    index_params = {
                        "index_type": "HNSW",
                        "metric_type": "COSINE",
                        "params": {"M": 16, "efConstruction": 200}
                    }
                else:
                    # 非向量字段使用排序索引
                    index_params = {
                        "index_type": "STL_SORT",
                        "metric_type": "L2"
                    }

            # 创建索引
            start_time = time.time()
            collection.create_index(field_name, index_params)
            build_time = time.time() - start_time

            logger.info(f"✅ 成功创建索引: {collection_name}.{field_name}")
            logger.info(f"🔧 索引类型: {index_params.get('index_type', 'unknown')}")
            logger.info(f"📏 相似度度量: {index_params.get('metric_type', 'unknown')}")
            logger.info(f"⏱️  构建耗时: {build_time:.2f}秒")

            return True

        except Exception as e:
            logger.error(f"❌ 创建索引失败: {e}")
            return False

    async def insert_data(self,
                         collection_name: str,
                         data: List[DocumentChunk],
                         batch_size: int = 1000) -> bool:
        """插入数据"""
        try:
            logger.info(f"正在插入数据到集合: {collection_name} (共{len(data)}条)")

            # 获取集合
            collection = self._get_collection(collection_name)
            if not collection:
                return False

            # 准备数据
            total_records = len(data)
            start_time = time.time()
            success_count = 0
            failed_count = 0

            # 批量插入
            for i in range(0, total_records, batch_size):
                batch_end = min(i + batch_size, total_records)
                batch_data = data[i:batch_end]

                try:
                    # 准备实体数据（注意：auto_id=True的字段不需要在entities中提供）
                    entities = [
                        [chunk.vector for chunk in batch_data],
                        [chunk.content for chunk in batch_data],
                        [chunk.content_ltks for chunk in batch_data],
                        [chunk.doc_id for chunk in batch_data],
                        [chunk.doc_name for chunk in batch_data],
                        [chunk.kb_id for chunk in batch_data],
                        [chunk.chunk_id for chunk in batch_data],
                        [chunk.category for chunk in batch_data],
                        [chunk.timestamp for chunk in batch_data],
                        [chunk.source for chunk in batch_data],
                        [chunk.keywords for chunk in batch_data],
                        [chunk.metadata for chunk in batch_data]
                    ]

                    # 插入数据
                    collection.insert(entities)
                    success_count += len(batch_data)

                    if (i + batch_size) % 5000 == 0 or batch_end == total_records:
                        logger.info(f"  已插入 {batch_end}/{total_records} 条")

                except Exception as e:
                    logger.error(f"批量插入失败 (批次 {i}-{batch_end}): {e}")
                    failed_count += len(batch_data)
                    # 可以继续处理下一个批次，而不是完全失败

            # 不执行flush操作，避免channel通信错误
            # Milvus会自动在后台处理数据持久化
            # collection.flush()

            total_time = time.time() - start_time
            qps = success_count / total_time if total_time > 0 else 0

            logger.info(f"✅ 数据插入完成")
            logger.info(f"📊 总记录数: {total_records}")
            logger.info(f"✅ 成功: {success_count}")
            logger.info(f"❌ 失败: {failed_count}")
            logger.info(f"⏱️  总耗时: {total_time:.2f}秒")
            logger.info(f"🚀 QPS: {qps:.0f}")
            logger.info("💡 数据已插入成功，Milvus将在后台自动持久化")

            return failed_count == 0  # 只有在没有失败时才返回True

        except Exception as e:
            logger.error(f"❌ 数据插入失败: {e}")
            return False

    async def search(self,
                    collection_name: str,
                    query_vector: List[float],
                    top_k: int = 10,
                    filter_expr: Optional[str] = None,
                    search_params: Optional[Dict[str, Any]] = None,
                    output_fields: Optional[List[str]] = None) -> List[SearchResult]:
        """向量搜索"""
        try:
            logger.info(f"正在搜索集合: {collection_name} (Top-K: {top_k})")

            # 获取集合
            collection = self._get_collection(collection_name)
            if not collection:
                return []

            # 确保集合已加载（无论集合是否为空，搜索前都需要加载集合到内存）
            try:
                # 检查集合加载状态
                from pymilvus import utility
                load_state = utility.load_state(collection_name)
                
                # 处理枚举和字符串两种格式
                state_name = load_state.name if hasattr(load_state, 'name') else str(load_state)
                
                # LoadState.Loaded 表示已加载，LoadState.Loading 表示正在加载
                # LoadState.NotLoad 表示未加载，LoadState.NotExist 表示不存在
                if state_name not in ['Loaded', 'Loading']:
                    logger.info(f"集合 {collection_name} 未加载，正在加载到内存...")
                    collection.load()
                    
                    # 等待加载完成（最多等待5秒）
                    max_wait = 5
                    wait_time = 0
                    while wait_time < max_wait:
                        current_state = utility.load_state(collection_name)
                        current_state_name = current_state.name if hasattr(current_state, 'name') else str(current_state)
                        if current_state_name == 'Loaded':
                            logger.info(f"✅ 集合 {collection_name} 加载完成")
                            break
                        time.sleep(0.2)
                        wait_time += 0.2
                    
                    if wait_time >= max_wait:
                        logger.warning(f"⚠️ 集合 {collection_name} 加载超时，但继续尝试搜索")
                else:
                    logger.debug(f"集合 {collection_name} 已加载，状态: {state_name}")
            except Exception as e:
                logger.warning(f"检查加载状态失败，尝试直接加载: {e}")
                try:
                    collection.load()
                    # 简短等待确保加载开始
                    time.sleep(0.5)
                    logger.info(f"✅ 集合 {collection_name} 已触发加载")
                except Exception as load_error:
                    logger.error(f"❌ 无法加载集合 {collection_name}: {load_error}")
                    raise Exception(f"集合 {collection_name} 加载失败: {load_error}")

            # 默认搜索参数
            if search_params is None:
                search_params = {
                    "metric_type": "COSINE",
                    "params": {"ef": 64}
                }

            # 默认输出字段
            if output_fields is None:
                output_fields = ["content", "doc_id", "doc_name", "category", "confidence", "source", "metadata", "chunk_id"]

            # 执行搜索
            start_time = time.time()

            results = collection.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                expr=filter_expr,
                output_fields=output_fields,
                consistency_level="Strong"
            )

            search_time = time.time() - start_time

            # 转换结果格式
            search_results = []

            if results and len(results) > 0:
                for hit in results[0]:
                    # 优先使用chunk_id作为唯一标识，如果没有则使用Milvus内部ID
                    chunk_id = hit.entity.get("chunk_id", "")
                    unique_id = chunk_id if chunk_id else str(hit.id)

                    result = SearchResult(
                        id=unique_id,
                        score=hit.score,
                        content=hit.entity.get("content", ""),
                        doc_id=hit.entity.get("doc_id", ""),
                        doc_name=hit.entity.get("doc_name", ""),
                        category=hit.entity.get("category", ""),
                        source=hit.entity.get("source", ""),
                        chunk_id=hit.entity.get("chunk_id", ""),
                        metadata=hit.entity.get("metadata", {})
                    )
                    search_results.append(result)

            logger.info(f"✅ 搜索完成，返回 {len(search_results)} 条结果")
            logger.info(f"⏱️  搜索耗时: {search_time:.3f}秒")

            return search_results

        except Exception as e:
            logger.error(f"❌ 搜索失败: {e}")
            # 抛出异常而不是返回空列表，这样上层可以正确处理错误
            raise Exception(f"Milvus搜索失败: {str(e)}")

    async def query(self,
                   collection_name: str,
                   filter_expr: str,
                   output_fields: Optional[List[str]] = None,
                   limit: int = 100) -> List[Dict[str, Any]]:
        """条件查询"""
        try:
            logger.info(f"正在查询集合: {collection_name} (过滤: {filter_expr})")

            # 获取集合
            collection = self._get_collection(collection_name)
            if not collection:
                return []

            # 确保集合已加载（只在未加载时才加载，避免重复加载）
            if not collection.is_empty:
                try:
                    # 检查集合加载状态
                    load_state = utility.load_state(collection_name)
                    if load_state.name not in ['Loaded', 'Loading']:
                        logger.info(f"集合 {collection_name} 未加载，正在加载到内存...")
                        collection.load()
                        logger.info(f"✅ 集合 {collection_name} 加载完成")
                    else:
                        logger.debug(f"集合 {collection_name} 已加载，状态: {load_state.name}")
                except Exception as e:
                    logger.warning(f"检查加载状态失败，尝试直接加载: {e}")
                    collection.load()

            # 默认输出字段
            if output_fields is None:
                output_fields = ["id", "content", "doc_id", "doc_name", "category", "confidence", "timestamp"]

            # 执行查询
            start_time = time.time()

            results = collection.query(
                expr=filter_expr,
                output_fields=output_fields,
                limit=limit
            )

            query_time = time.time() - start_time

            logger.info(f"✅ 查询完成，返回 {len(results)} 条结果")
            logger.info(f"⏱️  查询耗时: {query_time:.3f}秒")

            return results

        except Exception as e:
            logger.error(f"❌ 查询失败: {e}")
            return []

    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """获取集合统计信息"""
        try:
            collection = self._get_collection(collection_name)
            if not collection:
                return {}

            stats = {
                "collection_name": collection_name,
                "num_entities": collection.num_entities,
                "is_empty": collection.is_empty,
                "schema": {
                    "fields": [field.name for field in collection.schema.fields],
                    "description": collection.schema.description,
                    "enable_dynamic_field": collection.schema.enable_dynamic_field
                }
            }

            return stats

        except Exception as e:
            logger.error(f"❌ 获取集合统计信息失败: {e}")
            return {}

    async def delete_collection(self, collection_name: str) -> bool:
        """删除集合"""
        try:
            logger.info(f"正在删除集合: {collection_name}")

            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)

                # 从缓存中移除
                if collection_name in self.collections:
                    del self.collections[collection_name]

                logger.info(f"✅ 成功删除集合: {collection_name}")
                return True
            else:
                logger.warning(f"集合 {collection_name} 不存在")
                return True

        except Exception as e:
            logger.error(f"❌ 删除集合失败: {e}")
            return False

    def _get_collection(self, collection_name: str) -> Optional[Collection]:
        """获取集合实例（带缓存）"""
        try:
            # 检查缓存
            if collection_name in self.collections:
                return self.collections[collection_name]

            # 检查集合是否存在
            if not utility.has_collection(collection_name):
                logger.error(f"集合 {collection_name} 不存在")
                return None

            # 创建集合并缓存
            collection = Collection(name=collection_name)
            self.collections[collection_name] = collection

            return collection

        except Exception as e:
            logger.error(f"获取集合失败: {e}")
            return None

    async def load_collection(self, collection_name: str) -> bool:
        """加载集合到内存"""
        try:
            collection = self._get_collection(collection_name)
            if not collection:
                return False

            if collection.is_empty:
                logger.warning(f"集合 {collection_name} 为空，无需加载")
                return True

            collection.load()
            logger.info(f"✅ 成功加载集合: {collection_name}")
            return True

        except Exception as e:
            logger.error(f"❌ 加载集合失败: {e}")
            return False

    async def release_collection(self, collection_name: str) -> bool:
        """释放集合内存"""
        try:
            collection = self._get_collection(collection_name)
            if not collection:
                return False

            collection.release()
            logger.info(f"✅ 成功释放集合: {collection_name}")
            return True

        except Exception as e:
            logger.error(f"❌ 释放集合失败: {e}")
            return False

    async def get_server_version(self) -> str:
        """获取服务器版本"""
        try:
            return utility.get_server_version()
        except Exception as e:
            logger.error(f"获取服务器版本失败: {e}")
            return "unknown"

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 检查连接状态
            if not self.is_connected():
                return {"status": "unhealthy", "error": "Not connected"}

            # 检查服务器状态
            server_version = await self.get_server_version()

            # 检查集合状态
            collection_stats = {}
            for collection_name in self.collections.keys():
                stats = await self.get_collection_stats(collection_name)
                collection_stats[collection_name] = stats

            return {
                "status": "healthy",
                "server_version": server_version,
                "connected": True,
                "collections": collection_stats,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    # ===== 同步方法包装器 =====
    def create_collection_sync(self, collection_name: str, config: Optional[CollectionConfig] = None) -> bool:
        """同步创建集合 - 完全同步实现，避免事件循环冲突"""
        try:
            logger.info(f"🚀 开始同步创建/检查集合: {collection_name}")

            # 使用默认配置或自定义配置
            if config is None:
                config = DEFAULT_COLLECTION_CONFIGS.get("documents")
                if config is None:
                    # 如果没有找到默认配置，创建基础配置
                    config = CollectionConfig(collection_name=collection_name)
                    logger.info(f"📝 创建了新的配置: {collection_name}")
                else:
                    logger.info(f"📝 使用默认配置: {collection_name}")

            # 如果集合已存在，需要检查schema并可能重建（因为我们要移除confidence字段）
            if utility.has_collection(collection_name):
                logger.warning(f"集合 {collection_name} 已存在，检查schema...")
                collection = Collection(collection_name)
                field_names = [field.name for field in collection.schema.fields]
                logger.info(f"🔍 现有集合字段: {field_names}")
                logger.info(f"🔍 现有集合字段数量: {len(field_names)}")

                # 强制删除任何包含confidence字段的集合
                if "confidence" in field_names:
                    logger.warning(f"🗑️ 集合 {collection_name} 包含已废弃的confidence字段，将强制删除重建")
                    try:
                        utility.drop_collection(collection_name)
                        logger.info(f"✅ 成功删除旧集合: {collection_name}")
                    except Exception as e:
                        logger.error(f"❌ 删除集合失败: {e}")
                        return False
                else:
                    # 即使没有confidence字段，也检查字段数量是否正确
                    expected_fields = {"id", "vector", "content", "content_ltks", "doc_id", "doc_name", "kb_id", "chunk_id", "category", "timestamp", "source", "keywords", "metadata"}
                    if set(field_names) != expected_fields:
                        logger.warning(f"🔧 集合 {collection_name} 字段不匹配，预期: {expected_fields}, 实际: {set(field_names)}，将重建")
                        try:
                            utility.drop_collection(collection_name)
                            logger.info(f"✅ 成功删除不匹配的集合: {collection_name}")
                        except Exception as e:
                            logger.error(f"❌ 删除集合失败: {e}")
                            return False
                    else:
                        logger.info(f"✅ 集合 {collection_name} schema正确，跳过创建")
                        return True

            # 创建字段schema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=config.vector_dim),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=config.max_length),
                FieldSchema(name="content_ltks", dtype=DataType.VARCHAR, max_length=config.max_length),
                FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="doc_name", dtype=DataType.VARCHAR, max_length=500),
                FieldSchema(name="kb_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=200),
                FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="timestamp", dtype=DataType.INT64),
                FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=500),
                FieldSchema(name="keywords", dtype=DataType.VARCHAR, max_length=1000),
                FieldSchema(name="metadata", dtype=DataType.JSON)
            ]

            field_names = [field.name for field in fields]
            logger.info(f"🔍 新建集合schema字段: {field_names}")
            logger.info(f"🔍 新建集合字段数量: {len(field_names)}")

            # 创建schema
            schema = CollectionSchema(
                fields=fields,
                description=config.description,
                enable_dynamic_field=config.enable_dynamic_field
            )

            # 创建集合
            collection = Collection(name=collection_name, schema=schema)

            logger.info(f"✅ 成功同步创建集合: {collection_name}")
            logger.info(f"📋 集合描述: {config.description}")
            logger.info(f"📏 向量维度: {config.vector_dim}")
            logger.info(f"📊 是否支持动态字段: {config.enable_dynamic_field}")

            return True

        except Exception as e:
            logger.error(f"❌ 同步创建集合失败: {e}")
            return False

    def create_index_sync(self, collection_name: str, field_name: str = "vector", index_params: Optional[Dict] = None) -> bool:
        """同步创建索引 - 完全同步实现，避免事件循环冲突"""
        try:
            logger.info(f"正在同步创建索引: {collection_name}.{field_name}")

            # 获取集合
            collection = Collection(name=collection_name)

            # 检查索引是否已存在
            if collection.has_index():
                logger.info(f"集合 {collection_name} 的索引已存在，跳过创建")
                return True

            # 默认索引参数
            if index_params is None:
                if field_name == "vector":
                    index_params = {
                        "index_type": "HNSW",
                        "metric_type": "COSINE",
                        "params": {"M": 16, "efConstruction": 200}
                    }
                else:
                    # 非向量字段使用排序索引
                    index_params = {
                        "index_type": "STL_SORT",
                        "metric_type": "L2"
                    }

            # 创建索引
            start_time = time.time()
            collection.create_index(field_name, index_params)
            build_time = time.time() - start_time

            logger.info(f"✅ 成功同步创建索引: {collection_name}.{field_name}")
            logger.info(f"🔧 索引类型: {index_params.get('index_type', 'unknown')}")
            logger.info(f"📏 相似度度量: {index_params.get('metric_type', 'unknown')}")
            logger.info(f"⏱️  构建耗时: {build_time:.2f}秒")

            return True

        except Exception as e:
            logger.error(f"❌ 同步创建索引失败: {e}")
            return False

    def connect_sync(self) -> bool:
        """同步连接到Milvus服务器"""
        try:
            logger.info(f"正在同步连接到Milvus服务器: {self.host}:{self.port}")

            # 构建连接参数
            connect_params = {
                "alias": "default",
                "host": self.host,
                "port": self.port,
                "user": self.user,
                "password": self.password,
                "db_name": self.db_name,
                "consistency_level": self.consistency_level
            }

            # 移除空值参数
            connect_params = {k: v for k, v in connect_params.items() if v}

            # 建立连接 - 同步方式
            connections.connect(**connect_params)

            # 验证连接
            server_version = utility.get_server_version()
            logger.info(f"✅ 成功同步连接到Milvus，版本: {server_version}")

            self._connected = True
            return True

        except Exception as e:
            logger.error(f"❌ 同步连接Milvus失败: {e}")
            self._connected = False
            return False

    def insert_data_sync(self, collection_name: str, data: List[DocumentChunk], batch_size: int = 1000) -> bool:
        """同步插入数据"""
        try:
            # 直接同步执行插入操作，避免事件循环冲突
            if not self._connected:
                logger.error("Milvus未连接")
                return False

            if not data:
                logger.warning("没有数据需要插入")
                return True

            # 获取集合
            collection = Collection(name=collection_name)

            # 注意：插入数据时不需要加载集合，load()只用于查询/搜索操作
            # 插入操作可以直接在未加载的集合上执行

            # 批量插入数据
            total_inserted = 0
            for i in range(0, len(data), batch_size):
                batch_end = min(i + batch_size, len(data))
                batch_data = data[i:batch_end]

                try:
                    # 打印集合schema信息
                    schema_fields = [field.name for field in collection.schema.fields]
                    logger.info(f"🔍 集合schema字段: {schema_fields}")
                    logger.info(f"🔍 集合schema字段数量: {len(schema_fields)}")

                    # 准备实体数据（注意：auto_id=True的字段不需要在entities中提供）
                    entities = [
                        [chunk.vector for chunk in batch_data],
                        [chunk.content for chunk in batch_data],
                        [chunk.content_ltks for chunk in batch_data],
                        [chunk.doc_id for chunk in batch_data],
                        [chunk.doc_name for chunk in batch_data],
                        [chunk.kb_id for chunk in batch_data],
                        [chunk.chunk_id for chunk in batch_data],
                        [chunk.category for chunk in batch_data],
                        [chunk.timestamp for chunk in batch_data],
                        [chunk.source for chunk in batch_data],
                        [chunk.keywords for chunk in batch_data],
                        [chunk.metadata for chunk in batch_data]
                    ]

                    logger.info(f"🔍 插入数据字段数量: {len(entities)}")
                    logger.info(f"🔍 插入数据字段: ['vector', 'content', 'content_ltks', 'doc_id', 'doc_name', 'kb_id', 'chunk_id', 'category', 'timestamp', 'source', 'keywords', 'metadata']")

                    # 插入数据
                    collection.insert(entities)
                    total_inserted += len(batch_data)

                    logger.info(f"已插入 {total_inserted}/{len(data)} 条记录到集合 {collection_name}")

                except Exception as batch_error:
                    logger.error(f"批量插入失败 (批次 {i//batch_size + 1}): {batch_error}")
                    return False

            # 不执行flush操作，避免channel通信错误
            # Milvus会自动在后台处理数据持久化（通常在几秒到几分钟内完成）
            # 数据在插入后立即可用于查询，无需等待flush完成
            logger.info(f"✅ 同步插入完成，总共插入 {total_inserted} 条记录到集合 {collection_name}")
            logger.info("💡 数据已插入成功，Milvus将在后台自动持久化")
            return True

        except Exception as e:
            logger.error(f"同步插入数据失败: {e}")
            return False

    def delete_data_sync(self, collection_name: str, filter_expr: str) -> int:
        """同步删除数据"""
        try:
            logger.info(f"正在同步删除集合 {collection_name} 中匹配条件的数据: {filter_expr}")

            if not self._connected:
                logger.error("Milvus未连接")
                return 0

            # 获取集合
            collection = Collection(name=collection_name)

            # 执行删除操作
            collection.delete(expr=filter_expr)

            # 不执行flush操作，避免channel通信错误
            # Milvus会自动在后台处理数据持久化
            logger.info("⏳ 跳过flush操作，允许Milvus在后台自动持久化删除的数据")

            logger.info(f"✅ 同步删除数据完成，集合: {collection_name}")
            return 1  # 返回删除计数（简化版本）

        except Exception as e:
            logger.error(f"同步删除数据失败: {e}")
            return 0

    def search_sync(self, collection_name: str, query_vector: List[float], top_k: int = 10,
                   filter_expr: Optional[str] = None, search_params: Optional[Dict] = None,
                   output_fields: Optional[List[str]] = None) -> List[SearchResult]:
        """同步搜索"""
        import asyncio
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.search(collection_name, query_vector, top_k, filter_expr, search_params, output_fields))
        except Exception as e:
            logger.error(f"同步搜索失败: {e}")
            return []
        finally:
            if loop is not None:
                loop.close()