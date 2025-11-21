"""
混合检索服务
结合Milvus向量搜索和Elasticsearch全文搜索，实现高性能混合检索
"""

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from elasticsearch import AsyncElasticsearch

from .milvus_service import MilvusService
from .models import (
    SearchRequest, SearchResponse, SearchResult,
    DocumentChunk, HYBRID_SEARCH_WEIGHTS, PERFORMANCE_BASELINES
)

logger = logging.getLogger(__name__)


class HybridSearchService:
    """混合检索服务 - 结合Milvus和ES的优势"""

    def __init__(self,
                 milvus_service: MilvusService,
                 es_client: AsyncElasticsearch,
                 vector_weight: float = 0.95,
                 text_weight: float = 0.05,
                 max_workers: int = 4):
        """
        初始化混合检索服务

        Args:
            milvus_service: Milvus服务实例
            es_client: Elasticsearch客户端
            vector_weight: 向量搜索权重 (默认0.95)
            text_weight: 全文搜索权重 (默认0.05)
            max_workers: 最大工作线程数
        """
        self.milvus_service = milvus_service
        self.es_client = es_client
        self.vector_weight = vector_weight
        self.text_weight = text_weight
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # 验证权重和为1
        if abs(vector_weight + text_weight - 1.0) > 0.001:
            logger.warning(f"权重和不等于1，当前向量权重: {vector_weight}, 文本权重: {text_weight}")

    async def search(self, request: SearchRequest) -> SearchResponse:
        """执行混合检索"""
        try:
            logger.info(f"开始混合检索 - 查询: {request.query}, 用户: {request.kb_id}")
            start_time = time.time()

            # 1. 生成查询向量
            query_vector = await self._generate_query_vector(request.query)
            if not query_vector:
                logger.warning("查询向量化失败，降级为纯文本搜索")
                return await self._fallback_text_search(request)

            # 2. 构建过滤条件
            milvus_filters = self._build_milvus_filters(request)
            es_filters = self._build_es_filters(request)

            # 3. 并行执行向量搜索和全文搜索
            milvus_task = self._search_milvus(query_vector, request, milvus_filters)
            es_task = self._search_elasticsearch(request.query, request, es_filters)

            try:
                milvus_results, es_results = await asyncio.gather(
                    milvus_task, es_task, return_exceptions=True
                )

                # 处理异常结果
                if isinstance(milvus_results, Exception):
                    logger.error(f"Milvus搜索失败: {milvus_results}")
                    milvus_results = []

                if isinstance(es_results, Exception):
                    logger.error(f"ES搜索失败: {es_results}")
                    es_results = []

            except Exception as e:
                logger.error(f"并行搜索失败: {e}")
                return await self._handle_search_error(request, e)

            # 4. 结果融合
            fused_results = self._fuse_results(milvus_results, es_results)

            # 5. 重排序
            reranked_results = await self._rerank_results(fused_results, request.query)

            # 6. 应用阈值过滤
            final_results = self._apply_threshold_filter(reranked_results, request.similarity_threshold)

            # 7. 分页处理
            paginated_results = self._paginate_results(final_results, request.offset, request.top_k)

            search_time = time.time() - start_time

            response = SearchResponse(
                results=paginated_results,
                total=len(final_results),
                page=request.offset // request.top_k + 1,
                page_size=request.top_k,
                query=request.query,
                search_time=search_time,
                has_more=len(final_results) > (request.offset + request.top_k)
            )

            logger.info(f"✅ 混合检索完成 - 结果数: {len(paginated_results)}, 耗时: {search_time:.3f}s")
            return response

        except Exception as e:
            logger.error(f"❌ 混合检索失败: {e}")
            return await self._handle_search_error(request, e)

    async def _generate_query_vector(self, query: str) -> Optional[List[float]]:
        """生成查询向量"""
        try:
            # 使用与文档相同的向量化服务
            # 这里需要集成现有的DashScope text-embedding-v3服务
            logger.debug(f"生成查询向量: {query[:50]}...")

            # TODO: 集成实际的向量化服务
            # 临时返回模拟向量
            import random
            return [random.random() for _ in range(1024)]

        except Exception as e:
            logger.error(f"查询向量化失败: {e}")
            return None

    def _build_milvus_filters(self, request: SearchRequest) -> Dict[str, Any]:
        """构建Milvus过滤条件"""
        filters = {}

        if request.kb_id:
            filters['kb_id'] = request.kb_id

        if request.category:
            filters['category'] = request.category

        if request.confidence_min is not None:
            filters['confidence_min'] = request.confidence_min

        if request.confidence_max is not None:
            filters['confidence_max'] = request.confidence_max

        if request.timestamp_start is not None:
            filters['timestamp_start'] = request.timestamp_start

        if request.timestamp_end is not None:
            filters['timestamp_end'] = request.timestamp_end

        if request.source:
            filters['source'] = request.source

        if request.doc_ids:
            filters['doc_ids'] = request.doc_ids

        return filters

    def _build_es_filters(self, request: SearchRequest) -> Dict[str, Any]:
        """构建ES过滤条件"""
        filters = {}

        if request.kb_id:
            filters['kb_id'] = request.kb_id

        if request.category:
            filters['category'] = request.category

        if request.confidence_min is not None:
            filters['confidence_min'] = request.confidence_min

        if request.confidence_max is not None:
            filters['confidence_max'] = request.confidence_max

        if request.timestamp_start is not None:
            filters['timestamp_start'] = request.timestamp_start

        if request.timestamp_end is not None:
            filters['timestamp_end'] = request.timestamp_end

        if request.source:
            filters['source'] = request.source

        if request.doc_ids:
            filters['doc_ids'] = request.doc_ids

        return filters

    async def _search_milvus(self, query_vector: List[float], request: SearchRequest,
                           filters: Dict[str, Any]) -> List[SearchResult]:
        """Milvus向量搜索"""
        try:
            collection_name = f"user_{request.kb_id}_documents"

            # 构建过滤表达式
            filter_expr = self._build_milvus_filter_expression(filters)

            # 搜索参数
            search_params = {
                "metric_type": "COSINE",
                "params": {"ef": 64}
            }

            # 输出字段
            output_fields = ["content", "doc_id", "doc_name", "category",
                           "confidence", "source", "metadata", "chunk_id"]

            logger.debug(f"Milvus搜索 - 集合: {collection_name}, 过滤: {filter_expr}")

            # 执行搜索
            results = await self.milvus_service.search(
                collection_name=collection_name,
                query_vector=query_vector,
                top_k=request.top_k * 2,  # 获取更多结果用于融合
                filter_expr=filter_expr,
                search_params=search_params,
                output_fields=output_fields
            )

            logger.info(f"Milvus搜索完成 - 返回 {len(results)} 条结果")
            return results

        except Exception as e:
            logger.error(f"Milvus搜索失败: {e}")
            return []

    async def _search_elasticsearch(self, query: str, request: SearchRequest,
                                  filters: Dict[str, Any]) -> List[SearchResult]:
        """Elasticsearch全文搜索"""
        try:
            # 构建ES查询
            es_query = self._build_es_query(query, request, filters)

            logger.debug(f"ES搜索 - 索引: {request.kb_id}, 查询: {query[:50]}...")

            # 执行搜索
            es_results = await self.es_client.search(
                index=str(request.kb_id),
                body=es_query
            )

            # 转换结果格式
            results = self._convert_es_results(es_results)

            logger.info(f"ES搜索完成 - 返回 {len(results)} 条结果")
            return results

        except Exception as e:
            logger.error(f"ES搜索失败: {e}")
            return []

    def _build_milvus_filter_expression(self, filters: Dict[str, Any]) -> str:
        """构建Milvus过滤表达式"""
        expressions = []

        if 'kb_id' in filters:
            expressions.append(f'kb_id == "{filters["kb_id"]}"')

        if 'category' in filters:
            expressions.append(f'category == "{filters["category"]}"')

        if 'confidence_min' in filters:
            expressions.append(f'confidence >= {filters["confidence_min"]}')

        if 'confidence_max' in filters:
            expressions.append(f'confidence <= {filters["confidence_max"]}')

        if 'timestamp_start' in filters:
            expressions.append(f'timestamp >= {filters["timestamp_start"]}')

        if 'timestamp_end' in filters:
            expressions.append(f'timestamp <= {filters["timestamp_end"]}')

        if 'source' in filters:
            expressions.append(f'source == "{filters["source"]}"')

        if 'doc_ids' in filters and filters['doc_ids']:
            doc_ids_str = ', '.join([f'"{doc_id}"' for doc_id in filters['doc_ids']])
            expressions.append(f'doc_id in [{doc_ids_str}]')

        return ' and '.join(expressions) if expressions else ""

    def _build_es_query(self, query: str, request: SearchRequest, filters: Dict[str, Any]) -> Dict[str, Any]:
        """构建ES查询"""
        # 基础查询结构
        es_query = {
            "query": {
                "bool": {
                    "must": [
                        {"match": {"content_with_weight": query}}
                    ],
                    "filter": []
                }
            },
            "size": request.top_k * 2,  # 获取更多结果用于融合
            "_source": ["content_with_weight", "doc_id", "doc_name", "confidence", "create_time"]
        }

        # 添加过滤条件
        if 'kb_id' in filters:
            es_query["query"]["bool"]["filter"].append({"term": {"kb_id": filters['kb_id']}})

        if 'category' in filters:
            es_query["query"]["bool"]["filter"].append({"term": {"category": filters['category']}})

        if 'confidence_min' in filters:
            es_query["query"]["bool"]["filter"].append({"range": {"confidence": {"gte": filters['confidence_min']}}})

        if 'confidence_max' in filters:
            es_query["query"]["bool"]["filter"].append({"range": {"confidence": {"lte": filters['confidence_max']}}})

        if 'timestamp_start' in filters:
            es_query["query"]["bool"]["filter"].append({"range": {"create_timestamp_flt": {"gte": filters['timestamp_start']}}})

        if 'timestamp_end' in filters:
            es_query["query"]["bool"]["filter"].append({"range": {"create_timestamp_flt": {"lte": filters['timestamp_end']}}})

        if 'source' in filters:
            es_query["query"]["bool"]["filter"].append({"term": {"source": filters['source']}})

        if 'doc_ids' in filters and filters['doc_ids']:
            es_query["query"]["bool"]["filter"].append({"terms": {"doc_id": filters['doc_ids']}})

        return es_query

    def _convert_es_results(self, es_results: Dict[str, Any]) -> List[SearchResult]:
        """转换ES搜索结果"""
        results = []

        for hit in es_results.get('hits', {}).get('hits', []):
            source = hit['_source']

            result = SearchResult(
                id=int(hit['_id']),
                score=hit['_score'],
                content=source.get('content_with_weight', ''),
                doc_id=source.get('doc_id', ''),
                doc_name=source.get('doc_name', ''),
                category='general',  # ES结果默认分类
                confidence=source.get('confidence', 0.8),
                source='elasticsearch',
                metadata={'original_score': hit['_score']}
            )
            results.append(result)

        return results

    def _fuse_results(self, milvus_results: List[SearchResult],
                     es_results: List[SearchResult]) -> List[Dict[str, Any]]:
        """融合Milvus和ES搜索结果"""
        # 创建结果映射，使用doc_id + content作为唯一标识
        result_map = {}

        # 处理Milvus结果 (向量权重)
        for result in milvus_results:
            key = f"{result.doc_id}_{hash(result.content) % 1000000}"
            result_map[key] = {
                'chunk': result,
                'vector_score': result.score * self.vector_weight,
                'text_score': 0.0,
                'combined_score': result.score * self.vector_weight,
                'sources': ['milvus']
            }

        # 处理ES结果 (文本权重)
        for result in es_results:
            key = f"{result.doc_id}_{hash(result.content) % 1000000}"
            text_score = result.score * self.text_weight

            if key in result_map:
                # 更新现有结果
                fused = result_map[key]
                fused['text_score'] = text_score
                fused['combined_score'] += text_score
                fused['sources'].append('elasticsearch')
            else:
                # 新增结果
                result_map[key] = {
                    'chunk': result,
                    'vector_score': 0.0,
                    'text_score': text_score,
                    'combined_score': text_score,
                    'sources': ['elasticsearch']
                }

        # 转换为列表并按综合得分排序
        fused_results = list(result_map.values())
        fused_results.sort(key=lambda x: x['combined_score'], reverse=True)

        logger.info(f"结果融合完成 - Milvus: {len(milvus_results)}, ES: {len(es_results)}, 融合后: {len(fused_results)}")

        return fused_results

    async def _rerank_results(self, fused_results: List[Dict[str, Any]],
                            query: str) -> List[SearchResult]:
        """重排序结果"""
        try:
            reranked_results = []

            for i, fused in enumerate(fused_results):
                chunk = fused['chunk']

                # 计算额外的相似度特征
                text_similarity = self._calculate_text_similarity(query, chunk.content)
                vector_similarity = fused['vector_score'] / self.vector_weight if self.vector_weight > 0 else 0

                # 计算综合得分（考虑位置衰减）
                position_decay = 1.0 / (1.0 + i * 0.01)  # 位置衰减因子
                combined_score = fused['combined_score'] * position_decay

                # 创建新的搜索结果
                result = SearchResult(
                    id=chunk.id,
                    score=combined_score,
                    content=chunk.content,
                    doc_id=chunk.doc_id,
                    doc_name=chunk.doc_name,
                    category=chunk.category,
                    confidence=chunk.confidence,
                    source='+'.join(fused['sources']),
                    metadata={
                        **(chunk.metadata or {}),
                        'vector_similarity': vector_similarity,
                        'text_similarity': text_similarity,
                        'combined_score': combined_score,
                        'original_vector_score': fused['vector_score'],
                        'original_text_score': fused['text_score'],
                        'position': i
                    }
                )

                reranked_results.append(result)

            return reranked_results

        except Exception as e:
            logger.error(f"重排序失败: {e}")
            # 降级返回原始结果
            return [fused['chunk'] for fused in fused_results]

    def _calculate_text_similarity(self, query: str, content: str) -> float:
        """计算文本相似度"""
        try:
            # 简单的词频相似度计算
            query_words = set(query.lower().split())
            content_words = set(content.lower().split())

            if not query_words or not content_words:
                return 0.0

            # Jaccard相似度
            intersection = len(query_words & content_words)
            union = len(query_words | content_words)

            return intersection / union if union > 0 else 0.0

        except Exception as e:
            logger.error(f"文本相似度计算失败: {e}")
            return 0.0

    def _apply_threshold_filter(self, results: List[SearchResult],
                               threshold: Optional[float]) -> List[SearchResult]:
        """应用相似度阈值过滤"""
        if threshold is None:
            return results

        filtered_results = [
            result for result in results
            if result.score >= threshold
        ]

        if len(filtered_results) < len(results):
            logger.info(f"应用阈值过滤 - 原始: {len(results)}, 过滤后: {len(filtered_results)}, 阈值: {threshold}")

        return filtered_results

    def _paginate_results(self, results: List[SearchResult],
                         offset: int, page_size: int) -> List[SearchResult]:
        """分页处理结果"""
        start = offset
        end = offset + page_size
        return results[start:end]

    async def _fallback_text_search(self, request: SearchRequest) -> SearchResponse:
        """降级到纯文本搜索"""
        logger.warning("执行降级文本搜索")

        try:
            start_time = time.time()

            # 仅使用ES进行文本搜索
            es_results = await self._search_elasticsearch(
                request.query, request, self._build_es_filters(request)
            )

            # 调整得分
            for result in es_results:
                result.score *= self.text_weight
                result.metadata['fallback'] = True

            # 分页处理
            paginated_results = self._paginate_results(es_results, request.offset, request.top_k)

            search_time = time.time() - start_time

            return SearchResponse(
                results=paginated_results,
                total=len(es_results),
                page=request.offset // request.top_k + 1,
                page_size=request.top_k,
                query=request.query,
                search_time=search_time,
                has_more=len(es_results) > (request.offset + request.top_k)
            )

        except Exception as e:
            logger.error(f"降级文本搜索失败: {e}")
            return SearchResponse(
                results=[],
                total=0,
                page=1,
                page_size=request.top_k,
                query=request.query,
                search_time=0.0,
                has_more=False
            )

    async def _handle_search_error(self, request: SearchRequest, error: Exception) -> SearchResponse:
        """处理搜索错误"""
        logger.error(f"搜索错误处理 - 查询: {request.query}, 错误: {error}")

        return SearchResponse(
            results=[],
            total=0,
            page=1,
            page_size=request.top_k,
            query=request.query,
            search_time=0.0,
            has_more=False
        )

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 检查Milvus连接
            milvus_health = await self.milvus_service.health_check()

            # 检查ES连接
            es_health = await self.es_client.ping()

            return {
                "status": "healthy" if milvus_health.get("status") == "healthy" and es_health else "unhealthy",
                "milvus_status": milvus_health.get("status"),
                "elasticsearch_status": "connected" if es_health else "disconnected",
                "vector_weight": self.vector_weight,
                "text_weight": self.text_weight,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def update_weights(self, vector_weight: float, text_weight: float) -> bool:
        """更新搜索权重"""
        try:
            if abs(vector_weight + text_weight - 1.0) > 0.001:
                logger.error(f"权重和不等于1: vector={vector_weight}, text={text_weight}")
                return False

            self.vector_weight = vector_weight
            self.text_weight = text_weight

            logger.info(f"搜索权重已更新 - 向量: {vector_weight}, 文本: {text_weight}")
            return True

        except Exception as e:
            logger.error(f"更新权重失败: {e}")
            return False

    async def cleanup(self) -> None:
        """清理资源"""
        try:
            logger.info("正在清理混合搜索服务资源")
            self.executor.shutdown(wait=True)
            logger.info("✅ 混合搜索服务资源清理完成")
        except Exception as e:
            logger.error(f"清理资源失败: {e}")