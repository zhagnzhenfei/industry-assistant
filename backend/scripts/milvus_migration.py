#!/usr/bin/env python3
"""
Milvus迁移脚本
执行从Elasticsearch到Milvus的完整数据迁移
"""

import asyncio
import argparse
import logging
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.milvus import (
    MilvusService, DataMigrationService, HybridSearchService, MilvusOptimizationService
)
from app.services.milvus.models import MigrationResult
from elasticsearch import AsyncElasticsearch

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'milvus_migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)


class MilvusMigrationManager:
    """Milvus迁移管理器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化迁移管理器

        Args:
            config: 迁移配置
        """
        self.config = config
        self.milvus_service = None
        self.es_client = None
        self.migration_service = None
        self.hybrid_search_service = None
        self.optimization_service = None

    async def initialize_services(self):
        """初始化所有服务"""
        try:
            logger.info("正在初始化迁移服务...")

            # 1. 初始化Milvus服务
            self.milvus_service = MilvusService(
                host=self.config['milvus']['host'],
                port=self.config['milvus']['port'],
                user=self.config['milvus'].get('user', ''),
                password=self.config['milvus'].get('password', ''),
                db_name=self.config['milvus'].get('db_name', 'default')
            )

            # 连接到Milvus
            milvus_connected = await self.milvus_service.connect()
            if not milvus_connected:
                raise Exception("无法连接到Milvus服务器")

            logger.info("✅ Milvus服务初始化完成")

            # 2. 初始化ES客户端
            self.es_client = AsyncElasticsearch(
                hosts=[{
                    'host': self.config['elasticsearch']['host'],
                    'port': self.config['elasticsearch']['port'],
                    'scheme': 'http'
                }],
                basic_auth=(
                    self.config['elasticsearch'].get('user', ''),
                    self.config['elasticsearch'].get('password', '')
                ) if self.config['elasticsearch'].get('user') else None
            )

            # 测试ES连接
            es_connected = await self.es_client.ping()
            if not es_connected:
                raise Exception("无法连接到Elasticsearch服务器")

            logger.info("✅ Elasticsearch服务初始化完成")

            # 3. 初始化迁移服务
            self.migration_service = DataMigrationService(
                es_client=self.es_client,
                milvus_service=self.milvus_service,
                batch_size=self.config['migration']['batch_size'],
                max_workers=self.config['migration']['max_workers'],
                validation_sample_rate=self.config['migration']['validation_sample_rate']
            )

            logger.info("✅ 数据迁移服务初始化完成")

            # 4. 初始化混合搜索服务
            self.hybrid_search_service = HybridSearchService(
                milvus_service=self.milvus_service,
                es_client=self.es_client,
                vector_weight=self.config['search']['vector_weight'],
                text_weight=self.config['search']['text_weight']
            )

            logger.info("✅ 混合搜索服务初始化完成")

            # 5. 初始化优化服务
            self.optimization_service = MilvusOptimizationService(self.milvus_service)

            logger.info("✅ 优化服务初始化完成")
            logger.info("🎉 所有服务初始化成功")

        except Exception as e:
            logger.error(f"服务初始化失败: {e}")
            raise e

    async def migrate_user(self, user_id: int, dry_run: bool = False) -> MigrationResult:
        """
        迁移单个用户的数据

        Args:
            user_id: 用户ID
            dry_run: 是否只进行预检查

        Returns:
            迁移结果
        """
        try:
            logger.info(f"{'[预检查] ' if dry_run else ''}开始迁移用户 {user_id} 的数据...")

            if dry_run:
                # 预检查模式
                result = await self._dry_run_migration(user_id)
            else:
                # 实际迁移
                result = await self.migration_service.migrate_user_data(user_id)

            logger.info(f"用户 {user_id} 迁移完成:")
            logger.info(f"  📊 总记录数: {result.total_migrated}")
            logger.info(f"  ✅ 成功: {result.success_count}")
            logger.info(f"  ❌ 失败: {result.failed_count}")
            logger.info(f"  ✓ 验证通过: {result.validation_passed}")
            logger.info(f"  ⏱️  耗时: {result.migration_time:.2f}秒")

            if result.errors:
                logger.error(f"  ⚠️  错误数: {len(result.errors)}")
                for i, error in enumerate(result.errors[:5]):  # 只显示前5个错误
                    logger.error(f"    - {error}")

            return result

        except Exception as e:
            logger.error(f"用户 {user_id} 迁移失败: {e}")
            return MigrationResult(
                user_id=str(user_id),
                total_migrated=0,
                success_count=0,
                failed_count=0,
                validation_passed=False,
                migration_time=0.0,
                start_time=datetime.now(),
                end_time=datetime.now(),
                errors=[str(e)]
            )

    async def _dry_run_migration(self, user_id: int) -> MigrationResult:
        """预检查迁移"""
        try:
            logger.info(f"执行用户 {user_id} 的预检查...")

            # 1. 检查ES中的数据
            es_stats = await self.migration_service.get_es_statistics(user_id)
            total_documents = es_stats.get('total_documents', 0)

            if total_documents == 0:
                logger.warning(f"用户 {user_id} 在ES中没有数据")
                return MigrationResult(
                    user_id=str(user_id),
                    total_migrated=0,
                    success_count=0,
                    failed_count=0,
                    validation_passed=False,
                    migration_time=0.0,
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    errors=["No data found in Elasticsearch"]
                )

            logger.info(f"预检查通过 - 发现 {total_documents} 条记录")

            # 2. 检查Milvus连接
            health_check = await self.milvus_service.health_check()
            if health_check.get("status") != "healthy":
                raise Exception("Milvus服务不健康")

            # 3. 模拟迁移结果
            return MigrationResult(
                user_id=str(user_id),
                total_migrated=total_documents,
                success_count=total_documents,
                failed_count=0,
                validation_passed=True,
                migration_time=0.0,
                start_time=datetime.now(),
                end_time=datetime.now(),
                errors=[]
            )

        except Exception as e:
            logger.error(f"预检查失败: {e}")
            return MigrationResult(
                user_id=str(user_id),
                total_migrated=0,
                success_count=0,
                failed_count=0,
                validation_passed=False,
                migration_time=0.0,
                start_time=datetime.now(),
                end_time=datetime.now(),
                errors=[str(e)]
            )

    async def migrate_multiple_users(self, user_ids: List[int],
                                   batch_size: int = 1,
                                   dry_run: bool = False) -> Dict[str, Any]:
        """
        批量迁移多个用户

        Args:
            user_ids: 用户ID列表
            batch_size: 并发批次大小
            dry_run: 是否只进行预检查

        Returns:
            批量迁移结果
        """
        try:
            total_users = len(user_ids)
            logger.info(f"开始批量迁移 {total_users} 个用户...")

            results = []
            failed_users = []
            start_time = datetime.now()

            # 分批处理
            for i in range(0, total_users, batch_size):
                batch = user_ids[i:i + batch_size]
                logger.info(f"处理批次 {i//batch_size + 1}/{(total_users + batch_size - 1)//batch_size}")

                # 并发处理当前批次
                batch_tasks = [
                    self.migrate_user(user_id, dry_run) for user_id in batch
                ]
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

                # 处理结果
                for user_id, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        logger.error(f"用户 {user_id} 迁移异常: {result}")
                        failed_users.append(user_id)
                        results.append(MigrationResult(
                            user_id=str(user_id),
                            total_migrated=0,
                            success_count=0,
                            failed_count=0,
                            validation_passed=False,
                            migration_time=0.0,
                            start_time=datetime.now(),
                            end_time=datetime.now(),
                            errors=[str(result)]
                        ))
                    else:
                        results.append(result)
                        if not result.validation_passed or result.failed_count > 0:
                            failed_users.append(user_id)

            end_time = datetime.now()
            total_time = (end_time - start_time).total_seconds()

            # 统计汇总
            total_migrated = sum(r.total_migrated for r in results)
            total_success = sum(r.success_count for r in results)
            total_failed = sum(r.failed_count for r in results)

            summary = {
                "total_users": total_users,
                "successful_users": total_users - len(failed_users),
                "failed_users": len(failed_users),
                "total_migrated": total_migrated,
                "total_success": total_success,
                "total_failed": total_failed,
                "success_rate": (total_users - len(failed_users)) / total_users * 100 if total_users > 0 else 0,
                "total_time": total_time,
                "failed_user_ids": failed_users,
                "individual_results": results
            }

            logger.info(f"批量迁移完成:")
            logger.info(f"  📊 总用户数: {summary['total_users']}")
            logger.info(f"  ✅ 成功用户: {summary['successful_users']}")
            logger.info(f"  ❌ 失败用户: {summary['failed_users']}")
            logger.info(f"  📈 成功率: {summary['success_rate']:.1f}%")
            logger.info(f"  📋 总记录数: {summary['total_migrated']}")
            logger.info(f"  ⏱️  总耗时: {summary['total_time']:.2f}秒")

            return summary

        except Exception as e:
            logger.error(f"批量迁移失败: {e}")
            raise e

    async def optimize_collections(self, collection_names: List[str],
                                 optimization_level: str = "balanced") -> Dict[str, Any]:
        """
        优化多个集合

        Args:
            collection_names: 集合名称列表
            optimization_level: 优化级别

        Returns:
            优化结果汇总
        """
        try:
            logger.info(f"开始优化 {len(collection_names)} 个集合...")

            optimization_results = []
            start_time = datetime.now()

            # 逐个优化集合
            for collection_name in collection_names:
                try:
                    logger.info(f"优化集合: {collection_name}")
                    result = await self.optimization_service.optimize_collection(
                        collection_name, optimization_level
                    )
                    optimization_results.append(result)
                except Exception as e:
                    logger.error(f"集合 {collection_name} 优化失败: {e}")

            end_time = datetime.now()
            total_time = (end_time - start_time).total_seconds()

            # 生成优化报告
            report = self._generate_optimization_report(optimization_results, total_time)

            logger.info(f"集合优化完成 - 总耗时: {total_time:.2f}秒")
            return report

        except Exception as e:
            logger.error(f"集合优化失败: {e}")
            raise e

    def _generate_optimization_report(self, results: List, total_time: float) -> Dict[str, Any]:
        """生成优化报告"""
        try:
            if not results:
                return {"status": "no_results", "total_time": total_time}

            # 统计改进情况
            total_improvements = {}
            recommendations = []

            for result in results:
                for metric, improvement in result.improvement_ratio.items():
                    if metric not in total_improvements:
                        total_improvements[metric] = []
                    total_improvements[metric].append(improvement)

                recommendations.extend(result.recommendations)

            # 计算平均改进
            avg_improvements = {}
            for metric, improvements in total_improvements.items():
                avg_improvements[metric] = sum(improvements) / len(improvements)

            report = {
                "total_collections": len(results),
                "total_time": total_time,
                "average_improvements": avg_improvements,
                "recommendations": list(set(recommendations)),  # 去重
                "individual_results": [result.__dict__ for result in results]
            }

            return report

        except Exception as e:
            logger.error(f"生成优化报告失败: {e}")
            return {"error": str(e), "total_time": total_time}

    async def test_search_performance(self, user_id: int, test_queries: List[str]) -> Dict[str, Any]:
        """
        测试搜索性能

        Args:
            user_id: 用户ID
            test_queries: 测试查询列表

        Returns:
            性能测试结果
        """
        try:
            logger.info(f"开始搜索性能测试 - 用户: {user_id}")

            results = {
                "user_id": user_id,
                "test_queries": [],
                "average_latency": 0.0,
                "total_tests": len(test_queries)
            }

            total_latency = 0.0

            # 执行测试查询
            for query in test_queries:
                try:
                    start_time = datetime.now()

                    # 执行混合搜索
                    search_request = type('SearchRequest', (), {
                        'query': query,
                        'kb_id': str(user_id),
                        'top_k': 10,
                        'offset': 0,
                        'similarity_threshold': None
                    })()

                    response = await self.hybrid_search_service.search(search_request)

                    end_time = datetime.now()
                    latency = (end_time - start_time).total_seconds() * 1000  # 转换为毫秒

                    total_latency += latency

                    test_result = {
                        "query": query,
                        "latency_ms": latency,
                        "results_count": len(response.results),
                        "success": True
                    }

                    results["test_queries"].append(test_result)
                    logger.info(f"查询 '{query}' - 延迟: {latency:.2f}ms, 结果数: {len(response.results)}")

                except Exception as e:
                    logger.error(f"查询 '{query}' 失败: {e}")
                    results["test_queries"].append({
                        "query": query,
                        "latency_ms": 0,
                        "results_count": 0,
                        "success": False,
                        "error": str(e)
                    })

            # 计算平均延迟
            successful_tests = [t for t in results["test_queries"] if t["success"]]
            if successful_tests:
                results["average_latency"] = total_latency / len(successful_tests)

            logger.info(f"性能测试完成 - 平均延迟: {results['average_latency']:.2f}ms")
            return results

        except Exception as e:
            logger.error(f"性能测试失败: {e}")
            return {"error": str(e)}

    async def cleanup(self):
        """清理资源"""
        try:
            logger.info("正在清理迁移管理器资源...")

            # 清理各服务
            if self.migration_service:
                await self.migration_service.cleanup()

            if self.hybrid_search_service:
                await self.hybrid_search_service.cleanup()

            if self.optimization_service:
                await self.optimization_service.cleanup()

            # 断开连接
            if self.milvus_service:
                await self.milvus_service.disconnect()

            if self.es_client:
                await self.es_client.close()

            logger.info("✅ 迁移管理器资源清理完成")

        except Exception as e:
            logger.error(f"清理资源失败: {e}")


def load_config(config_path: str) -> Dict[str, Any]:
    """加载配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logger.info(f"配置文件加载成功: {config_path}")
        return config
    except Exception as e:
        logger.error(f"配置文件加载失败: {e}")
        raise e


def save_results(results: Dict[str, Any], output_path: str):
    """保存结果到文件"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"结果已保存到: {output_path}")
    except Exception as e:
        logger.error(f"保存结果失败: {e}")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Milvus迁移脚本')
    parser.add_argument('--config', '-c', required=True, help='配置文件路径')
    parser.add_argument('--user-id', '-u', type=int, help='要迁移的用户ID')
    parser.add_argument('--user-ids', help='要迁移的用户ID列表（逗号分隔）')
    parser.add_argument('--dry-run', action='store_true', help='只进行预检查')
    parser.add_argument('--batch-size', type=int, default=1, help='并发批次大小')
    parser.add_argument('--optimize', action='store_true', help='迁移后优化集合')
    parser.add_argument('--test-search', action='store_true', help='测试搜索性能')
    parser.add_argument('--output', '-o', help='结果输出文件路径')

    args = parser.parse_args()

    try:
        # 加载配置
        config = load_config(args.config)

        # 创建迁移管理器
        migration_manager = MilvusMigrationManager(config)
        await migration_manager.initialize_services()

        # 执行迁移
        if args.user_id:
            # 单个用户迁移
            result = await migration_manager.migrate_user(args.user_id, args.dry_run)
            results = {"single_user": result}

        elif args.user_ids:
            # 多个用户迁移
            user_ids = [int(uid.strip()) for uid in args.user_ids.split(',')]
            results = await migration_manager.migrate_multiple_users(
                user_ids, args.batch_size, args.dry_run
            )

        else:
            logger.error("必须指定 --user-id 或 --user-ids")
            return

        # 后续处理
        if not args.dry_run:
            # 获取迁移的集合列表
            migrated_collections = []
            if args.user_id:
                migrated_collections.append(f"user_{args.user_id}_documents")
            elif args.user_ids:
                user_ids = [int(uid.strip()) for uid in args.user_ids.split(',')]
                migrated_collections = [f"user_{uid}_documents" for uid in user_ids]

            # 优化集合
            if args.optimize and migrated_collections:
                logger.info("开始优化集合...")
                optimization_report = await migration_manager.optimize_collections(
                    migrated_collections, optimization_level="balanced"
                )
                results["optimization"] = optimization_report

            # 测试搜索性能
            if args.test_search and args.user_id:
                logger.info("开始测试搜索性能...")
                test_queries = [
                    "人工智能技术发展",
                    "机器学习算法",
                    "深度学习应用",
                    "自然语言处理",
                    "计算机视觉技术"
                ]
                performance_results = await migration_manager.test_search_performance(
                    args.user_id, test_queries
                )
                results["performance_test"] = performance_results

        # 保存结果
        if args.output:
            save_results(results, args.output)

        # 打印结果摘要
        print("\n" + "="*60)
        print("迁移结果摘要")
        print("="*60)

        if args.user_id:
            result = results["single_user"]
            print(f"用户ID: {result.user_id}")
            print(f"总记录数: {result.total_migrated}")
            print(f"成功: {result.success_count}")
            print(f"失败: {result.failed_count}")
            print(f"验证通过: {result.validation_passed}")
            print(f"耗时: {result.migration_time:.2f}秒")
        else:
            summary = results
            print(f"总用户数: {summary['total_users']}")
            print(f"成功用户: {summary['successful_users']}")
            print(f"失败用户: {summary['failed_users']}")
            print(f"成功率: {summary['success_rate']:.1f}%")
            print(f"总记录数: {summary['total_migrated']}")
            print(f"总耗时: {summary['total_time']:.2f}秒")

        print("="*60)

    except Exception as e:
        logger.error(f"迁移过程失败: {e}")
        sys.exit(1)

    finally:
        # 清理资源
        if 'migration_manager' in locals():
            await migration_manager.cleanup()


if __name__ == "__main__":
    asyncio.run(main())