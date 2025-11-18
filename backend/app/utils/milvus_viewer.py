#!/usr/bin/env python3
"""
Milvus数据查看工具
用于调试和查看Milvus中的数据存储情况
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from pymilvus import utility, connections, Collection
from services.milvus.milvus_service import MilvusService

async def view_collection_data(collection_name: str, limit: int = 5):
    """
    查看指定集合的数据结构

    Args:
        collection_name: 集合名称
        limit: 显示的记录数量
    """
    print(f"\n=== 查看集合: {collection_name} ===")

    try:
        # 连接Milvus
        milvus_service = MilvusService(
            host=os.getenv("MILVUS_HOST", "milvus-standalone"),
            port=os.getenv("MILVUS_PORT", "19530")
        )

        if not await milvus_service.connect():
            print("❌ 无法连接到Milvus")
            return

        # 检查集合是否存在
        if not utility.has_collection(collection_name):
            print(f"❌ 集合 {collection_name} 不存在")
            return

        # 获取集合
        collection = Collection(collection_name)

        # 查看集合schema
        print("\n📋 集合Schema:")
        print(f"集合名称: {collection.name}")
        print(f"集合描述: {collection.description}")
        print(f"分片数量: {collection.num_shards}")

        print("\n📊 字段信息:")
        for field in collection.schema.fields:
            print(f"  - {field.name}: {field.dtype}")
            if field.dtype.name == 'FLOAT_VECTOR':
                print(f"    维度: {field.dim}")
            elif field.dtype.name == 'VARCHAR':
                print(f"    最大长度: {field.max_length}")

        # 查看统计信息
        print(f"\n📈 数据统计:")
        print(f"记录数量: {collection.num_entities}")

        # 查看索引信息
        print(f"\n🔍 索引信息:")
        indexes = collection.indexes
        for index in indexes:
            print(f"  - 索引字段: {index.field_name}")
            print(f"    索引类型: {index.index_type}")
            print(f"    索引参数: {index.params}")

        # 加载集合并查看样本数据
        collection.load()

        print(f"\n📄 样本数据 (前{limit}条):")

        # 查询样本数据
        results = collection.query(
            expr="id >= 0",
            output_fields=["*", "q_1024_vec"],
            limit=limit
        )

        for i, record in enumerate(results):
            print(f"\n--- 记录 {i+1} ---")
            for key, value in record.items():
                if key == "q_1024_vec":
                    # 向量数据只显示部分信息
                    if isinstance(value, list) and len(value) > 0:
                        print(f"{key}: 向量[{len(value)}维] 前5个值: {value[:5]}...")
                    else:
                        print(f"{key}: {value}")
                elif key == "metadata" and isinstance(value, dict):
                    print(f"{key}: {value}")
                elif isinstance(value, str) and len(value) > 100:
                    print(f"{key}: {value[:100]}...")
                else:
                    print(f"{key}: {value}")

        # 关闭连接
        await milvus_service.disconnect()
        print(f"\n✅ 数据查看完成")

    except Exception as e:
        print(f"❌ 查看数据失败: {e}")
        import traceback
        traceback.print_exc()

async def list_all_collections():
    """列出所有集合"""
    print("\n=== 所有Milvus集合 ===")

    try:
        # 连接Milvus
        milvus_service = MilvusService(
            host=os.getenv("MILVUS_HOST", "milvus-standalone"),
            port=os.getenv("MILVUS_PORT", "19530")
        )

        if not await milvus_service.connect():
            print("❌ 无法连接到Milvus")
            return

        # 列出所有集合
        collections = utility.list_collections()

        if not collections:
            print("没有找到任何集合")
            return

        print(f"找到 {len(collections)} 个集合:")
        for collection_name in collections:
            collection = Collection(collection_name)
            entity_count = collection.num_entities
            print(f"  - {collection_name}: {entity_count} 条记录")

        await milvus_service.disconnect()

    except Exception as e:
        print(f"❌ 列出集合失败: {e}")

async def search_specific_data(collection_name: str, query_text: str = "人工智能", top_k: int = 3):
    """
    搜索特定查询的数据

    Args:
        collection_name: 集合名称
        query_text: 查询文本
        top_k: 返回结果数量
    """
    print(f"\n=== 搜索测试: '{query_text}' 在集合 {collection_name} ===")

    try:
        # 连接Milvus
        milvus_service = MilvusService(
            host=os.getenv("MILVUS_HOST", "milvus-standalone"),
            port=os.getenv("MILVUS_PORT", "19530")
        )

        if not await milvus_service.connect():
            print("❌ 无法连接到Milvus")
            return

        # 生成查询向量
        from dashscope import TextEmbedding
        import dashscope

        dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

        embedding_response = TextEmbedding.call(
            model=TextEmbedding.Models.text_embedding_v3,
            input=query_text,
            dimension=1024
        )

        if embedding_response.status_code != 200:
            print(f"❌ 生成查询向量失败: {embedding_response.message}")
            return

        query_vector = embedding_response.output["embeddings"][0]["embedding"]

        # 执行搜索
        search_results = await milvus_service.search(
            collection_name=collection_name,
            query_vector=query_vector,
            top_k=top_k,
            search_params={
                "metric_type": "COSINE",
                "params": {"ef": 64}
            }
        )

        print(f"\n🔍 搜索结果 (找到 {len(search_results)} 条):")

        for i, result in enumerate(search_results):
            print(f"\n--- 结果 {i+1} ---")
            print(f"ID: {result.id}")
            print(f"Score: {result.score}")
            print(f"Doc ID: {result.doc_id}")
            print(f"Doc Name: {result.doc_name}")
            print(f"Category: {result.category}")
            print(f"Confidence: {result.confidence}")
            print(f"Chunk ID: {result.chunk_id}")
            print(f"Source: {result.source}")
            print(f"Content: {result.content[:200]}...")
            if result.metadata:
                print(f"Metadata: {result.metadata}")

        await milvus_service.disconnect()

    except Exception as e:
        print(f"❌ 搜索失败: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """主函数"""
    import sys

    print("Milvus 数据查看工具")
    print("=" * 50)

    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python milvus_viewer.py list                    # 列出所有集合")
        print("  python milvus_viewer.py view <collection_name>  # 查看集合数据")
        print("  python milvus_viewer.py search <collection_name> [query_text]  # 搜索测试")
        print("\n示例:")
        print("  python milvus_viewer.py view user_collection_123")
        print("  python milvus_viewer.py search user_collection_123 '人工智能'")
        return

    command = sys.argv[1]

    if command == "list":
        await list_all_collections()
    elif command == "view":
        if len(sys.argv) < 3:
            print("请提供集合名称")
            return
        collection_name = sys.argv[2]
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        await view_collection_data(collection_name, limit)
    elif command == "search":
        if len(sys.argv) < 3:
            print("请提供集合名称")
            return
        collection_name = sys.argv[2]
        query_text = sys.argv[3] if len(sys.argv) > 3 else "人工智能"
        top_k = int(sys.argv[4]) if len(sys.argv) > 4 else 3
        await search_specific_data(collection_name, query_text, top_k)
    else:
        print(f"未知命令: {command}")

if __name__ == "__main__":
    asyncio.run(main())