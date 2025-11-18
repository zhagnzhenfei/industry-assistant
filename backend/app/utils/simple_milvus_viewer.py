#!/usr/bin/env python3
"""
简化版Milvus数据查看工具
"""

import asyncio
import os
from pymilvus import utility, connections, Collection

async def list_all_collections():
    """列出所有集合"""
    print("\n=== 所有Milvus集合 ===")

    try:
        # 连接Milvus
        connections.connect(
            alias="default",
            host=os.getenv("MILVUS_HOST", "milvus-standalone"),
            port=int(os.getenv("MILVUS_PORT", "19530"))
        )

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

        # 断开连接
        connections.disconnect("default")

    except Exception as e:
        print(f"❌ 列出集合失败: {e}")

async def view_collection_data(collection_name: str, limit: int = 3):
    """查看集合数据"""
    print(f"\n=== 查看集合: {collection_name} ===")

    try:
        # 连接Milvus
        connections.connect(
            alias="default",
            host=os.getenv("MILVUS_HOST", "milvus-standalone"),
            port=int(os.getenv("MILVUS_PORT", "19530"))
        )

        # 检查集合是否存在
        if not utility.has_collection(collection_name):
            print(f"❌ 集合 {collection_name} 不存在")
            return

        # 获取集合
        collection = Collection(collection_name)

        # 查看集合schema
        print(f"\n📋 集合信息:")
        print(f"集合名称: {collection.name}")
        print(f"记录数量: {collection.num_entities}")

        print(f"\n📊 字段信息:")
        for field in collection.schema.fields:
            print(f"  - {field.name}: {field.dtype}")
            if hasattr(field, 'dim'):
                print(f"    维度: {field.dim}")
            if hasattr(field, 'max_length'):
                print(f"    最大长度: {field.max_length}")

        # 加载集合并查看样本数据
        collection.load()

        print(f"\n📄 样本数据 (前{limit}条):")

        # 查询样本数据
        try:
            results = collection.query(
                expr="id >= 0",
                output_fields=["id", "doc_id", "doc_name", "category", "confidence", "source", "content"],
                limit=limit
            )

            for i, record in enumerate(results):
                print(f"\n--- 记录 {i+1} ---")
                for key, value in record.items():
                    if key == "content" and isinstance(value, str) and len(value) > 150:
                        print(f"{key}: {value[:150]}...")
                    else:
                        print(f"{key}: {value}")

        except Exception as query_error:
            print(f"查询数据失败: {query_error}")

        # 断开连接
        connections.disconnect("default")

    except Exception as e:
        print(f"❌ 查看数据失败: {e}")
        import traceback
        traceback.print_exc()

async def search_test(collection_name: str, query_text: str = "人工智能"):
    """搜索测试"""
    print(f"\n=== 搜索测试: '{query_text}' 在集合 {collection_name} ===")

    try:
        # 连接Milvus
        connections.connect(
            alias="default",
            host=os.getenv("MILVUS_HOST", "milvus-standalone"),
            port=int(os.getenv("MILVUS_PORT", "19530"))
        )

        # 生成查询向量
        from dashscope import TextEmbedding
        import dashscope

        dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

        if not dashscope.api_key:
            print("❌ 未设置DASHSCOPE_API_KEY，无法生成查询向量")
            return

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
        collection = Collection(collection_name)
        collection.load()

        search_results = collection.search(
            data=[query_vector],
            anns_field="vector",
            param={"metric_type": "COSINE", "params": {"ef": 64}},
            limit=5,
            output_fields=["id", "doc_id", "doc_name", "category", "confidence", "source", "content"],
            consistency_level="Strong"
        )

        print(f"\n🔍 搜索结果:")

        if search_results and len(search_results) > 0:
            for i, hit in enumerate(search_results[0]):
                print(f"\n--- 结果 {i+1} ---")
                print(f"ID: {hit.id}")
                print(f"Score: {hit.score}")

                # 显示字段信息
                for key in hit.entity.keys():
                    value = hit.entity[key]
                    if key == "content" and isinstance(value, str) and len(value) > 150:
                        print(f"{key}: {value[:150]}...")
                    else:
                        print(f"{key}: {value}")
        else:
            print("没有找到搜索结果")

        # 断开连接
        connections.disconnect("default")

    except Exception as e:
        print(f"❌ 搜索失败: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """主函数"""
    import sys

    print("Milvus 数据查看工具 (简化版)")
    print("=" * 50)

    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python simple_milvus_viewer.py list                    # 列出所有集合")
        print("  python simple_milvus_viewer.py view <collection_name>  # 查看集合数据")
        print("  python simple_milvus_viewer.py search <collection_name> [query_text]  # 搜索测试")
        print("\n示例:")
        print("  python simple_milvus_viewer.py view user_collection_123")
        print("  python simple_milvus_viewer.py search user_collection_123 '人工智能'")
        return

    command = sys.argv[1]

    if command == "list":
        await list_all_collections()
    elif command == "view":
        if len(sys.argv) < 3:
            print("请提供集合名称")
            return
        collection_name = sys.argv[2]
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 3
        await view_collection_data(collection_name, limit)
    elif command == "search":
        if len(sys.argv) < 3:
            print("请提供集合名称")
            return
        collection_name = sys.argv[2]
        query_text = sys.argv[3] if len(sys.argv) > 3 else "人工智能"
        await search_test(collection_name, query_text)
    else:
        print(f"未知命令: {command}")

if __name__ == "__main__":
    asyncio.run(main())