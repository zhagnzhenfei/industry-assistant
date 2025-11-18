# Milvus Standalone 部署与开发指南

## 🎯 概述

本文档描述如何在本地开发环境中快速部署和使用 Milvus standalone 模式，为 Agent 智能咨询系统提供向量存储支持。

## 🚀 快速开始（5分钟部署）

### 1. 环境要求

```bash
# 系统要求
- Docker >= 20.10
- Docker Compose >= 1.29
- Python >= 3.8
- 内存 >= 8GB（推荐16GB）
- 磁盘空间 >= 10GB
```

### 2. 一键部署

```bash
# 创建项目目录
mkdir ~/milvus-standalone && cd ~/milvus-standalone

# 下载官方 standalone compose 文件（推荐锁定版本）
wget https://github.com/milvus-io/milvus/releases/download/v2.3.3/milvus-standalone-docker-compose.yml -O docker-compose.yml

# 启动服务（后台运行）
docker compose up -d

# 验证状态
docker compose ps
```

### 3. 立即验证

```bash
# 查看日志确认无错误
docker logs milvus-standalone --tail 50

# 测试端口连通性
curl -f http://localhost:9091/health

# 预期输出：{"status":"ok"}
```

## 🔧 开发环境配置

### Python 环境设置

```bash
# 创建虚拟环境
python -m venv milvus-env
source milvus-env/bin/activate  # Linux/Mac
# milvus-env\Scripts\activate     # Windows

# 安装依赖
pip install pymilvus==2.3.3
pip install numpy==1.24.3
pip install pandas==2.0.3
```

### 连接测试脚本

创建 `test_connection.py`:

```python
#!/usr/bin/env python3
"""Milvus 连接测试脚本"""

from pymilvus import connections, utility, Collection, FieldSchema, CollectionSchema, DataType
import sys

def test_basic_connection():
    """测试基础连接"""
    try:
        # 连接 Milvus
        connections.connect(
            alias="default",
            host="127.0.0.1",
            port="19530"
        )

        # 获取服务器版本
        version = utility.get_server_version()
        print(f"✅ Milvus 连接成功！版本: {version}")

        # 获取系统信息
        sys_info = utility.get_system_info()
        print(f"📊 系统信息: {sys_info}")

        return True

    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False

def test_collection_operations():
    """测试集合操作"""
    try:
        # 定义集合schema
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=768),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535)
        ]

        schema = CollectionSchema(fields, "测试集合")

        # 创建集合
        collection_name = "test_collection"
        if utility.has_collection(collection_name):
            utility.drop_collection(collection_name)

        collection = Collection(name=collection_name, schema=schema)
        print(f"✅ 创建集合成功: {collection_name}")

        # 插入测试数据
        import numpy as np

        vectors = np.random.random((100, 768)).astype(np.float32).tolist()
        texts = [f"测试文本_{i}" for i in range(100)]

        entities = [vectors, texts]
        collection.insert(entities)
        print(f"✅ 插入数据成功: 100条记录")

        # 创建索引
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "L2",
            "params": {"nlist": 128}
        }
        collection.create_index("vector", index_params)
        print(f"✅ 创建索引成功")

        # 加载集合并搜索
        collection.load()

        # 搜索测试
        search_vectors = np.random.random((1, 768)).astype(np.float32).tolist()
        search_params = {"metric_type": "L2", "params": {"nprobe": 16}}

        results = collection.search(
            data=search_vectors,
            anns_field="vector",
            param=search_params,
            limit=5,
            output_fields=["text"]
        )

        print(f"✅ 向量搜索成功，返回 {len(results[0])} 条结果")

        # 清理
        collection.drop()
        print(f"✅ 清理完成")

        return True

    except Exception as e:
        print(f"❌ 集合操作失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 Milvus Standalone 连接测试开始...")

    # 基础连接测试
    if not test_basic_connection():
        sys.exit(1)

    # 集合操作测试
    if not test_collection_operations():
        sys.exit(1)

    print("\n🎉 所有测试通过！Milvus Standalone 运行正常")

    # 关闭连接
    connections.disconnect("default")

if __name__ == "__main__":
    main()
```

运行测试：
```bash
python test_connection.py
```

## 📊 性能基准测试

创建 `benchmark_test.py`:

```python
#!/usr/bin/env python3
"""Milvus 性能基准测试"""

import time
import numpy as np
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

class MilvusBenchmark:
    def __init__(self):
        self.collection_name = "benchmark_collection"
        self.dim = 768
        self.connect()
        self.setup_collection()

    def connect(self):
        """连接Milvus"""
        connections.connect(
            alias="default",
            host="127.0.0.1",
            port="19530"
        )

    def setup_collection(self):
        """设置测试集合"""
        from pymilvus import utility

        # 删除已存在的集合
        if utility.has_collection(self.collection_name):
            utility.drop_collection(self.collection_name)

        # 定义Schema
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.dim),
            FieldSchema(name="timestamp", dtype=DataType.INT64)
        ]

        schema = CollectionSchema(fields, "基准测试集合")
        self.collection = Collection(name=self.collection_name, schema=schema)

    def test_insert_performance(self, num_entities=10000, batch_size=1000):
        """测试插入性能"""
        print(f"\n📥 插入性能测试: {num_entities} 条记录, batch_size={batch_size}")

        total_time = 0
        for i in range(0, num_entities, batch_size):
            # 生成测试数据
            vectors = np.random.random((batch_size, self.dim)).astype(np.float32).tolist()
            timestamps = [int(time.time()) + j for j in range(batch_size)]

            # 插入数据
            start_time = time.time()
            entities = [vectors, timestamps]
            self.collection.insert(entities)
            insert_time = time.time() - start_time
            total_time += insert_time

            print(f"  Batch {i//batch_size + 1}: {batch_size} 条, 耗时 {insert_time:.3f}s, "
                  f"QPS: {batch_size/insert_time:.0f}")

        avg_qps = num_entities / total_time
        print(f"✅ 插入完成: 总耗时 {total_time:.3f}s, 平均 QPS: {avg_qps:.0f}")
        return avg_qps

    def test_search_performance(self, num_queries=1000, top_k=10):
        """测试搜索性能"""
        print(f"\n🔍 搜索性能测试: {num_queries} 次查询, top_k={top_k}")

        # 创建索引
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "L2",
            "params": {"nlist": 128}
        }
        self.collection.create_index("vector", index_params)
        self.collection.load()

        # 生成查询向量
        query_vectors = np.random.random((num_queries, self.dim)).astype(np.float32).tolist()
        search_params = {"metric_type": "L2", "params": {"nprobe": 16}}

        # 执行搜索
        start_time = time.time()
        for i, query_vector in enumerate(query_vectors):
            results = self.collection.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=top_k
            )

        total_time = time.time() - start_time
        avg_latency = (total_time / num_queries) * 1000  # ms
        avg_qps = num_queries / total_time

        print(f"✅ 搜索完成: 总耗时 {total_time:.3f}s")
        print(f"  平均延迟: {avg_latency:.2f}ms")
        print(f"  平均 QPS: {avg_qps:.0f}")

        return avg_latency, avg_qps

    def cleanup(self):
        """清理测试数据"""
        from pymilvus import utility
        utility.drop_collection(self.collection_name)
        print("\n🧹 测试数据已清理")

def main():
    print("🚀 Milvus Standalone 性能基准测试")
    print("=" * 50)

    benchmark = MilvusBenchmark()

    try:
        # 插入性能测试
        insert_qps = benchmark.test_insert_performance(num_entities=10000, batch_size=1000)

        # 搜索性能测试
        search_latency, search_qps = benchmark.test_search_performance(num_queries=1000, top_k=10)

        print("\n" + "=" * 50)
        print("📊 性能基准测试结果:")
        print(f"  插入 QPS: {insert_qps:.0f}")
        print(f"  搜索延迟: {search_latency:.2f}ms")
        print(f"  搜索 QPS: {search_qps:.0f}")

        # 性能基准判断
        if insert_qps > 5000 and search_latency < 50:
            print("\n✅ 性能达标！适合生产环境使用")
        else:
            print("\n⚠️  性能一般，建议调优后再使用")

    finally:
        benchmark.cleanup()
        connections.disconnect("default")

if __name__ == "__main__":
    main()
```

## 🔧 常用管理操作

### 服务管理脚本

创建 `milvus_manager.py`:

```python
#!/usr/bin/env python3
"""Milvus 服务管理工具"""

import subprocess
import time
import requests
import sys
from pathlib import Path

class MilvusManager:
    def __init__(self, compose_file="docker-compose.yml"):
        self.compose_file = Path(compose_file)
        self.milvus_port = 19530
        self.metrics_port = 9091

    def start(self):
        """启动Milvus服务"""
        print("🚀 正在启动 Milvus Standalone...")
        try:
            result = subprocess.run(
                ["docker", "compose", "up", "-d"],
                cwd=self.compose_file.parent,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print("✅ Milvus 容器已启动")
                self.wait_for_healthy()
                return True
            else:
                print(f"❌ 启动失败: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ 启动异常: {e}")
            return False

    def stop(self):
        """停止Milvus服务"""
        print("🛑 正在停止 Milvus Standalone...")
        try:
            result = subprocess.run(
                ["docker", "compose", "down"],
                cwd=self.compose_file.parent,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print("✅ Milvus 容器已停止")
                return True
            else:
                print(f"❌ 停止失败: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ 停止异常: {e}")
            return False

    def restart(self):
        """重启Milvus服务"""
        print("🔄 正在重启 Milvus Standalone...")
        if self.stop():
            time.sleep(3)
            return self.start()
        return False

    def status(self):
        """查看服务状态"""
        try:
            # 检查容器状态
            result = subprocess.run(
                ["docker", "compose", "ps"],
                cwd=self.compose_file.parent,
                capture_output=True,
                text=True
            )

            print("📊 容器状态:")
            print(result.stdout)

            # 检查健康状态
            self.check_health()

        except Exception as e:
            print(f"❌ 获取状态失败: {e}")

    def check_health(self):
        """检查服务健康状态"""
        try:
            # 检查metrics端口
            response = requests.get(f"http://localhost:{self.metrics_port}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Milvus 服务健康")
                return True
            else:
                print(f"⚠️  服务状态异常: {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"❌ 服务连接失败: {e}")
            return False

    def logs(self, tail=50):
        """查看服务日志"""
        try:
            result = subprocess.run(
                ["docker", "logs", "milvus-standalone", f"--tail={tail}"],
                capture_output=True,
                text=True
            )

            print(f"📋 最近 {tail} 行日志:")
            print(result.stdout)

            if result.stderr:
                print("⚠️  错误日志:")
                print(result.stderr)

        except Exception as e:
            print(f"❌ 获取日志失败: {e}")

    def clean_data(self):
        """清理所有数据（谨慎使用）"""
        print("⚠️  即将清理所有Milvus数据！")
        confirm = input("确认要继续吗? (yes/no): ")

        if confirm.lower() == "yes":
            print("🧹 正在清理数据...")
            try:
                result = subprocess.run(
                    ["docker", "compose", "down", "-v"],
                    cwd=self.compose_file.parent,
                    capture_output=True,
                    text=True
                )

                if result.returncode == 0:
                    print("✅ 数据清理完成")
                    return True
                else:
                    print(f"❌ 清理失败: {result.stderr}")
                    return False

            except Exception as e:
                print(f"❌ 清理异常: {e}")
                return False
        else:
            print("❌ 取消清理操作")
            return False

def main():
    """命令行界面"""
    import argparse

    parser = argparse.ArgumentParser(description="Milvus Standalone 管理工具")
    parser.add_argument("command", choices=["start", "stop", "restart", "status", "logs", "clean"],
                       help="管理命令")
    parser.add_argument("--tail", type=int, default=50, help="日志行数")

    args = parser.parse_args()

    manager = MilvusManager()

    commands = {
        "start": manager.start,
        "stop": manager.stop,
        "restart": manager.restart,
        "status": manager.status,
        "logs": lambda: manager.logs(args.tail),
        "clean": manager.clean_data
    }

    if args.command in commands:
        success = commands[args.command]()
        sys.exit(0 if success else 1)
    else:
        print(f"❌ 未知命令: {args.command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## 📊 资源监控

### 资源使用监控脚本

创建 `resource_monitor.py`:

```python
#!/usr/bin/env python3
"""Milvus 资源监控"""

import subprocess
import time
import json
from datetime import datetime

class ResourceMonitor:
    def __init__(self):
        self.container_name = "milvus-standalone"

    def get_container_stats(self):
        """获取容器资源使用情况"""
        try:
            result = subprocess.run(
                ["docker", "stats", self.container_name, "--no-stream", "--format", "json"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                stats = json.loads(result.stdout)
                return {
                    "timestamp": datetime.now().isoformat(),
                    "cpu_percent": stats.get("CPUPerc", "0%").rstrip("%"),
                    "memory_usage": stats.get("MemUsage", "0B / 0B"),
                    "memory_percent": stats.get("MemPerc", "0%").rstrip("%"),
                    "network_io": stats.get("NetIO", "0B / 0B"),
                    "block_io": stats.get("BlockIO", "0B / 0B")
                }
            else:
                return None

        except Exception as e:
            print(f"获取容器状态失败: {e}")
            return None

    def get_system_info(self):
        """获取系统信息"""
        try:
            # 获取Docker系统信息
            result = subprocess.run(
                ["docker", "system", "df", "--format", "json"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return None

        except Exception as e:
            print(f"获取系统信息失败: {e}")
            return None

    def monitor_continuously(self, interval=5, duration=60):
        """持续监控资源使用"""
        print(f"🔍 开始监控资源使用 (间隔: {interval}s, 持续时间: {duration}s)")
        print("-" * 80)

        stats_history = []
        start_time = time.time()

        try:
            while time.time() - start_time < duration:
                stats = self.get_container_stats()
                if stats:
                    stats_history.append(stats)
                    self.print_stats(stats)

                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n⏹️  监控被中断")

        print("\n" + "=" * 80)
        print("📊 监控总结:")
        self.print_summary(stats_history)

    def print_stats(self, stats):
        """打印统计信息"""
        timestamp = datetime.fromisoformat(stats["timestamp"]).strftime("%H:%M:%S")
        print(f"[{timestamp}] CPU: {stats['cpu_percent']:>6}% | "
              f"内存: {stats['memory_percent']:>6}% | "
              f"网络: {stats['network_io']}")

    def print_summary(self, stats_history):
        """打印监控总结"""
        if not stats_history:
            print("❌ 没有收集到监控数据")
            return

        cpu_values = [float(s["cpu_percent"]) for s in stats_history]
        memory_values = [float(s["memory_percent"]) for s in stats_history]

        avg_cpu = sum(cpu_values) / len(cpu_values)
        max_cpu = max(cpu_values)
        avg_memory = sum(memory_values) / len(memory_values)
        max_memory = max(memory_values)

        print(f"平均 CPU 使用率: {avg_cpu:.1f}%")
        print(f"峰值 CPU 使用率: {max_cpu:.1f}%")
        print(f"平均内存使用率: {avg_memory:.1f}%")
        print(f"峰值内存使用率: {max_memory:.1f}%")
        print(f"监控数据点数量: {len(stats_history)}")

def main():
    """命令行监控工具"""
    import argparse

    parser = argparse.ArgumentParser(description="Milvus 资源监控工具")
    parser.add_argument("--interval", type=int, default=5, help="监控间隔(秒)")
    parser.add_argument("--duration", type=int, default=60, help="监控时长(秒)")
    parser.add_argument("--once", action="store_true", help="只获取一次状态")

    args = parser.parse_args()

    monitor = ResourceMonitor()

    if args.once:
        # 只获取一次状态
        stats = monitor.get_container_stats()
        if stats:
            monitor.print_stats(stats)
        else:
            print("❌ 无法获取容器状态")
    else:
        # 持续监控
        monitor.monitor_continuously(args.interval, args.duration)

if __name__ == "__main__":
    main()
```

## 🐳 Docker Compose 配置优化

创建 `docker-compose.yml`（优化版）:

```yaml
version: '3.5'

services:
  milvus-standalone:
    container_name: milvus-standalone
    image: milvusdb/milvus:v2.3.3
    command: ["milvus", "run", "standalone"]
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
    volumes:
      - ${DOCKER_VOLUME_DIRECTORY:-.}/volumes/milvus:/milvus
    ports:
      - "19530:19530"
      - "9091:9091"
    depends_on:
      - "etcd"
      - "minio"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9091/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    networks:
      - milvus

  etcd:
    container_name: milvus-etcd
    image: quay.io/coreos/etcd:v3.5.5
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
      - ETCD_QUOTA_BACKEND_BYTES=4294967296
      - ETCD_SNAPSHOT_COUNT=50000
    volumes:
      - ${DOCKER_VOLUME_DIRECTORY:-.}/volumes/etcd:/etcd-data
    command: etcd -advertise-client-urls=http://127.0.0.1:2379 -listen-client-urls http://0.0.0.0:2379 --data-dir /etcd-data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "etcdctl", "endpoint", "health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    networks:
      - milvus

  minio:
    container_name: milvus-minio
    image: minio/minio:RELEASE.2023-03-20T20-16-18Z
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
    volumes:
      - ${DOCKER_VOLUME_DIRECTORY:-.}/volumes/minio:/minio_data
    command: minio server /minio_data --console-address ":9001"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3
      start_period: 30s
    ports:
      - "9001:9001"
    networks:
      - milvus

networks:
  milvus:
    driver: bridge
    ipam:
      driver: default
      config:
        - subnet: 172.23.0.0/24

volumes:
  milvus:
    driver: local
  etcd:
    driver: local
  minio:
    driver: local
```

## 📚 学习资源

### 官方文档
- [Milvus 官方文档](https://milvus.io/docs)
- [PyMilvus SDK 文档](https://milvus.io/api-reference/pymilvus/v2.3.x/About.md)
- [Milvus GitHub](https://github.com/milvus-io/milvus)

### 最佳实践
- [向量索引选择指南](https://milvus.io/docs/index.md)
- [性能调优指南](https://milvus.io/docs/performance_faq.md)
- [生产环境部署建议](https://milvus.io/docs/deploy_milvus.md)

### 社区资源
- [Milvus 中文社区](https://milvus.io/cn/)
- [技术博客](https://milvus.io/blog)
- [FAQ](https://milvus.io/docs/faq.md)

## 🎯 下一步

完成 Milvus standalone 部署后，可以：

1. **运行测试脚本**验证部署成功
2. **执行性能基准测试**了解系统能力
3. **开始开发向量服务**集成到Agent系统
4. **参考主项目计划**继续第一周的其他任务

这个 standalone 部署为后续的开发工作提供了稳定的基础环境！🎉

---

**版本**: v1.0
**更新时间**: 2025年1月
**适用版本**: Milvus v2.3.3
**维护**: 开发团队