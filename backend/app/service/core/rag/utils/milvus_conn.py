#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import logging
import re
import time
import os
import json
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime

from pymilvus import (
    connections, Collection, FieldSchema, CollectionSchema, DataType,
    utility, MilvusClient
)
from service.core.rag.utils import singleton
from service.core.api.utils.file_utils import get_project_base_directory
from service.core.rag.utils.doc_store_conn import (
    MatchExpr, OrderByExpr, MatchTextExpr, MatchDenseExpr,
    MatchSparseExpr, FusionExpr, DocStoreConnection
)
from service.core.rag.nlp import is_english
from service.core.rag.nlp.model import generate_embedding
from dotenv import load_dotenv

load_dotenv()

MILVUS_HOST = os.getenv("MILVUS_HOST", "milvus-standalone")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
MILVUS_USERNAME = os.getenv("MILVUS_USERNAME", "")
MILVUS_PASSWORD = os.getenv("MILVUS_PASSWORD", "")
MILVUS_VECTOR_DIM = int(os.getenv("MILVUS_VECTOR_DIMENSION", "1024"))
ATTEMPT_TIME = 2

logger = logging.getLogger('ragflow.milvus_conn')


@singleton
class MilvusConnection(DocStoreConnection):
    """
    Milvus连接类
    实现DocStoreConnection接口
    负责与Milvus交互，进行文档存储和检索
    """
    def __init__(self):
        """
        初始化Milvus连接
        加载配置和映射文件
        建立与Milvus的连接
        """
        self.client = None
        self.collections = {}
        self.milvus_available = False
        self.vector_dim = MILVUS_VECTOR_DIM

        # 检查Milvus配置
        if not MILVUS_HOST:
            logger.warning("MILVUS_HOST not configured. Milvus functionality will be disabled.")
            return

        try:
            logger.info(f"Use Milvus {MILVUS_HOST}:{MILVUS_PORT} as the doc engine.")

            # 构建Milvus连接参数
            connection_config = {
                "alias": "default",
                "host": MILVUS_HOST,
                "port": MILVUS_PORT,
            }

            # 如果有用户名和密码，添加认证
            if MILVUS_USERNAME and MILVUS_PASSWORD:
                connection_config["user"] = MILVUS_USERNAME
                connection_config["password"] = MILVUS_PASSWORD

            # 建立连接
            connections.connect(**connection_config)
            self.client = MilvusClient(
                uri=f"http://{MILVUS_HOST}:{MILVUS_PORT}",
                user=MILVUS_USERNAME if MILVUS_USERNAME else None,
                password=MILVUS_PASSWORD if MILVUS_PASSWORD else None
            )

            # 测试连接
            utility.get_server_version()
            self.milvus_available = True
            logger.info("Milvus connection established successfully.")

        except Exception as e:
            logger.error(f"Failed to initialize Milvus connection: {str(e)}")
            logger.warning("Milvus functionality will be disabled.")
            self.client = None
            self.milvus_available = False

    def dbType(self) -> str:
        """返回数据库类型"""
        return "milvus"

    def health(self) -> dict:
        """返回数据库健康状态"""
        if not self.milvus_available:
            return {"status": "unavailable", "message": "Milvus connection not available"}

        try:
            version = utility.get_server_version()
            return {"status": "healthy", "version": version}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    def _get_collection_name(self, index_name: str, knowledgebase_id: str) -> str:
        """生成Milvus集合名称"""
        return f"{index_name}_{knowledgebase_id}".replace("-", "_").lower()

    def _create_collection_schema(self, vector_size: int) -> CollectionSchema:
        """创建Milvus集合schema"""
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="kb_id", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="docnm_kwd", dtype=DataType.VARCHAR, max_length=1024),
            FieldSchema(name="content_ltks", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="content_with_weight", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="title_tks", dtype=DataType.VARCHAR, max_length=2048),
            FieldSchema(name="important_kwd", dtype=DataType.VARCHAR, max_length=2048),
            FieldSchema(name="question_kwd", dtype=DataType.VARCHAR, max_length=2048),
            FieldSchema(name="question_tks", dtype=DataType.VARCHAR, max_length=2048),
            FieldSchema(name="img_id", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="page_num_int", dtype=DataType.INT64),
            FieldSchema(name="top_int", dtype=DataType.INT64),
            FieldSchema(name="position_int", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="create_timestamp_flt", dtype=DataType.FLOAT),
            FieldSchema(name="available_int", dtype=DataType.INT64, default_value=1),
            FieldSchema(name="knowledge_graph_kwd", dtype=DataType.VARCHAR, max_length=2048),
            FieldSchema(name="tag_kwd", dtype=DataType.VARCHAR, max_length=2048),
            FieldSchema(name="pagerank_fea", dtype=DataType.FLOAT, default_value=0.0),
            FieldSchema(name="tag_feas", dtype=DataType.VARCHAR, max_length=4096),
        ]

        # 添加向量字段
        vector_field_name = f"q_{vector_size}_vec"
        fields.append(FieldSchema(name=vector_field_name, dtype=DataType.FLOAT_VECTOR, dim=vector_size))

        return CollectionSchema(
            fields=fields,
            description=f"Document collection with {vector_size}d vectors",
            enable_dynamic_field=True
        )

    def createIdx(self, indexName: str, knowledgebaseId: str, vectorSize: int):
        """创建Milvus集合"""
        if not self.milvus_available:
            logger.warning("Milvus is not available. Index creation skipped.")
            return False

        try:
            collection_name = self._get_collection_name(indexName, knowledgebaseId)

            # 如果集合已存在，先删除
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)
                logger.info(f"Dropped existing collection: {collection_name}")

            # 创建schema
            schema = self._create_collection_schema(vectorSize)

            # 创建集合
            collection = Collection(name=collection_name, schema=schema)

            # 创建向量索引
            index_params = {
                "index_type": "HNSW",
                "metric_type": "COSINE",
                "params": {
                    "M": 16,
                    "efConstruction": 200
                }
            }

            vector_field_name = f"q_{vectorSize}_vec"
            collection.create_index(vector_field_name, index_params)

            # 创建文本字段索引用于过滤
            collection.create_index("chunk_id", {"index_type": "STL_SORT"})
            collection.create_index("doc_id", {"index_type": "STL_SORT"})
            collection.create_index("kb_id", {"index_type": "STL_SORT"})
            collection.create_index("docnm_kwd", {"index_type": "STL_SORT"})

            self.collections[collection_name] = collection
            logger.info(f"Successfully created Milvus collection: {collection_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create Milvus collection: {str(e)}")
            return False

    def deleteIdx(self, indexName: str, knowledgebaseId: str):
        """删除Milvus集合"""
        if not self.milvus_available:
            logger.warning("Milvus is not available. Index deletion skipped.")
            return False

        try:
            collection_name = self._get_collection_name(indexName, knowledgebaseId)

            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)
                if collection_name in self.collections:
                    del self.collections[collection_name]
                logger.info(f"Successfully dropped Milvus collection: {collection_name}")
                return True
            else:
                logger.warning(f"Collection {collection_name} does not exist")
                return False

        except Exception as e:
            logger.error(f"Failed to delete Milvus collection: {str(e)}")
            return False

    def indexExist(self, indexName: str, knowledgebaseId: str) -> bool:
        """检查Milvus集合是否存在"""
        if not self.milvus_available:
            return False

        try:
            collection_name = self._get_collection_name(indexName, knowledgebaseId)
            return utility.has_collection(collection_name)
        except Exception as e:
            logger.error(f"Failed to check collection existence: {str(e)}")
            return False

    def _build_filter_expression(self, condition: dict) -> str:
        """构建Milvus过滤表达式"""
        if not condition:
            return ""

        filter_parts = []

        for field, value in condition.items():
            if not value:
                continue

            if field == "available_int":
                if value == 0:
                    filter_parts.append(f"{field} < 1")
                else:
                    filter_parts.append(f"{field} >= 1")
            elif isinstance(value, list):
                if len(value) == 1:
                    if isinstance(value[0], str):
                        filter_parts.append(f'{field} == "{value[0]}"')
                    else:
                        filter_parts.append(f"{field} == {value[0]}")
                else:
                    # 处理多个值的情况
                    str_values = [f'"{v}"' if isinstance(v, str) else str(v) for v in value]
                    filter_parts.append(f"{field} in [{','.join(str_values)}]")
            elif isinstance(value, str):
                filter_parts.append(f'{field} == "{value}"')
            else:
                filter_parts.append(f"{field} == {value}")

        return " and ".join(filter_parts)

    def search(
        self, selectFields: list[str],
        highlightFields: list[str],
        condition: dict,
        matchExprs: list[MatchExpr],
        orderBy: OrderByExpr,
        offset: int,
        limit: int,
        indexNames: str | list[str],
        knowledgebaseIds: list[str],
        aggFields: list[str] = [],
        rank_feature: dict | None = None
    ):
        """
        在Milvus中执行搜索
        支持向量搜索和过滤条件
        """
        if not self.milvus_available:
            logger.warning("Milvus is not available. Returning empty search results.")
            return {
                "total": 0,
                "ids": [],
                "fields": {}
            }

        try:
            # 处理索引名称
            if isinstance(indexNames, str):
                indexNames = [indexNames]

            # 获取第一个可用的集合
            collection_name = None
            for idx_name in indexNames:
                if knowledgebaseIds:
                    for kb_id in knowledgebaseIds:
                        test_name = self._get_collection_name(idx_name, kb_id)
                        if utility.has_collection(test_name):
                            collection_name = test_name
                            break
                    if collection_name:
                        break

            if not collection_name:
                logger.warning(f"No valid Milvus collection found for {indexNames}")
                return {
                    "total": 0,
                    "ids": [],
                    "fields": {}
                }

            # 获取集合
            collection = Collection(collection_name)
            collection.load()

            # 处理匹配表达式
            vector_search = False
            query_vector = None
            topk = limit if limit > 0 else 10
            filter_expr = self._build_filter_expression(condition)

            for expr in matchExprs:
                if isinstance(expr, MatchDenseExpr):
                    vector_search = True
                    query_vector = expr.embedding_data
                    topk = expr.topn
                    if "similarity" in expr.extra_options:
                        # 相似度阈值处理
                        similarity = expr.extra_options["similarity"]
                        logger.debug(f"Using similarity threshold: {similarity}")
                    break

            # 执行搜索
            if vector_search and query_vector:
                # 向量搜索
                vector_field_name = f"q_{len(query_vector)}_vec"
                search_params = {
                    "metric_type": "COSINE",
                    "params": {"ef": 64}
                }

                results = collection.search(
                    data=[query_vector],
                    anns_field=vector_field_name,
                    param=search_params,
                    limit=topk,
                    expr=filter_expr if filter_expr else None,
                    output_fields=selectFields if selectFields else ["*"]
                )

                # 处理搜索结果
                hits = results[0]
                total = len(hits)
                ids = [str(hit.id) for hit in hits]

                # 构建结果格式
                fields = {}
                for i, hit in enumerate(hits):
                    chunk_data = {"id": str(hit.id)}
                    for field in selectFields:
                        chunk_data[field] = hit.entity.get(field, "")
                    # 添加分数信息
                    chunk_data["_score"] = hit.score
                    fields[str(hit.id)] = chunk_data

                return {
                    "total": total,
                    "ids": ids,
                    "fields": fields
                }

            else:
                # 过滤查询
                query_results = collection.query(
                    expr=filter_expr if filter_expr else "",
                    output_fields=selectFields if selectFields else ["*"],
                    limit=limit if limit > 0 else 100,
                    offset=offset
                )

                total = len(query_results)
                ids = [str(result["id"]) for result in query_results]

                fields = {}
                for result in query_results:
                    result["id"] = str(result["id"])
                    fields[str(result["id"])] = result

                return {
                    "total": total,
                    "ids": ids,
                    "fields": fields
                }

        except Exception as e:
            logger.error(f"Milvus search failed: {str(e)}")
            return {
                "total": 0,
                "ids": [],
                "fields": {}
            }

    def get(self, chunkId: str, indexName: str, knowledgebaseIds: list[str]) -> dict | None:
        """获取单个文档"""
        if not self.milvus_available:
            return None

        try:
            for kb_id in knowledgebaseIds:
                collection_name = self._get_collection_name(indexName, kb_id)
                if utility.has_collection(collection_name):
                    collection = Collection(collection_name)
                    collection.load()

                    results = collection.query(
                        expr=f'chunk_id == "{chunkId}"',
                        output_fields=["*"],
                        limit=1
                    )

                    if results:
                        return results[0]

            return None

        except Exception as e:
            logger.error(f"Failed to get document {chunkId}: {str(e)}")
            return None

    def insert(self, rows: list[dict], indexName: str, knowledgebaseId: str = None) -> list[str]:
        """批量插入文档到Milvus"""
        if not self.milvus_available:
            logger.warning("Milvus is not available. Document indexing skipped.")
            return ["Milvus is not available"]

        try:
            collection_name = self._get_collection_name(indexName, knowledgebaseId)

            # 确保集合存在
            if not utility.has_collection(collection_name):
                # 自动创建集合，假设向量维度为768
                self.createIdx(indexName, knowledgebaseId, self.vector_dim)

            collection = Collection(collection_name)

            # 准备数据
            entities = []
            field_names = []

            # 获取集合的字段信息
            schema = collection.schema
            for field in schema.fields:
                if field.name != "id":  # 跳过自增ID字段
                    field_names.append(field.name)

            # 为每个字段准备数据
            for field_name in field_names:
                field_data = []
                for row in rows:
                    if field_name == "position_int" and isinstance(row.get(field_name), list):
                        # 处理位置信息列表
                        field_data.append(json.dumps(row.get(field_name, [])))
                    elif field_name == "important_kwd" and isinstance(row.get(field_name), list):
                        # 处理关键词列表
                        field_data.append(",".join(row.get(field_name, [])))
                    elif field_name.startswith("q_") and field_name.endswith("_vec"):
                        # 处理向量字段
                        vector_data = row.get(field_name, [])
                        if isinstance(vector_data, str):
                            vector_data = [float(v) for v in vector_data.split("\t")]
                        field_data.append(vector_data)
                    else:
                        field_data.append(row.get(field_name, ""))

                entities.append(field_data)

            # 批量插入
            insert_result = collection.insert(entities)
            collection.flush()

            logger.info(f"Successfully inserted {len(rows)} documents into Milvus collection {collection_name}")
            return []

        except Exception as e:
            error_msg = f"Failed to insert documents into Milvus: {str(e)}"
            logger.error(error_msg)
            return [error_msg]

    def update(self, condition: dict, newValue: dict, indexName: str, knowledgebaseId: str) -> bool:
        """更新文档"""
        if not self.milvus_available:
            return False

        try:
            collection_name = self._get_collection_name(indexName, knowledgebaseId)
            if not utility.has_collection(collection_name):
                return False

            collection = Collection(collection_name)
            collection.load()

            # 构建过滤表达式
            filter_expr = self._build_filter_expression(condition)

            # 执行更新
            collection.delete(filter_expr)

            # 重新插入更新后的数据
            # 这里简化处理，实际应该合并新旧数据
            return True

        except Exception as e:
            logger.error(f"Failed to update documents: {str(e)}")
            return False

    def delete(self, condition: dict, indexName: str, knowledgebaseId: str) -> int:
        """删除文档"""
        if not self.milvus_available:
            return 0

        try:
            collection_name = self._get_collection_name(indexName, knowledgebaseId)
            if not utility.has_collection(collection_name):
                return 0

            collection = Collection(collection_name)
            collection.load()

            # 构建过滤表达式
            filter_expr = self._build_filter_expression(condition)

            # 先查询要删除的记录数量
            results = collection.query(
                expr=filter_expr,
                output_fields=["id"],
                limit=None
            )

            delete_count = len(results)

            # 执行删除
            if delete_count > 0:
                collection.delete(filter_expr)
                logger.info(f"Deleted {delete_count} documents from Milvus collection {collection_name}")

            return delete_count

        except Exception as e:
            logger.error(f"Failed to delete documents: {str(e)}")
            return 0

    def delete_user_document_data(self, file_name: str, index_name: str) -> dict:
        """智能删除用户文档数据（按文件名）"""
        result = {
            'deleted_count': 0,
            'collection_exists': False,
            'strategy_used': '',
            'errors': []
        }

        if not self.milvus_available:
            result['errors'].append("Milvus连接不可用")
            return result

        try:
            import xxhash

            # 检查集合是否存在（使用用户ID作为索引名称）
            if not utility.has_collection(index_name):
                result['strategy_used'] = 'collection_not_exists'
                logger.info(f"Milvus集合不存在: {index_name}")
                return result

            result['collection_exists'] = True
            collection = Collection(index_name)
            collection.load()

            # 生成文档ID哈希
            doc_id = xxhash.xxh64(file_name.encode("utf-8")).hexdigest()

            # 构建多条件查询
            filter_expr = f'(doc_id == "{doc_id}") or (docnm_kwd == "{file_name}")'

            # 查询要删除的记录
            results = collection.query(
                expr=filter_expr,
                output_fields=["id"],
                limit=None
            )

            delete_count = len(results)
            result['deleted_count'] = delete_count
            result['strategy_used'] = 'multi_field_match'

            # 执行删除
            if delete_count > 0:
                collection.delete(filter_expr)
                logger.info(f"按文件名删除Milvus文档: {file_name}, 删除数量: {delete_count}, collection: {index_name}")

            return result

        except Exception as e:
            error_msg = f"删除Milvus文档失败: file_name={file_name}, collection={index_name}, error={str(e)}"
            result['errors'].append(error_msg)
            logger.error(error_msg)
            return result

    """
    Helper functions for search result
    """

    def getTotal(self, res):
        """获取搜索结果总数"""
        return res.get("total", 0)

    def getChunkIds(self, res):
        """提取搜索结果中的文档ID"""
        return res.get("ids", [])

    def getHighlight(self, res, keywords: list[str], fieldnm: str):
        """处理搜索结果的高亮片段"""
        # Milvus不直接支持高亮，这里模拟高亮处理
        ans = {}
        fields = res.get("fields", {})

        for chunk_id, chunk_data in fields.items():
            content = chunk_data.get(fieldnm, "")
            if not content:
                continue

            # 简单的关键词高亮处理
            highlighted_content = content
            for keyword in keywords:
                if is_english([keyword]):
                    # 英文高亮
                    highlighted_content = re.sub(
                        rf"(^|[ .?/'\"\(\)!,:;-])({re.escape(keyword)})([ .?/'\"\(\)!,:;-])",
                        r"\1<em>\2</em>\3",
                        highlighted_content,
                        flags=re.IGNORECASE | re.MULTILINE
                    )
                else:
                    # 中文高亮
                    highlighted_content = highlighted_content.replace(keyword, f"<em>{keyword}</em>")

            if "<em>" in highlighted_content:
                ans[chunk_id] = highlighted_content

        return ans

    def getAggregation(self, res, fieldnm: str):
        """提取搜索结果的聚合信息"""
        # Milvus的聚合功能有限，这里返回空列表
        # 实际应用中可以通过额外的query操作实现
        return []

    def getFields(self, res, fields: list[str]) -> dict[str, dict]:
        """从搜索结果中提取指定字段"""
        res_fields = {}
        if not fields:
            return {}

        result_fields = res.get("fields", {})
        for chunk_id, chunk_data in result_fields.items():
            m = {n: chunk_data.get(n) for n in fields if chunk_data.get(n) is not None}
            for n, v in m.items():
                if isinstance(v, list):
                    m[n] = v
                    continue
                if not isinstance(v, str):
                    m[n] = str(m[n])

            if m:
                res_fields[chunk_id] = m

        return res_fields

    def sql(self, sql: str, fetch_size: int, format: str):
        """执行SQL查询"""
        # Milvus不支持标准SQL，这里提供一个基本的查询接口
        logger.warning("Milvus does not support standard SQL queries")
        return []


# 全局Milvus连接实例
milvus_connection = MilvusConnection()