"""
ES到Milvus数据迁移服务
实现从现有Elasticsearch到Milvus的平滑数据迁移
"""

import asyncio
import time
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from elasticsearch import AsyncElasticsearch
from pymilvus import Collection, utility

from .models import (
    DocumentChunk, MigrationResult, ES_TO_MILVUS_MAPPING,
    MIGRATION_CONFIG, PERFORMANCE_BASELINES
)
from .milvus_service import MilvusService

logger = logging.getLogger(__name__)


class DataMigrationService:
    """ES到Milvus数据迁移服务"""

    def __init__(self,
                 es_client: AsyncElasticsearch,
                 milvus_service: MilvusService,
                 batch_size: int = 1000,
                 max_workers: int = 4,
                 validation_sample_rate: float = 0.01):
        """
        初始化迁移服务

        Args:
            es_client: Elasticsearch客户端
            milvus_service: Milvus服务实例
            batch_size: 批量处理大小
            max_workers: 最大工作线程数
            validation_sample_rate: 验证采样率
        """
        self.es_client = es_client
        self.milvus_service = milvus_service
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.validation_sample_rate = validation_sample_rate
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def migrate_user_data(self, user_id: int) -> MigrationResult:
        """迁移单个用户的所有数据"""
        try:
            logger.info(f"开始迁移用户 {user_id} 的数据")

            start_time = datetime.now()
            total_migrated = 0
            success_count = 0
            failed_count = 0
            errors = []

            # 1. 获取用户数据统计
            es_stats = await self.get_es_statistics(user_id)
            logger.info(f"ES数据统计 - 总记录数: {es_stats['total_documents']}")

            # 2. 创建Milvus集合
            collection_name = f"user_{user_id}_documents"
            if not await self._create_user_collection(collection_name):
                error_msg = f"创建用户集合失败: {collection_name}"
                logger.error(error_msg)
                return MigrationResult(
                    user_id=str(user_id),
                    total_migrated=0,
                    success_count=0,
                    failed_count=0,
                    validation_passed=False,
                    migration_time=0,
                    start_time=start_time,
                    end_time=datetime.now(),
                    errors=[error_msg]
                )

            # 3. 执行数据迁移
            migration_result = await self._migrate_data_in_batches(
                user_id, collection_name, es_stats['total_documents']
            )

            total_migrated = migration_result['total_processed']
            success_count = migration_result['success_count']
            failed_count = migration_result['failed_count']
            errors.extend(migration_result['errors'])

            # 4. 数据验证
            validation_passed = await self._validate_migration(
                user_id, collection_name, total_migrated
            )

            # 5. 性能对比
            performance_comparison = await self._compare_performance(
                user_id, collection_name, es_stats
            )

            end_time = datetime.now()
            migration_time = (end_time - start_time).total_seconds()

            # 6. 生成迁移报告
            migration_result = MigrationResult(
                user_id=str(user_id),
                total_migrated=total_migrated,
                success_count=success_count,
                failed_count=failed_count,
                validation_passed=validation_passed,
                migration_time=migration_time,
                start_time=start_time,
                end_time=end_time,
                errors=errors
            )

            # 7. 记录迁移结果
            await self._log_migration_result(migration_result, performance_comparison)

            logger.info(f"✅ 用户 {user_id} 数据迁移完成")
            logger.info(f"📊 总计: {total_migrated}, 成功: {success_count}, 失败: {failed_count}")
            logger.info(f"✅ 验证通过: {validation_passed}")
            logger.info(f"⏱️  耗时: {migration_time:.2f}秒")

            return migration_result

        except Exception as e:
            logger.error(f"❌ 迁移用户 {user_id} 数据失败: {e}")
            end_time = datetime.now()
            migration_time = (end_time - start_time).total_seconds()

            return MigrationResult(
                user_id=str(user_id),
                total_migrated=0,
                success_count=0,
                failed_count=0,
                validation_passed=False,
                migration_time=migration_time,
                start_time=start_time,
                end_time=end_time,
                errors=[str(e)]
            )

    async def get_es_statistics(self, user_id: int) -> Dict[str, Any]:
        """获取ES数据统计"""
        try:
            logger.info(f"正在获取用户 {user_id} 的ES数据统计")

            # 获取总文档数
            count_query = {
                "query": {"match_all": {}},
                "size": 0
            }

            count_response = await self.es_client.search(
                index=str(user_id),
                body=count_query
            )

            total_documents = count_response['hits']['total']['value']

            # 获取索引信息
            index_info = await self.es_client.indices.get(index=str(user_id))

            # 获取文档大小统计
            size_query = {
                "query": {"match_all": {}},
                "size": 100,  # 采样100个文档
                "_source": ["content_with_weight"]
            }

            size_response = await self.es_client.search(
                index=str(user_id),
                body=size_query
            )

            # 计算平均文档大小
            total_size = 0
            doc_count = 0
            for hit in size_response['hits']['hits']:
                content = hit['_source'].get('content_with_weight', '')
                total_size += len(content)
                doc_count += 1

            avg_doc_size = total_size / doc_count if doc_count > 0 else 0

            stats = {
                "total_documents": total_documents,
                "index_name": str(user_id),
                "avg_doc_size": avg_doc_size,
                "estimated_total_size": total_documents * avg_doc_size
            }

            logger.info(f"📊 ES数据统计 - 总记录数: {total_documents}, 平均文档大小: {avg_doc_size:.0f}字符")

            return stats

        except Exception as e:
            logger.error(f"❌ 获取ES数据统计失败: {e}")
            return {"total_documents": 0, "avg_doc_size": 0}

    async def _create_user_collection(self, collection_name: str) -> bool:
        """创建用户专用集合"""
        try:
            logger.info(f"正在创建用户集合: {collection_name}")

            # 创建集合配置
            config = CollectionConfig(
                collection_name=collection_name,
                description=f"用户文档向量存储 - {collection_name}",
                vector_dim=1024,  # 保持与ES相同的维度
                metric_type=MetricType.COSINE,  # 保持与ES相同的度量方式
                index_type=IndexType.HNSW,  # 高性能索引
                enable_dynamic_field=True
            )

            # 创建集合
            success = await self.milvus_service.create_collection(collection_name, config)
            if not success:
                return False

            # 创建索引
            index_success = await self.milvus_service.create_index(collection_name)
            if not index_success:
                return False

            logger.info(f"✅ 成功创建用户集合: {collection_name}")
            return True

        except Exception as e:
            logger.error(f"❌ 创建用户集合失败: {e}")
            return False

    async def _migrate_data_in_batches(self, user_id: int, collection_name: str, total_count: int) -> Dict[str, Any]:
        """批量迁移数据"""
        try:
            logger.info(f"开始批量迁移数据 - 总数: {total_count}")

            total_processed = 0
            success_count = 0
            failed_count = 0
            errors = []

            # 使用scroll API批量读取数据
            scroll_time = "5m"
            batch_size = self.batch_size

            # 开始scroll
            initial_query = {
                "query": {"match_all": {}},
                "size": batch_size,
                "_source": [
                    "_id", "content_with_weight", "content_ltks", "doc_id", "docnm_kwd",
                    "q_1024_vec", "create_time", "create_timestamp_flt", "kb_id"
                ],
                "sort": ["_doc"]
            }

            scroll_response = await self.es_client.search(
                index=str(user_id),
                body=initial_query,
                scroll=scroll_time
            )

            scroll_id = scroll_response.get('_scroll_id')
            hits = scroll_response['hits']['hits']

            while hits:
                logger.info(f"📦 处理批次: {total_processed}-{min(total_processed + batch_size, total_count)}")

                # 转换和处理数据
                batch_result = await self._process_batch(hits, collection_name)

                total_processed += batch_result['processed_count']
                success_count += batch_result['success_count']
                failed_count += batch_result['failed_count']
                errors.extend(batch_result['errors'])

                # 获取下一批数据
                scroll_response = await self.es_client.scroll(
                    scroll_id=scroll_id,
                    scroll=scroll_time
                )

                hits = scroll_response['hits']['hits']

                # 定期报告进度
                if total_processed % 10000 == 0:
                    progress = (total_processed / total_count) * 100
                    logger.info(f"📈 迁移进度: {progress:.1f}% ({total_processed}/{total_count})")

            return {
                "total_processed": total_processed,
                "success_count": success_count,
                "failed_count": failed_count,
                "errors": errors
            }

        except Exception as e:
            logger.error(f"❌ 批量迁移数据失败: {e}")
            return {
                "total_processed": total_processed,
                "success_count": success_count,
                "failed_count": failed_count,
                "errors": [str(e)]
            }

    async def _process_batch(self, hits: List[Dict[str, Any]], collection_name: str) -> Dict[str, Any]:
        """处理一批数据"""
        try:
            processed_count = 0
            success_count = 0
            failed_count = 0
            errors = []
            milvus_data = []

            for hit in hits:
                try:
                    # 转换ES数据到Milvus格式
                    milvus_record = self._convert_es_to_milvus(hit)
                    milvus_data.append(milvus_record)
                    processed_count += 1

                except Exception as e:
                    logger.error(f"数据转换失败 (ID: {hit.get('_id', 'unknown')}): {e}")
                    failed_count += 1
                    errors.append(f"ID {hit.get('_id', 'unknown')}: {str(e)}")

            # 批量插入Milvus
            if milvus_data:
                try:
                    # 创建DocumentChunk对象
                    chunks = []
                    for record in milvus_data:
                        chunk = DocumentChunk(**record)
                        chunks.append(chunk)

                    # 插入数据
                    insert_success = await self.milvus_service.insert_data(
                        collection_name, chunks, batch_size=100
                    )

                    if insert_success:
                        success_count += len(milvus_data)
                    else:
                        failed_count += len(milvus_data)
                        errors.append("Milvus插入失败")

                except Exception as e:
                    logger.error(f"Milvus插入失败: {e}")
                    failed_count += len(milvus_data)
                    errors.append(f"Milvus插入: {str(e)}")

            return {
                "processed_count": processed_count,
                "success_count": success_count,
                "failed_count": failed_count,
                "errors": errors
            }

        except Exception as e:
            logger.error(f"❌ 处理批次失败: {e}")
            return {
                "processed_count": 0,
                "success_count": 0,
                "failed_count": len(hits),
                "errors": [str(e)]
            }

    def _convert_es_to_milvus(self, es_hit: Dict[str, Any]) -> Dict[str, Any]:
        """转换ES数据到Milvus格式"""
        try:
            source = es_hit['_source']
            es_id = es_hit['_id']
            es_index = es_hit['_index']

            # 基础数据转换
            milvus_record = {
                "vector": source.get('q_1024_vec', []),
                "content": source.get('content_with_weight', ''),
                "content_ltks": source.get('content_ltks', ''),
                "doc_id": source.get('doc_id', ''),
                "doc_name": source.get('docnm_kwd', ''),
                "kb_id": es_index,  # ES索引名作为kb_id
                "chunk_id": es_id,  # ES文档ID作为chunk_id
                "category": "general",  # 默认分类
                "confidence": 0.8,  # 默认置信度
                "timestamp": int(source.get('create_timestamp_flt', time.time())),
                "source": "migration",
                "keywords": "",  # 可以从内容中提取
                "metadata": {
                    "original_id": es_id,
                    "original_index": es_index,
                    "migration_time": datetime.now().isoformat(),
                    "es_create_time": source.get('create_time', ''),
                    # 存储ES中的其他动态字段
                    "es_dynamic_fields": {
                        key: value for key, value in source.items()
                        if key not in ['q_1024_vec', 'content_with_weight', 'content_ltks', 'doc_id', 'docnm_kwd', 'create_time', 'create_timestamp_flt']
                    }
                }
            }

            return milvus_record

        except Exception as e:
            logger.error(f"数据转换失败: {e}")
            raise e

    async def _validate_migration(self, user_id: int, collection_name: str, expected_count: int) -> bool:
        """验证迁移结果"""
        try:
            logger.info(f"正在验证迁移结果 - 用户: {user_id}, 集合: {collection_name}")

            # 获取Milvus中的数据数量
            milvus_stats = await self.milvus_service.get_collection_stats(collection_name)
            milvus_count = milvus_stats.get('num_entities', 0)

            # 获取ES中的数据数量（再次确认）
            es_stats = await self.get_es_statistics(user_id)
            es_count = es_stats.get('total_documents', 0)

            # 数据数量验证
            count_match = abs(milvus_count - expected_count) <= 10  # 允许10条以内的差异

            # 采样验证
            sample_validation = await self._sample_validation(user_id, collection_name)

            validation_passed = count_match and sample_validation

            logger.info(f"✅ 验证结果 - 数量匹配: {count_match}, 采样验证: {sample_validation}")
            logger.info(f"📊 Milvus数量: {milvus_count}, ES数量: {es_count}, 期望数量: {expected_count}")

            return validation_passed

        except Exception as e:
            logger.error(f"❌ 验证迁移结果失败: {e}")
            return False

    async def _sample_validation(self, user_id: int, collection_name: str) -> bool:
        """采样验证"""
        try:
            logger.info(f"正在执行采样验证 - 采样率: {self.validation_sample_rate}")

            # 从ES获取采样数据
            sample_query = {
                "query": {"function_score": {
                    "functions": [{"random_score": {}}],
                    "random_score": {}
                }},
                "size": 100,  # 采样100条
                "_source": [
                    "_id", "content_with_weight", "q_1024_vec", "doc_id", "docnm_kwd"
                ]
            }

            sample_response = await self.es_client.search(
                index=str(user_id),
                body=sample_query
            )

            samples = sample_response['hits']['hits']
            validation_passed = True

            for i, hit in enumerate(samples):
                try:
                    es_data = hit['_source']
                    es_id = hit['_id']

                    # 在Milvus中查找对应记录
                    milvus_results = await self.milvus_service.query(
                        collection_name=collection_name,
                        filter_expr=f'chunk_id == "{es_id}"',
                        output_fields=["content", "vector", "doc_id", "doc_name"],
                        limit=1
                    )

                    if len(milvus_results) == 0:
                        logger.warning(f"采样验证失败 - 未找到对应记录: {es_id}")
                        validation_passed = False
                        continue

                    milvus_data = milvus_results[0]

                    # 验证关键字段
                    content_match = es_data.get('content_with_weight', '') == milvus_data.get('content', '')
                    doc_id_match = es_data.get('doc_id', '') == milvus_data.get('doc_id', '')
                    doc_name_match = es_data.get('docnm_kwd', '') == milvus_data.get('doc_name', '')
                    vector_match = len(es_data.get('q_1024_vec', [])) == len(milvus_data.get('vector', []))

                    if not (content_match and doc_id_match and doc_name_match and vector_match):
                        logger.warning(f"采样验证失败 - 字段不匹配: {es_id}")
                        validation_passed = False

                except Exception as e:
                    logger.error(f"采样验证错误 (ID: {es_id}): {e}")
                    validation_passed = False

            logger.info(f"✅ 采样验证完成 - 通过率: {validation_passed}")
            return validation_passed

        except Exception as e:
            logger.error(f"❌ 采样验证失败: {e}")
            return False

    async def _compare_performance(self, user_id: int, collection_name: str, es_stats: Dict[str, Any]) -> Dict[str, Any]:
        """性能对比"""
        try:
            logger.info(f"正在对比性能 - 用户: {user_id}, 集合: {collection_name}")

            # 准备测试数据
            test_query = {
                "query": {"match_all": {}},
                "size": 10,
                "_source": ["q_1024_vec"]
            }

            test_response = await self.es_client.search(
                index=str(user_id),
                body=test_query
            )

            if len(test_response['hits']['hits']) == 0:
                return {"error": "No test data available"}

            test_vector = test_response['hits']['hits'][0]['_source']['q_1024_vec']

            # ES性能测试
            es_start = time.time()
            es_results = await self.es_client.search(
                index=str(user_id),
                body={
                    "query": {
                        "script_score": {
                            "query": {"match_all": {}},
                            "script": {
                                "source": "cosineSimilarity(params.query_vector, 'q_1024_vec') + 1.0",
                                "params": {"query_vector": test_vector}
                            }
                        }
                    },
                    "size": 10
                }
            )
            es_time = time.time() - es_start

            # Milvus性能测试
            milvus_start = time.time()
            milvus_results = await self.milvus_service.search(
                collection_name=collection_name,
                query_vector=test_vector,
                top_k=10
            )
            milvus_time = time.time() - milvus_start

            comparison = {
                "es_search_time": es_time,
                "milvus_search_time": milvus_time,
                "speedup_ratio": es_time / milvus_time if milvus_time > 0 else 0,
                "es_result_count": len(es_results['hits']['hits']),
                "milvus_result_count": len(milvus_results)
            }

            logger.info(f"📊 性能对比 - ES: {es_time:.3f}s, Milvus: {milvus_time:.3f}s, 加速比: {comparison['speedup_ratio']:.2f}x")

            return comparison

        except Exception as e:
            logger.error(f"❌ 性能对比失败: {e}")
            return {"error": str(e)}

    async def _log_migration_result(self, result: MigrationResult, performance_comparison: Dict[str, Any]) -> None:
        """记录迁移结果"""
        try:
            migration_log = {
                "user_id": result.user_id,
                "timestamp": datetime.now().isoformat(),
                "total_migrated": result.total_migrated,
                "success_rate": result.success_count / result.total_migrated if result.total_migrated > 0 else 0,
                "validation_passed": result.validation_passed,
                "migration_time": result.migration_time,
                "performance_comparison": performance_comparison,
                "errors_count": len(result.errors)
            }

            logger.info(f"📋 迁移结果记录: {json.dumps(migration_log, indent=2)}")

        except Exception as e:
            logger.error(f"记录迁移结果失败: {e}")

    async def incremental_sync(self, user_id: int, last_sync_time: datetime) -> bool:
        """增量数据同步"""
        try:
            logger.info(f"开始增量数据同步 - 用户: {user_id}, 上次同步: {last_sync_time}")

            # 获取新增数据
            new_data_query = {
                "query": {
                    "range": {
                        "create_timestamp_flt": {
                            "gt": last_sync_time.timestamp()
                        }
                    }
                },
                "size": 1000,
                "sort": [{"create_timestamp_flt": "asc"}]
            }

            new_data_response = await self.es_client.search(
                index=str(user_id),
                body=new_data_query,
                scroll="2m"
            )

            new_data_count = 0
            scroll_id = new_data_response.get('_scroll_id')
            hits = new_data_response['hits']['hits']

            while hits:
                # 处理新增数据
                for hit in hits:
                    await self._process_new_document(hit, user_id)
                    new_data_count += 1

                # 获取下一批
                scroll_response = await self.es_client.scroll(
                    scroll_id=scroll_id,
                    scroll="2m"
                )
                hits = scroll_response['hits']['hits']

            # 获取更新数据
            updated_data_query = {
                "query": {
                    "bool": {
                        "must": [
                            {"range": {"create_timestamp_flt": {"lte": last_sync_time.timestamp()}}},
                            {"range": {"update_timestamp_flt": {"gt": last_sync_time.timestamp()}}}
                        ]
                    }
                },
                "size": 1000
            }

            # 处理更新数据
            updated_data_response = await self.es_client.search(
                index=str(user_id),
                body=updated_data_query
            )

            updated_data_count = 0
            for hit in updated_data_response['hits']['hits']:
                await self._process_updated_document(hit, user_id)
                updated_data_count += 1

            logger.info(f"✅ 增量同步完成 - 新增: {new_data_count}, 更新: {updated_data_count}")
            return True

        except Exception as e:
            logger.error(f"❌ 增量同步失败: {e}")
            return False

    async def _process_new_document(self, hit: Dict[str, Any], user_id: int) -> None:
        """处理新增文档"""
        try:
            # 转换数据格式
            milvus_record = self._convert_es_to_milvus(hit)

            # 插入到Milvus
            collection_name = f"user_{user_id}_documents"
            chunk = DocumentChunk(**milvus_record)
            await self.milvus_service.insert_data(collection_name, [chunk])

        except Exception as e:
            logger.error(f"处理新增文档失败: {e}")

    async def _process_updated_document(self, hit: Dict[str, Any], user_id: int) -> None:
        """处理更新文档"""
        try:
            es_id = hit['_id']
            collection_name = f"user_{user_id}_documents"

            # 删除旧记录
            await self.milvus_service.query(
                collection_name=collection_name,
                filter_expr=f'chunk_id == "{es_id}"',
                output_fields=["id"],
                limit=1
            )

            # 插入更新后的记录
            milvus_record = self._convert_es_to_milvus(hit)
            chunk = DocumentChunk(**milvus_record)
            await self.milvus_service.insert_data(collection_name, [chunk])

        except Exception as e:
            logger.error(f"处理更新文档失败: {e}")

    async def rollback_migration(self, user_id: int) -> bool:
        """回滚迁移"""
        try:
            logger.warning(f"正在回滚用户 {user_id} 的迁移")

            collection_name = f"user_{user_id}_documents"

            # 删除Milvus中的数据
            await self.milvus_service.delete_collection(collection_name)

            logger.info(f"✅ 回滚完成 - 已删除集合: {collection_name}")
            return True

        except Exception as e:
            logger.error(f"❌ 回滚失败: {e}")
            return False

    async def cleanup(self) -> None:
        """清理资源"""
        try:
            logger.info("正在清理迁移服务资源")
            self.executor.shutdown(wait=True)
            logger.info("✅ 迁移服务资源清理完成")
        except Exception as e:
            logger.error(f"清理资源失败: {e}")

    def get_migration_status(self, user_id: int) -> Dict[str, Any]:
        """获取迁移状态"""
        try:
            collection_name = f"user_{user_id}_documents"

            # 检查集合是否存在
            if not utility.has_collection(collection_name):
                return {
                    "status": "not_started",
                    "milvus_count": 0,
                    "es_count": 0,
                    "progress": 0
                }

            # 获取Milvus数据数量
            milvus_stats = self.milvus_service.get_collection_stats(collection_name)
            milvus_count = milvus_stats.get('num_entities', 0)

            # 获取ES数据数量
            # 这里需要异步调用，但在同步方法中无法使用await
            # 返回异步方法调用所需的信息
            return {
                "status": "completed" if milvus_count > 0 else "in_progress",
                "milvus_count": milvus_count,
                "collection_name": collection_name,
                "user_id": user_id
            }

        except Exception as e:
            logger.error(f"获取迁移状态失败: {e}")
            return {"status": "error", "error": str(e)}
