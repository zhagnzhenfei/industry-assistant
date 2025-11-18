# Milvus 迁移指南

## 🎯 概述

本文档提供了从 Elasticsearch 到 Milvus 的完整迁移指南，包括数据迁移、混合检索、性能优化等核心功能。

## 📁 项目结构

```
app/services/milvus/
├── __init__.py                    # 模块初始化
├── models.py                      # 数据模型定义
├── milvus_service.py              # 核心 Milvus 服务
├── migration_service.py           # 数据迁移服务
├── hybrid_search_service.py       # 混合检索服务
├── optimization_service.py        # 性能优化服务
└── monitoring_service.py          # 监控服务 (可选)

scripts/
└── milvus_migration.py            # 迁移脚本

configs/
└── milvus_migration.json          # 迁移配置
```

## 🚀 快速开始

### 1. 环境准备

确保已安装以下依赖：

```bash
pip install pymilvus==2.3.3
pip install elasticsearch==8.11.3
pip install numpy==1.24.3
pip install asyncio
```

### 2. 配置文件

编辑 `configs/milvus_migration.json`：

```json
{
  "milvus": {
    "host": "localhost",
    "port": "19530",
    "user": "",
    "password": "",
    "db_name": "default"
  },
  "elasticsearch": {
    "host": "localhost",
    "port": 9200,
    "user": "",
    "password": ""
  }
}
```

### 3. 执行迁移

#### 单个用户迁移
```bash
python scripts/milvus_migration.py \
  --config configs/milvus_migration.json \
  --user-id 12345 \
  --output results/user_12345_migration.json
```

#### 批量用户迁移
```bash
python scripts/milvus_migration.py \
  --config configs/milvus_migration.json \
  --user-ids "12345,12346,12347" \
  --batch-size 2 \
  --output results/batch_migration.json
```

#### 预检查模式
```bash
python scripts/milvus_migration.py \
  --config configs/milvus_migration.json \
  --user-id 12345 \
  --dry-run
```

#### 完整迁移（含优化和测试）
```bash
python scripts/milvus_migration.py \
  --config configs/milvus_migration.json \
  --user-id 12345 \
  --optimize \
  --test-search \
  --output results/complete_migration.json
```

## 🔧 核心功能

### 1. 数据迁移服务 (DataMigrationService)

负责将数据从 Elasticsearch 迁移到 Milvus：

```python
from app.services.milvus import DataMigrationService

# 初始化服务
migration_service = DataMigrationService(
    es_client=es_client,
    milvus_service=milvus_service,
    batch_size=1000,
    max_workers=4
)

# 迁移单个用户
result = await migration_service.migrate_user_data(user_id=12345)
```

#### 主要功能：
- **批量数据迁移**：使用 scroll API 高效读取 ES 数据
- **数据格式转换**：自动转换 ES 数据格式到 Milvus 格式
- **数据验证**：迁移后数据完整性验证
- **增量同步**：支持增量数据同步
- **回滚机制**：完整的回滚支持

### 2. 混合检索服务 (HybridSearchService)

结合 Milvus 向量搜索和 Elasticsearch 全文搜索：

```python
from app.services.milvus import HybridSearchService, SearchRequest

# 初始化服务
hybrid_service = HybridSearchService(
    milvus_service=milvus_service,
    es_client=es_client,
    vector_weight=0.95,  # 向量权重 95%
    text_weight=0.05     # 文本权重 5%
)

# 执行混合搜索
request = SearchRequest(
    query="人工智能技术",
    kb_id="12345",
    top_k=10
)
results = await hybrid_service.search(request)
```

#### 搜索流程：
1. **查询预处理**：生成查询向量，构建过滤条件
2. **并行搜索**：同时执行 Milvus 向量搜索和 ES 全文搜索
3. **结果融合**：按权重融合搜索结果（向量95% + 文本5%）
4. **重排序**：基于多维度特征重新排序
5. **阈值过滤**：应用相似度阈值过滤

### 3. 性能优化服务 (MilvusOptimizationService)

自动优化 Milvus 集合性能：

```python
from app.services.milvus import MilvusOptimizationService

# 初始化服务
optimization_service = MilvusOptimizationService(milvus_service)

# 优化集合
result = await optimization_service.optimize_collection(
    collection_name="user_12345_documents",
    optimization_level="balanced"  # performance/balanced/memory
)
```

#### 优化策略：
- **索引优化**：根据数据量自动选择最优索引类型
- **搜索参数优化**：调优搜索参数以平衡性能和精度
- **内存优化**：智能管理集合加载策略
- **基准测试**：性能基准测试和对比

## 📊 性能指标

### 预期性能提升

| 指标 | Elasticsearch | Milvus | 提升幅度 |
|------|---------------|---------|----------|
| **向量搜索延迟** | ~50ms | ~10ms | **80%降低** |
| **并发处理能力** | ~2,000 QPS | ~15,000 QPS | **650%提升** |
| **内存使用效率** | 32GB | 24GB | **25%节省** |
| **数据规模支持** | 100万级 | 1000万级 | **10倍扩展** |

### 索引类型选择

| 数据规模 | 推荐索引 | 延迟预期 | QPS预期 |
|----------|----------|----------|---------|
| < 10K | HNSW | < 10ms | > 10,000 |
| 10K - 1M | IVF_FLAT | < 50ms | > 5,000 |
| 1M - 10M | IVF_PQ | < 100ms | > 1,000 |
| > 10M | IVF_PQ | < 500ms | > 500 |

## 🔍 数据模型映射

### ES 到 Milvus 字段映射

| Elasticsearch 字段 | Milvus 字段 | 说明 |
|-------------------|-------------|------|
| `content_with_weight` | `content` | 文档内容 |
| `content_ltks` | `content_ltks` | 分词内容 |
| `q_1024_vec` | `vector` | 1024维向量 |
| `doc_id` | `doc_id` | 文档ID |
| `docnm_kwd` | `doc_name` | 文档名称 |
| `kb_id` | `kb_id` | 知识库ID |
| `_id` | `chunk_id` | 分块ID |
| `create_timestamp_flt` | `timestamp` | 创建时间戳 |

### 新增字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `category` | VARCHAR | 文档分类 |
| `confidence` | FLOAT | 置信度评分 |
| `source` | VARCHAR | 数据来源 |
| `keywords` | VARCHAR | 关键词 |
| `metadata` | JSON | 扩展元数据 |

## ⚙️ 配置选项

### 迁移配置

```json
{
  "migration": {
    "batch_size": 1000,              // 批处理大小
    "max_workers": 4,                // 最大工作线程数
    "validation_sample_rate": 0.01,  // 验证采样率（1%）
    "timeout_seconds": 300,          // 超时时间
    "max_retries": 3,                // 最大重试次数
    "retry_delay": 1.0               // 重试延迟（秒）
  }
}
```

### 搜索配置

```json
{
  "search": {
    "vector_weight": 0.95,  // 向量搜索权重
    "text_weight": 0.05,    // 文本搜索权重
    "max_workers": 4        // 最大工作线程数
  }
}
```

### 优化配置

```json
{
  "optimization": {
    "default_level": "balanced",  // 默认优化级别
    "performance_target": {
      "search_latency_p99_ms": 10,  // P99延迟目标
      "insert_qps": 5000,           // 插入吞吐量目标
      "memory_efficiency": 0.8      // 内存效率目标
    }
  }
}
```

## 🔧 高级用法

### 自定义数据转换

```python
class CustomMigrationService(DataMigrationService):
    async def _convert_es_to_milvus(self, es_hit: Dict[str, Any]) -> Dict[str, Any]:
        """自定义数据转换逻辑"""
        # 自定义转换逻辑
        milvus_record = {
            # ... 自定义字段映射
        }
        return milvus_record
```

### 自定义搜索融合

```python
class CustomHybridSearchService(HybridSearchService):
    def _fuse_results(self, milvus_results: List[SearchResult],
                     es_results: List[SearchResult]) -> List[Dict[str, Any]]:
        """自定义结果融合逻辑"""
        # 自定义融合算法
        return fused_results
```

### 性能监控集成

```python
# 集成 Prometheus 监控
from prometheus_client import Counter, Histogram, Gauge

# 定义指标
search_requests = Counter('milvus_search_requests_total', 'Total search requests')
search_latency = Histogram('milvus_search_latency_seconds', 'Search latency')
collection_size = Gauge('milvus_collection_entities', 'Number of entities in collection')

# 在代码中使用
search_requests.inc()
with search_latency.time():
    results = await hybrid_service.search(request)
```

## ⚠️ 注意事项

### 迁移前准备

1. **数据备份**：确保 Elasticsearch 数据已完整备份
2. **环境检查**：验证 Milvus 和 Elasticsearch 连接
3. **容量评估**：确保 Milvus 有足够的存储空间
4. **性能基线**：记录当前 ES 的性能指标

### 迁移过程监控

1. **进度监控**：关注迁移进度和错误日志
2. **资源监控**：监控系统资源使用情况
3. **性能验证**：定期进行数据验证和性能测试
4. **错误处理**：及时处理迁移过程中的错误

### 回滚策略

1. **保留原始数据**：迁移过程中保留 ES 原始数据
2. **增量同步**：支持增量数据同步，确保数据一致性
3. **快速回滚**：提供快速的回滚机制
4. **验证机制**：迁移后数据完整性验证

## 🐛 故障排除

### 常见问题

#### 1. Milvus 连接失败
```bash
# 检查 Milvus 服务状态
docker ps | grep milvus

# 检查网络连接
telnet localhost 19530

# 查看 Milvus 日志
docker logs milvus-standalone
```

#### 2. 迁移性能慢
- 调整 `batch_size` 参数
- 增加 `max_workers` 数量
- 检查网络带宽
- 优化索引参数

#### 3. 搜索结果不准确
- 检查向量生成是否正确
- 验证权重配置
- 调整相似度阈值
- 优化索引类型

#### 4. 内存使用过高
- 选择合适的索引类型
- 调整集合加载策略
- 优化搜索参数
- 增加硬件资源

### 日志分析

查看详细日志：
```bash
tail -f milvus_migration_*.log
```

关键日志级别：
- `INFO`：正常操作信息
- `WARNING`：警告信息
- `ERROR`：错误信息
- `DEBUG`：调试信息（开发模式）

## 📚 相关文档

- [Milvus 官方文档](https://milvus.io/docs)
- [Elasticsearch 官方文档](https://www.elastic.co/guide/)
- [项目迁移分析](./MILVUS_MIGRATION_ANALYSIS.md)
- [Milvus Standalone 部署指南](./MILVUS_STANDALONE_DEPLOYMENT.md)

## 🤝 支持

如遇到问题，请：

1. 查看详细日志信息
2. 检查配置文件
3. 验证网络连接
4. 参考故障排除部分
5. 联系技术支持

---

**维护信息：**
- **版本**: v1.0
- **更新时间**: 2025年1月
- **适用版本**: 当前项目架构