import os
import sys
import json
from dotenv import load_dotenv
from openai import OpenAI
from service.core.rag.utils.milvus_conn import MilvusConnection
from service.core.rag.nlp.model import generate_embedding
# 加载环境变量
load_dotenv()

def generate_embedding(text: str, api_key: str = None, base_url: str = None, model_name: str = "text-embedding-v3", dimensions: int = 1024, encoding_format: str = "float"):
    """生成文本向量嵌入"""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    base_url = os.getenv("DASHSCOPE_BASE_URL")

    # 初始化 OpenAI 客户端
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )

    # 调用 OpenAI 的嵌入接口
    try:
        completion = client.embeddings.create(
            model=model_name,
            input=text,
            dimensions=dimensions,
            encoding_format=encoding_format
        )
        embedding = completion.data[0].embedding
        return embedding
    except Exception as e:
        print(f"OpenAI API 请求失败: {e}")
        return None



class PolicySearchService:
    """政策文档搜索服务类，使用Milvus提供各种检索方法，返回数据结构而不是打印结果"""

    def __init__(self, milvus_host=None, milvus_port=None, collection_name="policy_documents"):
        """初始化Milvus连接和集合名称"""
        self.milvus_conn = MilvusConnection()
        self.collection_name = collection_name
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        self.base_url = os.getenv("DASHSCOPE_BASE_URL")

    def check_connection(self):
        """检查Milvus连接状态

        Returns:
            dict: 包含连接状态信息的字典
        """
        try:
            health = self.milvus_conn.health()
            status = health.get("status")

            if status == "healthy":
                return {
                    "success": True,
                    "status": status,
                    "message": f"Milvus连接正常，服务状态: {status}"
                }
            else:
                return {
                    "success": False,
                    "status": status,
                    "message": f"Milvus服务状态异常: {status}"
                }
        except Exception as e:
            return {
                "success": False,
                "status": "error",
                "message": f"Milvus连接异常: {str(e)}"
            }

    def get_collection_info(self):
        """获取集合信息

        Returns:
            dict: 包含集合统计信息的字典
        """
        try:
            # 检查集合是否存在
            if not self.milvus_conn.indexExist(self.collection_name, "policy_kb"):
                return {
                    "success": False,
                    "message": f"集合 '{self.collection_name}' 不存在"
                }

            # 获取集合统计信息
            # Milvus的统计信息需要通过查询获取
            from pymilvus import Collection, utility

            collection_name = f"{self.collection_name}_policy_kb".lower()
            if utility.has_collection(collection_name):
                collection = Collection(collection_name)
                collection.load()

                # 获取文档数量
                count = collection.num_entities

                # 获取字段信息
                schema = collection.schema
                fields = [field.name for field in schema.fields]

                # 获取一个示例文档
                results = collection.query(
                    expr="",
                    output_fields=["title", "content", "website"],
                    limit=1
                )

                has_sample = len(results) > 0
                sample_doc = results[0] if has_sample else None

                return {
                    "success": True,
                    "collection_name": self.collection_name,
                    "doc_count": count,
                    "fields": fields,
                    "sample_doc": sample_doc
                }
            else:
                return {
                    "success": False,
                    "message": f"集合 '{collection_name}' 不存在"
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"获取集合信息出错: {str(e)}"
            }

    def list_collections(self):
        """列出所有集合

        Returns:
            dict: 包含所有集合信息的字典
        """
        try:
            from pymilvus import utility

            collections = utility.list_collections()
            return {
                "success": True,
                "collections": collections
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"获取集合列表出错: {str(e)}"
            }

    def get_document(self, doc_id):
        """获取指定文档的完整内容

        Args:
            doc_id (str): 文档ID

        Returns:
            dict: 包含文档完整内容的字典
        """
        try:
            result = self.milvus_conn.get(doc_id, self.collection_name, ["policy_kb"])

            if result:
                return {
                    "success": True,
                    "document": result,
                    "id": doc_id,
                    "collection": self.collection_name
                }
            else:
                return {
                    "success": False,
                    "message": f"文档 '{doc_id}' 未找到"
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"获取文档出错: {str(e)}"
            }

    def hybrid_search(self, query, top_n=3):
        """混合检索：结合向量检索和关键词检索

        Args:
            query (str): 查询关键词
            top_n (int): 返回结果数量

        Returns:
            dict: 包含搜索结果的字典
        """
        try:
            # 获取查询的向量表示
            query_vector = generate_embedding(
                query,
                api_key=self.api_key,
                base_url=self.base_url
            )

            if not query_vector:
                return {
                    "success": False,
                    "message": "无法生成查询向量，请检查API配置"
                }

            # 构建搜索请求
            from service.core.rag.utils.doc_store_conn import MatchTextExpr, MatchDenseExpr, FusionExpr, OrderByExpr

            # 文本搜索表达式
            match_text = MatchTextExpr(
                fields=["title", "content"],
                matching_text=query,
                topn=top_n * 2,  # 获取更多结果用于融合
                extra_options={"minimum_should_match": "30%"}
            )

            # 向量搜索表达式
            match_dense = MatchDenseExpr(
                vector_column_name=f"q_{len(query_vector)}_vec",
                embedding_data=query_vector,
                embedding_data_type="float",
                distance_type="cosine",
                topn=top_n * 2,
                extra_options={"similarity": 0.1}
            )

            # 融合表达式
            fusion_expr = FusionExpr("weighted_sum", top_n, {"weights": "0.4, 0.6"})

            # 执行搜索
            result = self.milvus_conn.search(
                selectFields=["title", "content", "website", "detail_url", "date"],
                highlightFields=["title", "content"],
                condition={},
                matchExprs=[match_text, match_dense, fusion_expr],
                orderBy=OrderByExpr(),
                offset=0,
                limit=top_n,
                indexNames=self.collection_name,
                knowledgebaseIds=["policy_kb"]
            )

            # 处理结果
            total = self.milvus_conn.getTotal(result)
            ids = self.milvus_conn.getChunkIds(result)
            fields = self.milvus_conn.getFields(result, ["title", "content", "website", "detail_url", "date"])
            highlight = self.milvus_conn.getHighlight(result, [query], "content_with_weight")

            search_results = []

            for i, chunk_id in enumerate(ids[:top_n]):
                if chunk_id in fields:
                    item = fields[chunk_id]

                    # 构建搜索结果项
                    result_item = {
                        "id": chunk_id,
                        "title": item.get("title", ""),
                        "website": item.get("website", ""),
                        "detail_url": item.get("detail_url", ""),
                        "date": item.get("date", ""),
                        "content": item.get("content", ""),
                        "content_preview": item.get("content", "")[:300] + "..." if len(item.get("content", "")) > 300 else item.get("content", ""),
                        "score": 0.8  # Milvus返回的分数需要转换
                    }

                    # 添加高亮信息（如果有）
                    if chunk_id in highlight:
                        result_item["highlights"] = {"content": highlight[chunk_id]}

                    search_results.append(result_item)

            return {
                "success": True,
                "query": query,
                "method": "hybrid",
                "total": len(search_results),
                "results": search_results
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"搜索出错: {str(e)}"
            }

    def keyword_search(self, query, top_n=10):
        """仅使用关键词搜索

        Args:
            query (str): 查询关键词
            top_n (int): 返回结果数量

        Returns:
            dict: 包含搜索结果的字典
        """
        try:
            # 构建文本搜索表达式
            from service.core.rag.utils.doc_store_conn import MatchTextExpr, OrderByExpr

            match_text = MatchTextExpr(
                fields=["title", "content"],
                matching_text=query,
                topn=top_n,
                extra_options={"minimum_should_match": "30%"}
            )

            # 执行搜索
            result = self.milvus_conn.search(
                selectFields=["title", "content", "website", "detail_url", "date"],
                highlightFields=["title", "content"],
                condition={},
                matchExprs=[match_text],
                orderBy=OrderByExpr(),
                offset=0,
                limit=top_n,
                indexNames=self.collection_name,
                knowledgebaseIds=["policy_kb"]
            )

            # 处理结果
            total = self.milvus_conn.getTotal(result)
            ids = self.milvus_conn.getChunkIds(result)
            fields = self.milvus_conn.getFields(result, ["title", "content", "website", "detail_url", "date"])
            highlight = self.milvus_conn.getHighlight(result, [query], "content_with_weight")

            search_results = []

            for chunk_id in ids[:top_n]:
                if chunk_id in fields:
                    item = fields[chunk_id]

                    result_item = {
                        "id": chunk_id,
                        "title": item.get("title", ""),
                        "website": item.get("website", ""),
                        "detail_url": item.get("detail_url", ""),
                        "date": item.get("date", ""),
                        "content": item.get("content", ""),
                        "content_preview": item.get("content", "")[:300] + "..." if len(item.get("content", "")) > 300 else item.get("content", ""),
                        "score": 0.7
                    }

                    # 添加高亮信息（如果有）
                    if chunk_id in highlight:
                        result_item["highlights"] = {"content": highlight[chunk_id]}

                    search_results.append(result_item)

            return {
                "success": True,
                "query": query,
                "method": "keyword",
                "total": len(search_results),
                "results": search_results
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"搜索出错: {str(e)}"
            }

    def vector_search(self, query, top_n=10):
        """仅使用向量搜索

        Args:
            query (str): 查询关键词
            top_n (int): 返回结果数量

        Returns:
            dict: 包含搜索结果的字典
        """
        try:
            # 获取查询的向量表示
            query_vector = generate_embedding(
                query,
                api_key=self.api_key,
                base_url=self.base_url
            )

            if not query_vector:
                return {
                    "success": False,
                    "message": "无法生成查询向量，请检查API配置"
                }

            # 构建向量搜索表达式
            from service.core.rag.utils.doc_store_conn import MatchDenseExpr, OrderByExpr

            match_dense = MatchDenseExpr(
                vector_column_name=f"q_{len(query_vector)}_vec",
                embedding_data=query_vector,
                embedding_data_type="float",
                distance_type="cosine",
                topn=top_n,
                extra_options={"similarity": 0.1}
            )

            # 执行搜索
            result = self.milvus_conn.search(
                selectFields=["title", "content", "website", "detail_url", "date"],
                highlightFields=[],
                condition={},
                matchExprs=[match_dense],
                orderBy=OrderByExpr(),
                offset=0,
                limit=top_n,
                indexNames=self.collection_name,
                knowledgebaseIds=["policy_kb"]
            )

            # 处理结果
            total = self.milvus_conn.getTotal(result)
            ids = self.milvus_conn.getChunkIds(result)
            fields = self.milvus_conn.getFields(result, ["title", "content", "website", "detail_url", "date"])

            search_results = []

            for chunk_id in ids[:top_n]:
                if chunk_id in fields:
                    item = fields[chunk_id]

                    result_item = {
                        "id": chunk_id,
                        "title": item.get("title", ""),
                        "website": item.get("website", ""),
                        "detail_url": item.get("detail_url", ""),
                        "date": item.get("date", ""),
                        "content": item.get("content", ""),
                        "content_preview": item.get("content", "")[:300] + "..." if len(item.get("content", "")) > 300 else item.get("content", ""),
                        "score": 0.9  # 向量搜索分数通常较高
                    }

                    search_results.append(result_item)

            return {
                "success": True,
                "query": query,
                "method": "vector",
                "total": len(search_results),
                "results": search_results
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"搜索出错: {str(e)}"
            }

    def search(self, query, method="hybrid", top_n=10):
        """统一的搜索接口，根据method参数选择不同的搜索方法

        Args:
            query (str): 查询关键词
            method (str): 搜索方法，可选值：hybrid, keyword, vector
            top_n (int): 返回结果数量

        Returns:
            dict: 包含搜索结果的字典
        """
        if method == "hybrid":
            return self.hybrid_search(query, top_n)
        elif method == "keyword":
            return self.keyword_search(query, top_n)
        elif method == "vector":
            return self.vector_search(query, top_n)
        else:
            return {
                "success": False,
                "message": f"不支持的搜索方法: {method}，可选值：hybrid, keyword, vector"
            }


# 示例用法
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="政策文档搜索服务")
    parser.add_argument("query", nargs="?", default=None, help="搜索查询")
    parser.add_argument("--method", "-m", choices=["hybrid", "keyword", "vector"], default="hybrid",
                        help="搜索方法: hybrid(混合搜索), keyword(关键词搜索), vector(向量搜索)")
    parser.add_argument("--top", "-n", type=int, default=5, help="返回的结果数量")
    parser.add_argument("--doc-id", "-d", help="获取指定文档的内容")
    parser.add_argument("--connection", "-c", action="store_true", help="检查Milvus连接状态")
    parser.add_argument("--collection-info", "-i", action="store_true", help="获取集合信息")
    parser.add_argument("--list-collections", "-l", action="store_true", help="列出所有集合")
    parser.add_argument("--pretty", "-p", action="store_true", help="美化输出的JSON")

    args = parser.parse_args()

    # 初始化服务对象
    service = PolicySearchService()
    result = None

    # 执行相应操作
    if args.connection:
        result = service.check_connection()
    elif args.collection_info:
        result = service.get_collection_info()
    elif args.list_collections:
        result = service.list_collections()
    elif args.doc_id:
        result = service.get_document(args.doc_id)
    elif args.query:
        result = service.search(args.query, args.method, args.top)
    else:
        parser.print_help()
        sys.exit(1)

    # 输出结果
    if result:
        if args.pretty:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(result, ensure_ascii=False))