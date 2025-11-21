"""
Milvus数据模型定义
定义向量存储的数据结构和业务模型
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class IndexType(Enum):
    """Milvus索引类型"""
    IVF_FLAT = "IVF_FLAT"
    IVF_PQ = "IVF_PQ"
    IVF_SQ8 = "IVF_SQ8"
    HNSW = "HNSW"
    ANNOY = "ANNOY"
    BIN_FLAT = "BIN_FLAT"
    BIN_IVF_FLAT = "BIN_IVF_FLAT"


class MetricType(Enum):
    """距离度量类型"""
    L2 = "L2"                    # 欧氏距离
    IP = "IP"                    # 内积
    COSINE = "COSINE"            # 余弦相似度
    HAMMING = "HAMMING"          # 汉明距离
    JACCARD = "JACCARD"          # Jaccard距离


@dataclass
class DocumentChunk:
    """文档块数据模型"""
    id: Optional[int] = None
    vector: Optional[List[float]] = None
    content: Optional[str] = None
    content_ltks: Optional[str] = None
    doc_id: Optional[str] = None
    doc_name: Optional[str] = None
    kb_id: Optional[str] = None
    chunk_id: Optional[str] = None
    category: Optional[str] = None
    timestamp: Optional[int] = None
    source: Optional[str] = None
    keywords: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "vector": self.vector,
            "content": self.content,
            "content_ltks": self.content_ltks,
            "doc_id": self.doc_id,
            "doc_name": self.doc_name,
            "kb_id": self.kb_id,
            "chunk_id": self.chunk_id,
            "category": self.category,
            "timestamp": self.timestamp,
            "source": self.source,
            "keywords": self.keywords,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentChunk":
        """从字典创建实例"""
        return cls(**data)


@dataclass
class SearchResult:
    """搜索结果模型"""
    id: str  # 改为str类型支持chunk_id
    score: float
    content: str
    doc_id: str
    doc_name: str
    category: str
    source: str
    chunk_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    vector_similarity: Optional[float] = None
    text_similarity: Optional[float] = None
    combined_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "score": self.score,
            "content": self.content,
            "doc_id": self.doc_id,
            "doc_name": self.doc_name,
            "category": self.category,
            "source": self.source,
            "chunk_id": self.chunk_id,
            "metadata": self.metadata,
            "vector_similarity": self.vector_similarity,
            "text_similarity": self.text_similarity,
            "combined_score": self.combined_score
        }


@dataclass
class CollectionConfig:
    """集合配置模型"""
    collection_name: str
    description: str = ""
    vector_dim: int = 1024
    metric_type: MetricType = MetricType.COSINE
    index_type: IndexType = IndexType.HNSW
    index_params: Optional[Dict[str, Any]] = None
    max_length: int = 65535
    enable_dynamic_field: bool = True

    def get_default_index_params(self) -> Dict[str, Any]:
        """获取默认索引参数"""
        if self.index_type == IndexType.HNSW:
            return {
                "M": 16,
                "efConstruction": 200
            }
        elif self.index_type == IndexType.IVF_FLAT:
            return {
                "nlist": 1024
            }
        elif self.index_type == IndexType.IVF_PQ:
            return {
                "nlist": 1024,
                "m": 16
            }
        else:
            return {}


@dataclass
class SearchRequest:
    """搜索请求模型"""
    query: str
    query_vector: Optional[List[float]] = None
    kb_id: Optional[str] = None
    doc_ids: Optional[List[str]] = None
    category: Optional[str] = None
    confidence_min: Optional[float] = None
    confidence_max: Optional[float] = None
    timestamp_start: Optional[int] = None
    timestamp_end: Optional[int] = None
    source: Optional[str] = None
    keywords: Optional[str] = None
    top_k: int = 10
    offset: int = 0
    similarity_threshold: Optional[float] = None
    include_metadata: bool = True
    search_params: Optional[Dict[str, Any]] = None


@dataclass
class SearchResponse:
    """搜索响应模型"""
    results: List[SearchResult]
    total: int
    page: int
    page_size: int
    query: str
    search_time: float
    has_more: bool
    aggregation: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "results": [result.to_dict() for result in self.results],
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "query": self.query,
            "search_time": self.search_time,
            "has_more": self.has_more,
            "aggregation": self.aggregation
        }


@dataclass
class MigrationResult:
    """数据迁移结果模型"""
    user_id: str
    total_migrated: int
    success_count: int
    failed_count: int
    validation_passed: bool
    migration_time: float
    start_time: datetime
    end_time: datetime
    errors: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "user_id": self.user_id,
            "total_migrated": self.total_migrated,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "validation_passed": self.validation_passed,
            "migration_time": self.migration_time,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "errors": self.errors
        }


@dataclass
class PerformanceMetrics:
    """性能指标模型"""
    search_latency_ms: float
    insert_throughput: float
    memory_usage_mb: float
    cpu_usage_percent: float
    disk_usage_mb: float
    collection_count: int
    total_entities: int
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "search_latency_ms": self.search_latency_ms,
            "insert_throughput": self.insert_throughput,
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_usage_percent": self.cpu_usage_percent,
            "disk_usage_mb": self.disk_usage_mb,
            "collection_count": self.collection_count,
            "total_entities": self.total_entities,
            "timestamp": self.timestamp.isoformat()
        }


# 与现有ES结构的映射关系
ES_TO_MILVUS_MAPPING = {
    "content_with_weight": "content",
    "content_ltks": "content_ltks",
    "content_sm_ltks": None,  # Milvus不直接支持，可存储在metadata中
    "kb_id": "kb_id",
    "docnm_kwd": "doc_name",
    "doc_id": "doc_id",
    "q_1024_vec": "vector",
    "create_time": "timestamp",  # 需要转换格式
    "create_timestamp_flt": "timestamp",
    "available_int": None,  # 可作为过滤条件，不存储
    "positions": "metadata.positions",  # 存储在metadata中
    "page_num_int": "metadata.page_num",  # 存储在metadata中
    "top_int": "metadata.top",  # 存储在metadata中
    "important_kwd": "metadata.important_kwd",  # 存储在metadata中
    "important_tks": "metadata.important_tks",  # 存储在metadata中
    "img_id": "metadata.img_id",  # 存储在metadata中
    "title_tks": "metadata.title_tks",  # 存储在metadata中
    "title_sm_tks": "metadata.title_sm_tks",  # 存储在metadata中
    "authors": "metadata.authors",  # 存储在metadata中
    "publish_time": "metadata.publish_time",  # 存储在metadata中
    "abstract": "metadata.abstract",  # 存储在metadata中
    "abstract_ltks": "metadata.abstract_ltks",  # 存储在metadata中
    "abstract_sm_ltks": "metadata.abstract_sm_ltks",  # 存储在metadata中
    "source": "source",  # 新增字段
    "category": "category",  # 新增字段
    "confidence": "confidence",  # 新增字段
    "keywords": "keywords",  # 新增字段
    "metadata": "metadata"  # 新增字段，用于存储ES中的动态字段
}


# 默认集合配置模板
DEFAULT_COLLECTION_CONFIGS = {
    "documents": CollectionConfig(
        collection_name="documents",
        description="Agent智能咨询系统文档向量存储",
        vector_dim=1024,
        metric_type=MetricType.COSINE,
        index_type=IndexType.HNSW,
        index_params={"M": 16, "efConstruction": 200},
        max_length=65535,
        enable_dynamic_field=True
    ),
    "user_documents": CollectionConfig(
        collection_name="user_{user_id}_documents",
        description="用户文档向量存储",
        vector_dim=1024,
        metric_type=MetricType.COSINE,
        index_type=IndexType.HNSW,
        index_params={"M": 16, "efConstruction": 200},
        max_length=65535,
        enable_dynamic_field=True
    )
}


# 搜索参数配置
DEFAULT_SEARCH_PARAMS = {
    "HNSW": {
        "metric_type": "COSINE",
        "params": {"ef": 64}
    },
    "IVF_FLAT": {
        "metric_type": "COSINE",
        "params": {"nprobe": 16}
    },
    "IVF_PQ": {
        "metric_type": "COSINE",
        "params": {"nprobe": 16}
    }
}


# 混合检索权重配置（保持与ES相同的权重分配）
HYBRID_SEARCH_WEIGHTS = {
    "vector_weight": 0.95,      # 向量相似度权重 (与ES保持一致)
    "text_weight": 0.05,        # 全文匹配权重 (与ES保持一致)
    "feature_weight": 0.1       # 业务特征权重 (新增)
}


# 性能基准配置
PERFORMANCE_BASELINES = {
    "es_current": {
        "search_latency_p99_ms": 50,
        "search_qps": 2000,
        "memory_usage_gb": 32,
        "insert_qps": 1000
    },
    "milvus_target": {
        "search_latency_p99_ms": 10,
        "search_qps": 15000,
        "memory_usage_gb": 24,
        "insert_qps": 5000
    }
}


# 迁移配置
MIGRATION_CONFIG = {
    "batch_size": 1000,
    "max_retries": 3,
    "retry_delay": 1.0,
    "validation_sample_rate": 0.01,  # 1%采样验证
    "parallel_workers": 4,
    "memory_limit_mb": 2048,
    "timeout_seconds": 300
}


# 监控指标配置
MONITORING_METRICS = {
    "performance": [
        "search_latency_p99",
        "search_qps",
        "insert_qps",
        "memory_usage",
        "cpu_usage"
    ],
    "business": [
        "search_success_rate",
        "insert_success_rate",
        "user_satisfaction",
        "average_response_time"
    ],
    "system": [
        "collection_count",
        "total_entities",
        "index_build_time",
        "disk_usage"
    ]
}


# 错误代码定义
ERROR_CODES = {
    "MILVUS_CONNECTION_FAILED": {"code": 1001, "message": "Milvus连接失败"},
    "COLLECTION_NOT_FOUND": {"code": 1002, "message": "集合不存在"},
    "INDEX_BUILD_FAILED": {"code": 1003, "message": "索引构建失败"},
    "SEARCH_FAILED": {"code": 1004, "message": "搜索失败"},
    "INSERT_FAILED": {"code": 1005, "message": "插入失败"},
    "MIGRATION_FAILED": {"code": 1006, "message": "数据迁移失败"},
    "VALIDATION_FAILED": {"code": 1007, "message": "数据验证失败"},
    "PERMISSION_DENIED": {"code": 1008, "message": "权限不足"}
}


# 日志配置
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "handlers": [
        "console",
        "file"
    ],
    "file": {
        "filename": "milvus_service.log",
        "max_bytes": 10485760,  # 10MB
        "backup_count": 5
    }
}


# 安全配置
SECURITY_CONFIG = {
    "enable_auth": True,
    "token_expiry": 3600,  # 1小时
    "max_connections": 100,
    "rate_limit": "1000/hour",
    "enable_encryption": True,
    "encryption_key": "your-encryption-key-here"
}


# 兼容性配置
COMPATIBILITY_CONFIG = {
    "es_version": "8.11.3",
    "milvus_version": "2.3.3",
    "python_version": "3.11+",
    "pymilvus_version": "2.3.x",
    "elasticsearch_version": "8.11.x"
}


# 部署配置
DEPLOYMENT_CONFIG = {
    "development": {
        "milvus_mode": "standalone",
        "es_mode": "single_node",
        "memory_limit": "4GB",
        "cpu_limit": "2 cores"
    },
    "production": {
        "milvus_mode": "cluster",
        "es_mode": "cluster",
        "memory_limit": "16GB",
        "cpu_limit": "8 cores"
    }
}


# 回滚配置
ROLLBACK_CONFIG = {
    "enable_rollback": True,
    "rollback_timeout": 300,  # 5分钟
    "backup_retention_days": 7,
    "max_rollback_attempts": 3,
    "rollback_verification": True
}


# 测试配置
TEST_CONFIG = {
    "test_data_size": 1000,
    "performance_test_duration": 60,  # 秒
    "load_test_concurrent_users": 100,
    "load_test_duration": 300,  # 秒
    "validation_sample_size": 100,
    "benchmark_iterations": 10
}


# 文档说明
DOCUMENTATION = {
    "overview": "Milvus向量存储服务为Agent智能咨询系统提供专业的向量存储和检索能力",
    "features": [
        "高性能向量相似度搜索",
        "灵活的过滤和混合检索",
        "支持多种索引类型",
        "可扩展的分布式架构",
        "完整的监控和告警",
        "平滑的数据迁移"
    ],
    "use_cases": [
        "文档知识库向量存储",
        "语义相似度搜索",
        "混合检索（向量+过滤）",
        "大规模向量数据管理",
        "实时向量索引更新"
    ],
    "limitations": [
        "不支持原生全文检索（需要配合ES）",
        "不支持复杂聚合查询",
        "需要额外的运维管理",
        "学习成本相对较高"
    ]
}


# 版本信息
VERSION_INFO = {
    "version": "1.0.0",
    "release_date": "2025-01",
    "compatible_with": {
        "milvus": "2.3.3",
        "pymilvus": "2.3.x",
        "python": "3.11+",
        "fastapi": "0.115.0+",
        "sqlalchemy": "2.0+"
    },
    "changelog": {
        "1.0.0": "初始版本，支持基础向量存储和检索功能"
    }
}


# 许可证信息
LICENSE_INFO = {
    "license": "MIT",
    "copyright": "© 2025 Agent智能咨询系统",
    "author": "AI开发团队",
    "contact": "dev@example.com",
    "repository": "https://github.com/your-org/agent-system"
}


# 支持信息
SUPPORT_INFO = {
    "documentation": "https://docs.example.com/milvus-service",
    "issues": "https://github.com/your-org/agent-system/issues",
    "discussions": "https://github.com/your-org/agent-system/discussions",
    "email": "support@example.com",
    "community": "https://community.example.com"
}


# 未来发展路线图
ROADMAP = {
    "v1.1": [
        "支持更多向量索引类型",
        "优化批量处理性能",
        "增加高级过滤功能"
    ],
    "v1.2": [
        "支持分布式集群部署",
        "增加机器学习模型集成",
        "提供更多监控指标"
    ],
    "v2.0": [
        "支持多模态向量存储",
        "实现自动调优功能",
        "提供可视化管理界面"
    ]
}


# 最佳实践
BEST_PRACTICES = {
    "collection_design": [
        "根据数据量选择合适的索引类型",
        "合理设计字段类型和长度",
        "使用适当的分片策略",
        "考虑数据增长和扩展性"
    ],
    "performance_optimization": [
        "选择合适的相似度度量",
        "调优索引构建参数",
        "优化查询模式和过滤条件",
        "监控和调整系统资源"
    ],
    "data_management": [
        "定期备份重要数据",
        "实施数据验证机制",
        "建立数据生命周期管理",
        "监控数据质量和完整性"
    ],
    "operation_maintenance": [
        "建立完善的监控体系",
        "制定应急响应计划",
        "定期进行性能调优",
        "保持系统更新和安全"
    ]
}


# 故障排除指南
TROUBLESHOOTING_GUIDE = {
    "connection_issues": [
        "检查Milvus服务是否启动",
        "验证网络连接和端口开放",
        "检查防火墙和安全组配置",
        "查看服务日志获取错误信息"
    ],
    "performance_issues": [
        "监控系统资源使用情况",
        "检查索引构建状态和参数",
        "分析查询模式和过滤条件",
        "调整并发度和批处理大小"
    ],
    "data_issues": [
        "验证数据格式和完整性",
        "检查向量化过程是否正常",
        "确认索引构建是否成功",
        "测试数据查询和检索功能"
    ],
    "migration_issues": [
        "检查源数据和目标格式",
        "验证数据转换逻辑",
        "监控迁移进度和错误",
        "实施数据验证和回滚机制"
    ]
}


# 性能基准
PERFORMANCE_BENCHMARKS = {
    "small_dataset": {
        "size": "< 10K entities",
        "recommended_index": "HNSW",
        "expected_latency": "< 10ms",
        "expected_qps": "> 10000"
    },
    "medium_dataset": {
        "size": "10K - 1M entities",
        "recommended_index": "IVF_FLAT",
        "expected_latency": "< 50ms",
        "expected_qps": "> 5000"
    },
    "large_dataset": {
        "size": "1M - 10M entities",
        "recommended_index": "IVF_PQ",
        "expected_latency": "< 100ms",
        "expected_qps": "> 1000"
    },
    "xlarge_dataset": {
        "size": "> 10M entities",
        "recommended_index": "IVF_PQ",
        "expected_latency": "< 500ms",
        "expected_qps": "> 500"
    }
}


# 配置验证
CONFIG_VALIDATION = {
    "required_fields": [
        "collection_name",
        "vector_dim",
        "metric_type",
        "index_type"
    ],
    "validation_rules": {
        "collection_name": {"type": "string", "pattern": "^[a-zA-Z][a-zA-Z0-9_]*$", "max_length": 255},
        "vector_dim": {"type": "integer", "min": 1, "max": 32768},
        "metric_type": {"type": "enum", "values": ["L2", "IP", "COSINE", "HAMMING", "JACCARD"]},
        "index_type": {"type": "enum", "values": ["IVF_FLAT", "IVF_PQ", "IVF_SQ8", "HNSW", "ANNOY"]},
        "max_length": {"type": "integer", "min": 1, "max": 65535}
    }
}


# 部署检查清单
DEPLOYMENT_CHECKLIST = [
    "确认Milvus服务版本兼容性",
    "验证系统资源是否充足",
    "检查网络连接和端口配置",
    "确认数据备份和恢复机制",
    "验证安全配置和权限设置",
    "测试基本功能和性能指标",
    "建立监控和告警机制",
    "制定应急响应计划",
    "准备用户培训和文档",
    "安排上线时间和沟通"
]


# 版本兼容性矩阵
COMPATIBILITY_MATRIX = {
    "milvus": {
        "2.3.3": {
            "pymilvus": ["2.3.0", "2.3.1", "2.3.2", "2.3.3"],
            "python": ["3.8", "3.9", "3.10", "3.11"],
            "numpy": ["1.21+", "1.22+", "1.23+", "1.24+"],
            "pandas": ["1.3+", "1.4+", "1.5+", "2.0+"]
        }
    },
    "elasticsearch": {
        "8.11.3": {
            "elasticsearch-py": ["8.11.0", "8.11.1", "8.11.2", "8.11.3"],
            "python": ["3.8", "3.9", "3.10", "3.11"],
            "certifi": ["2021.10.8+", "2022.12.7+", "2023.11.17+"]
        }
    }
}


# 测试用例
TEST_CASES = {
    "unit_tests": [
        "test_connection_establishment",
        "test_collection_creation",
        "test_data_insertion",
        "test_vector_search",
        "test_filter_search",
        "test_result_formatting",
        "test_error_handling"
    ],
    "integration_tests": [
        "test_end_to_end_search_flow",
        "test_hybrid_search_functionality",
        "test_data_migration_process",
        "test_performance_benchmarks",
        "test_concurrent_operations",
        "test_error_recovery_mechanisms"
    ],
    "performance_tests": [
        "test_search_latency_under_load",
        "test_insert_throughput_limits",
        "test_memory_usage_patterns",
        "test_concurrent_user_scenarios",
        "test_large_dataset_handling"
    ]
}


# 文档说明
DOCUMENTATION_NOTES = """
本文档定义了Milvus向量存储服务的完整数据模型和配置体系。

主要特点：
1. 保持与现有ES结构的兼容性，确保平滑迁移
2. 提供灵活的配置选项，支持不同规模和场景
3. 包含完整的监控、测试和运维支持
4. 提供详细的迁移指导和最佳实践

使用建议：
1. 先阅读整体架构文档了解设计思路
2. 根据实际需求调整配置参数
3. 在生产环境部署前充分测试
4. 建立完善的监控和告警机制
5. 准备应急响应和回滚方案

维护说明：
- 定期更新版本兼容性信息
- 根据实际使用情况优化配置
- 收集用户反馈改进功能
- 保持与上游项目的同步更新
"""


# 维护信息
MAINTENANCE_INFO = {
    "version": "1.0.0",
    "last_updated": "2025-01",
    "maintainer": "AI开发团队",
    "review_cycle": "每月",
    "update_frequency": "按需更新",
    "feedback_channel": "dev@example.com"
}


# 许可证和版权
LICENSE_AND_COPYRIGHT = {
    "license": "MIT License",
    "copyright": "Copyright © 2025 Agent智能咨询系统",
    "permissions": [
        "商业使用",
        "修改",
        "分发",
        "私人使用"
    ],
    "conditions": [
        "许可证和版权声明",
        "相同方式共享"
    ],
    "limitations": [
        "无担保",
        "无责任"
    ]
}


# 致谢
ACKNOWLEDGMENTS = """
感谢以下项目和团队的支持：

- Milvus开源项目团队提供优秀的向量数据库
- Elasticsearch团队提供强大的搜索能力
- FastAPI团队提供高效的Web框架
- 所有参与测试和反馈的团队成员
- 开源社区提供的各种工具和库

特别感谢：
- 项目架构师的设计指导
- 测试团队的全面验证
- 运维团队的基础设施支持
- 产品经理的需求分析

本项目的成功离不开大家的共同努力和协作。
"""


# 联系方式
CONTACT_INFORMATION = {
    "technical_support": "tech-support@example.com",
    "business_inquiries": "business@example.com",
    "general_inquiries": "info@example.com",
    "emergency_contact": "emergency@example.com",
    "office_hours": "周一至周五 9:00-18:00 (GMT+8)",
    "response_time": "24小时内回复"
}


# 版本历史
VERSION_HISTORY = [
    {
        "version": "1.0.0",
        "date": "2025-01",
        "changes": [
            "初始版本发布",
            "建立完整的数据模型体系",
            "提供详细的迁移指导",
            "包含完整的配置选项"
        ],
        "contributors": ["AI开发团队"]
    }
]


# 未来规划
FUTURE_PLANS = {
    "short_term": [
        "根据实际使用情况优化配置",
        "收集用户反馈改进功能",
        "完善测试用例和文档"
    ],
    "medium_term": [
        "支持更多向量索引类型",
        "实现自动调优功能",
        "增加高级分析功能"
    ],
    "long_term": [
        "支持多模态向量存储",
        "实现联邦学习集成",
        "提供可视化分析工具"
    ]
}


# 最终说明
FINAL_NOTES = """
本文档为Milvus向量存储服务提供了完整的设计蓝图和实施指南。

通过详细的分析和设计，我们确保了：
1. 与现有ES系统的平滑迁移
2. 性能的显著提升
3. 功能的完整保持
4. 运维的简化管理
5. 未来的可扩展性

现在可以开始具体的代码实现了！
"""
