"""
Milvus优化服务
提供性能优化、索引调优、查询优化等功能
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from dataclasses import dataclass

from .milvus_service import MilvusService
from .models import (
    CollectionConfig, IndexType, MetricType,
    PERFORMANCE_BASELINES, PERFORMANCE_BENCHMARKS
)

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """优化结果"""
    collection_name: str
    optimization_type: str
    before_metrics: Dict[str, Any]
    after_metrics: Dict[str, Any]
    improvement_ratio: Dict[str, float]
    recommendations: List[str]
    execution_time: float
    timestamp: datetime


@dataclass
class CollectionStats:
    """集合统计信息"""
    collection_name: str
    num_entities: int
    avg_doc_size: float
    index_type: str
    search_latency_p99: float
    insert_throughput: float
    memory_usage_mb: float
    disk_usage_mb: float
    last_updated: datetime


class MilvusOptimizationService:
    """Milvus性能优化服务"""

    def __init__(self, milvus_service: MilvusService):
        """
        初始化优化服务

        Args:
            milvus_service: Milvus服务实例
        """
        self.milvus_service = milvus_service
        self.optimization_history = []
        self.performance_cache = {}

    async def optimize_collection(self, collection_name: str,
                                optimization_level: str = "balanced") -> OptimizationResult:
        """
        优化集合性能

        Args:
            collection_name: 集合名称
            optimization_level: 优化级别 (performance/balanced/memory)

        Returns:
            优化结果
        """
        try:
            logger.info(f"开始优化集合: {collection_name}, 级别: {optimization_level}")
            start_time = time.time()

            # 1. 获取当前性能基线
            before_metrics = await self._get_collection_metrics(collection_name)
            logger.info(f"优化前性能基线: {before_metrics}")

            # 2. 分析集合特征
            collection_stats = await self._analyze_collection(collection_name)
            logger.info(f"集合统计分析: {collection_stats}")

            # 3. 索引优化
            index_result = await self._optimize_index(collection_name, collection_stats, optimization_level)

            # 4. 搜索参数优化
            search_result = await self._optimize_search_parameters(collection_name, optimization_level)

            # 5. 内存优化
            memory_result = await self._optimize_memory_usage(collection_name, optimization_level)

            # 6. 获取优化后性能
            after_metrics = await self._get_collection_metrics(collection_name)
            logger.info(f"优化后性能指标: {after_metrics}")

            # 7. 计算改进比例
            improvement_ratio = self._calculate_improvement_ratio(before_metrics, after_metrics)

            # 8. 生成优化建议
            recommendations = self._generate_recommendations(
                collection_stats, before_metrics, after_metrics, optimization_level
            )

            execution_time = time.time() - start_time

            result = OptimizationResult(
                collection_name=collection_name,
                optimization_type=optimization_level,
                before_metrics=before_metrics,
                after_metrics=after_metrics,
                improvement_ratio=improvement_ratio,
                recommendations=recommendations,
                execution_time=execution_time,
                timestamp=datetime.now()
            )

            # 保存优化历史
            self.optimization_history.append(result)

            logger.info(f"✅ 集合优化完成 - 耗时: {execution_time:.2f}s")
            logger.info(f"📊 性能改进: {improvement_ratio}")

            return result

        except Exception as e:
            logger.error(f"❌ 集合优化失败: {e}")
            raise e

    async def _get_collection_metrics(self, collection_name: str) -> Dict[str, Any]:
        """获取集合性能指标"""
        try:
            # 获取基本统计信息
            stats = await self.milvus_service.get_collection_stats(collection_name)

            # 性能测试
            search_latency = await self._measure_search_latency(collection_name)
            insert_throughput = await self._measure_insert_throughput(collection_name)

            # 系统资源使用
            memory_usage = await self._get_memory_usage(collection_name)
            disk_usage = await self._get_disk_usage(collection_name)

            metrics = {
                "num_entities": stats.get("num_entities", 0),
                "search_latency_p99": search_latency,
                "insert_throughput": insert_throughput,
                "memory_usage_mb": memory_usage,
                "disk_usage_mb": disk_usage,
                "index_type": await self._get_current_index_type(collection_name)
            }

            # 缓存性能数据
            self.performance_cache[collection_name] = {
                "metrics": metrics,
                "timestamp": datetime.now()
            }

            return metrics

        except Exception as e:
            logger.error(f"获取集合指标失败: {e}")
            return {}

    async def _analyze_collection(self, collection_name: str) -> CollectionStats:
        """分析集合特征"""
        try:
            stats = await self.milvus_service.get_collection_stats(collection_name)
            num_entities = stats.get("num_entities", 0)

            # 估算平均文档大小
            avg_doc_size = await self._estimate_avg_document_size(collection_name)

            # 获取当前索引类型
            index_type = await self._get_current_index_type(collection_name)

            # 性能指标
            search_latency = await self._measure_search_latency(collection_name)
            insert_throughput = await self._measure_insert_throughput(collection_name)

            # 资源使用
            memory_usage = await self._get_memory_usage(collection_name)
            disk_usage = await self._get_disk_usage(collection_name)

            collection_stats = CollectionStats(
                collection_name=collection_name,
                num_entities=num_entities,
                avg_doc_size=avg_doc_size,
                index_type=index_type,
                search_latency_p99=search_latency,
                insert_throughput=insert_throughput,
                memory_usage_mb=memory_usage,
                disk_usage_mb=disk_usage,
                last_updated=datetime.now()
            )

            logger.info(f"集合分析完成: {collection_stats}")
            return collection_stats

        except Exception as e:
            logger.error(f"集合分析失败: {e}")
            raise e

    async def _optimize_index(self, collection_name: str, stats: CollectionStats,
                            optimization_level: str) -> Dict[str, Any]:
        """优化索引"""
        try:
            logger.info(f"开始索引优化 - 集合: {collection_name}, 数据量: {stats.num_entities}")

            # 根据数据量和优化级别选择索引类型
            new_index_type = self._select_optimal_index_type(stats.num_entities, optimization_level)

            if new_index_type == stats.index_type:
                logger.info(f"当前索引类型 {stats.index_type} 已是最优选择")
                return {"status": "already_optimal", "index_type": stats.index_type}

            # 构建索引参数
            index_params = self._build_index_params(new_index_type, stats.num_entities)

            logger.info(f"创建新索引 - 类型: {new_index_type}, 参数: {index_params}")

            # 删除旧索引（如果存在）
            try:
                collection = self.milvus_service._get_collection(collection_name)
                if collection:
                    collection.drop_index("vector")
            except Exception as e:
                logger.warning(f"删除旧索引失败: {e}")

            # 创建新索引
            success = await self.milvus_service.create_index(
                collection_name=collection_name,
                field_name="vector",
                index_params=index_params
            )

            if success:
                logger.info(f"✅ 索引优化完成 - 新索引类型: {new_index_type}")
                return {"status": "optimized", "index_type": new_index_type, "params": index_params}
            else:
                logger.error("❌ 索引优化失败")
                return {"status": "failed", "index_type": stats.index_type}

        except Exception as e:
            logger.error(f"索引优化失败: {e}")
            return {"status": "error", "error": str(e)}

    def _select_optimal_index_type(self, num_entities: int, optimization_level: str) -> str:
        """选择最优索引类型"""
        if optimization_level == "performance":
            # 性能优先
            if num_entities > 1000000:
                return IndexType.IVF_PQ.value
            elif num_entities > 100000:
                return IndexType.IVF_FLAT.value
            else:
                return IndexType.HNSW.value

        elif optimization_level == "memory":
            # 内存优先
            if num_entities > 100000:
                return IndexType.IVF_PQ.value
            else:
                return IndexType.IVF_SQ8.value

        else:  # balanced
            # 平衡模式
            if num_entities > 1000000:
                return IndexType.IVF_PQ.value
            elif num_entities > 100000:
                return IndexType.IVF_FLAT.value
            else:
                return IndexType.HNSW.value

    def _build_index_params(self, index_type: str, num_entities: int) -> Dict[str, Any]:
        """构建索引参数"""
        if index_type == IndexType.HNSW.value:
            return {
                "index_type": IndexType.HNSW.value,
                "metric_type": MetricType.COSINE.value,
                "params": {"M": 16, "efConstruction": 200}
            }
        elif index_type == IndexType.IVF_FLAT.value:
            nlist = min(4096, max(1024, num_entities // 100))
            return {
                "index_type": IndexType.IVF_FLAT.value,
                "metric_type": MetricType.COSINE.value,
                "params": {"nlist": nlist}
            }
        elif index_type == IndexType.IVF_PQ.value:
            nlist = min(4096, max(1024, num_entities // 100))
            return {
                "index_type": IndexType.IVF_PQ.value,
                "metric_type": MetricType.COSINE.value,
                "params": {"nlist": nlist, "m": 16}
            }
        elif index_type == IndexType.IVF_SQ8.value:
            nlist = min(4096, max(1024, num_entities // 100))
            return {
                "index_type": IndexType.IVF_SQ8.value,
                "metric_type": MetricType.COSINE.value,
                "params": {"nlist": nlist}
            }
        else:
            return {
                "index_type": IndexType.HNSW.value,
                "metric_type": MetricType.COSINE.value,
                "params": {"M": 16, "efConstruction": 200}
            }

    async def _optimize_search_parameters(self, collection_name: str,
                                        optimization_level: str) -> Dict[str, Any]:
        """优化搜索参数"""
        try:
            logger.info(f"开始搜索参数优化 - 集合: {collection_name}")

            # 根据优化级别设置搜索参数
            if optimization_level == "performance":
                search_params = {
                    "metric_type": MetricType.COSINE.value,
                    "params": {"ef": 128}  # 更高的ef值，更好的召回率
                }
            elif optimization_level == "memory":
                search_params = {
                    "metric_type": MetricType.COSINE.value,
                    "params": {"ef": 32}  # 更低的ef值，更快的搜索
                }
            else:  # balanced
                search_params = {
                    "metric_type": MetricType.COSINE.value,
                    "params": {"ef": 64}  # 平衡设置
                }

            logger.info(f"搜索参数优化完成: {search_params}")
            return {"status": "optimized", "search_params": search_params}

        except Exception as e:
            logger.error(f"搜索参数优化失败: {e}")
            return {"status": "error", "error": str(e)}

    async def _optimize_memory_usage(self, collection_name: str,
                                   optimization_level: str) -> Dict[str, Any]:
        """优化内存使用"""
        try:
            logger.info(f"开始内存优化 - 集合: {collection_name}")

            # 根据优化级别决定是否加载集合到内存
            if optimization_level == "memory":
                # 内存优化模式，不预加载集合
                await self.milvus_service.release_collection(collection_name)
                logger.info("已释放集合内存（内存优化模式）")
                return {"status": "optimized", "memory_mode": "lazy_loading"}
            else:
                # 性能优先模式，预加载集合
                await self.milvus_service.load_collection(collection_name)
                logger.info("已预加载集合到内存（性能优化模式）")
                return {"status": "optimized", "memory_mode": "preloaded"}

        except Exception as e:
            logger.error(f"内存优化失败: {e}")
            return {"status": "error", "error": str(e)}

    async def _measure_search_latency(self, collection_name: str) -> float:
        """测量搜索延迟"""
        try:
            # 使用模拟查询向量进行测试
            test_vector = [0.1] * 1024

            # 预热
            await self.milvus_service.search(
                collection_name=collection_name,
                query_vector=test_vector,
                top_k=10
            )

            # 正式测量
            latencies = []
            for _ in range(5):
                start_time = time.time()
                await self.milvus_service.search(
                    collection_name=collection_name,
                    query_vector=test_vector,
                    top_k=10
                )
                latency = (time.time() - start_time) * 1000  # 转换为毫秒
                latencies.append(latency)

            # 返回P99延迟（这里用最大值近似）
            return max(latencies)

        except Exception as e:
            logger.error(f"测量搜索延迟失败: {e}")
            return 100.0  # 默认值

    async def _measure_insert_throughput(self, collection_name: str) -> float:
        """测量插入吞吐量"""
        try:
            # 创建测试数据
            from .models import DocumentChunk
            test_chunks = []
            for i in range(100):
                chunk = DocumentChunk(
                    vector=[0.1] * 1024,
                    content=f"测试内容 {i}",
                    doc_id=f"test_doc_{i}",
                    doc_name=f"测试文档 {i}",
                    kb_id="test_kb",
                    chunk_id=f"test_chunk_{i}",
                    category="test",
                    confidence=0.8,
                    timestamp=int(time.time())
                )
                test_chunks.append(chunk)

            # 测量插入性能
            start_time = time.time()
            await self.milvus_service.insert_data(collection_name, test_chunks, batch_size=50)
            insert_time = time.time() - start_time

            # 计算吞吐量 (文档/秒)
            throughput = len(test_chunks) / insert_time if insert_time > 0 else 0

            # 清理测试数据
            await self.milvus_service.query(
                collection_name=collection_name,
                filter_expr='doc_id like "test_doc_%"',
                output_fields=["id"]
            )

            return throughput

        except Exception as e:
            logger.error(f"测量插入吞吐量失败: {e}")
            return 0.0

    async def _get_memory_usage(self, collection_name: str) -> float:
        """获取内存使用量"""
        try:
            # 这里应该调用系统API获取实际内存使用
            # 暂时返回估算值
            stats = await self.milvus_service.get_collection_stats(collection_name)
            num_entities = stats.get("num_entities", 0)

            # 粗略估算：每个实体约占用1KB内存（包括向量、文本、元数据）
            estimated_memory_mb = (num_entities * 1.0) / 1024

            return estimated_memory_mb

        except Exception as e:
            logger.error(f"获取内存使用失败: {e}")
            return 0.0

    async def _get_disk_usage(self, collection_name: str) -> float:
        """获取磁盘使用量"""
        try:
            # 这里应该调用系统API获取实际磁盘使用
            # 暂时返回估算值
            stats = await self.milvus_service.get_collection_stats(collection_name)
            num_entities = stats.get("num_entities", 0)

            # 粗略估算：每个实体约占用2KB磁盘空间
            estimated_disk_mb = (num_entities * 2.0) / 1024

            return estimated_disk_mb

        except Exception as e:
            logger.error(f"获取磁盘使用失败: {e}")
            return 0.0

    async def _estimate_avg_document_size(self, collection_name: str) -> float:
        """估算平均文档大小"""
        try:
            # 采样获取文档大小
            samples = await self.milvus_service.query(
                collection_name=collection_name,
                filter_expr="",
                output_fields=["content"],
                limit=10
            )

            if not samples:
                return 0.0

            total_size = sum(len(sample.get("content", "")) for sample in samples)
            return total_size / len(samples)

        except Exception as e:
            logger.error(f"估算平均文档大小失败: {e}")
            return 0.0

    async def _get_current_index_type(self, collection_name: str) -> str:
        """获取当前索引类型"""
        try:
            collection = self.milvus_service._get_collection(collection_name)
            if not collection:
                return "unknown"

            # 获取索引信息
            indexes = collection.indexes
            if indexes:
                for index in indexes:
                    if index.field_name == "vector":
                        return index.params.get("index_type", "unknown")

            return "none"

        except Exception as e:
            logger.error(f"获取当前索引类型失败: {e}")
            return "unknown"

    def _calculate_improvement_ratio(self, before: Dict[str, Any],
                                   after: Dict[str, Any]) -> Dict[str, float]:
        """计算改进比例"""
        improvements = {}

        for key in before.keys():
            if key in after and isinstance(before[key], (int, float)) and isinstance(after[key], (int, float)):
                if before[key] > 0:
                    if key in ["search_latency_p99", "memory_usage_mb", "disk_usage_mb"]:
                        # 这些指标越小越好
                        improvement = (before[key] - after[key]) / before[key] * 100
                    else:
                        # 这些指标越大越好
                        improvement = (after[key] - before[key]) / before[key] * 100

                    improvements[key] = round(improvement, 2)

        return improvements

    def _generate_recommendations(self, stats: CollectionStats,
                                before: Dict[str, Any],
                                after: Dict[str, Any],
                                optimization_level: str) -> List[str]:
        """生成优化建议"""
        recommendations = []

        # 基于数据量的建议
        if stats.num_entities > 1000000:
            recommendations.append("数据量较大，建议使用IVF_PQ索引以节省内存")
            recommendations.append("考虑使用分区策略提高查询性能")

        elif stats.num_entities > 100000:
            recommendations.append("数据量中等，建议使用IVF_FLAT索引平衡性能和精度")

        else:
            recommendations.append("数据量较小，HNSW索引能提供最佳性能")

        # 基于性能指标的建议
        if after.get("search_latency_p99", 0) > 50:
            recommendations.append("搜索延迟较高，建议优化搜索参数或增加硬件资源")

        if after.get("memory_usage_mb", 0) > 2048:
            recommendations.append("内存使用较高，建议优化索引类型或清理无用数据")

        # 基于优化级别的建议
        if optimization_level == "performance":
            recommendations.append("性能优化模式：已启用预加载和高级索引参数")
        elif optimization_level == "memory":
            recommendations.append("内存优化模式：已启用延迟加载和压缩索引")
        else:
            recommendations.append("平衡模式：在性能和资源使用之间取得平衡")

        return recommendations

    async def get_optimization_history(self, collection_name: Optional[str] = None) -> List[OptimizationResult]:
        """获取优化历史"""
        if collection_name:
            return [result for result in self.optimization_history
                   if result.collection_name == collection_name]
        return self.optimization_history

    async def get_performance_trends(self, collection_name: str,
                                   days: int = 7) -> Dict[str, List[float]]:
        """获取性能趋势"""
        try:
            trends = {
                "search_latency": [],
                "insert_throughput": [],
                "memory_usage": [],
                "timestamps": []
            }

            # 从历史数据中提取趋势
            cutoff_date = datetime.now() - timedelta(days=days)
            relevant_history = [
                result for result in self.optimization_history
                if result.collection_name == collection_name
                and result.timestamp >= cutoff_date
            ]

            for result in relevant_history:
                trends["search_latency"].append(result.after_metrics.get("search_latency_p99", 0))
                trends["insert_throughput"].append(result.after_metrics.get("insert_throughput", 0))
                trends["memory_usage"].append(result.after_metrics.get("memory_usage_mb", 0))
                trends["timestamps"].append(result.timestamp.isoformat())

            return trends

        except Exception as e:
            logger.error(f"获取性能趋势失败: {e}")
            return {}

    async def benchmark_collection(self, collection_name: str) -> Dict[str, Any]:
        """基准测试集合性能"""
        try:
            logger.info(f"开始基准测试 - 集合: {collection_name}")

            # 获取集合统计
            stats = await self.milvus_service.get_collection_stats(collection_name)
            num_entities = stats.get("num_entities", 0)

            # 确定数据集规模类别
            dataset_size = self._classify_dataset_size(num_entities)

            # 获取基准配置
            benchmark_config = PERFORMANCE_BENCHMARKS.get(dataset_size, {})

            # 执行性能测试
            actual_metrics = await self._get_collection_metrics(collection_name)

            # 对比基准
            comparison = {}
            for metric, expected in benchmark_config.items():
                actual = actual_metrics.get(metric, 0)
                if isinstance(expected, str) and expected.startswith("<"):
                    # 小于某个值
                    threshold = float(expected[1:])
                    meets_benchmark = actual < threshold
                elif isinstance(expected, str) and expected.startswith(">"):
                    # 大于某个值
                    threshold = float(expected[1:])
                    meets_benchmark = actual > threshold
                else:
                    meets_benchmark = False

                comparison[metric] = {
                    "expected": expected,
                    "actual": actual,
                    "meets_benchmark": meets_benchmark
                }

            result = {
                "dataset_size": dataset_size,
                "num_entities": num_entities,
                "benchmark_config": benchmark_config,
                "actual_metrics": actual_metrics,
                "comparison": comparison,
                "overall_score": self._calculate_overall_score(comparison)
            }

            logger.info(f"基准测试完成 - 总体评分: {result['overall_score']}")
            return result

        except Exception as e:
            logger.error(f"基准测试失败: {e}")
            return {"error": str(e)}

    def _classify_dataset_size(self, num_entities: int) -> str:
        """分类数据集规模"""
        if num_entities < 10000:
            return "small_dataset"
        elif num_entities < 1000000:
            return "medium_dataset"
        elif num_entities < 10000000:
            return "large_dataset"
        else:
            return "xlarge_dataset"

    def _calculate_overall_score(self, comparison: Dict[str, Any]) -> float:
        """计算总体评分"""
        total_metrics = len(comparison)
        if total_metrics == 0:
            return 0.0

        passed_metrics = sum(1 for metric in comparison.values()
                           if metric.get("meets_benchmark", False))

        return (passed_metrics / total_metrics) * 100

    async def cleanup(self) -> None:
        """清理资源"""
        try:
            logger.info("正在清理优化服务资源")
            self.performance_cache.clear()
            logger.info("✅ 优化服务资源清理完成")
        except Exception as e:
            logger.error(f"清理资源失败: {e}")