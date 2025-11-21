import os
import time
import hashlib
from typing import List, Optional
from fastapi import HTTPException, status
from utils.database import default_manager
from models import Document, User
from schemas.document import MilvusSearchResponse, MilvusSearchResult
from service.core.file_parse import execute_insert_process


class DocumentManagementService:
    """文档管理服务"""
    
    def __init__(self):
        pass
    
    def calculate_file_hash(self, file_name: str) -> str:
        """计算文件名的SHA256哈希值"""
        hash_sha256 = hashlib.sha256()
        hash_sha256.update(file_name.encode('utf-8'))
        return hash_sha256.hexdigest()
    
    def check_duplicate_file(self, user_id: str, file_hash: str) -> Optional[Document]:
        """检查用户是否已经上传过相同文件名的文件"""
        try:
            db = default_manager.session_factory()
            try:
                existing_doc = db.query(Document).filter(
                    Document.user_id == user_id,
                    Document.file_hash == file_hash
                ).first()
                return existing_doc
            finally:
                db.close()
        except Exception as e:
            print(f"检查重复文件失败: {e}")
            return None
    
    def create_document(self, user_id: str, file_name: str, file_path: str, 
                       file_size: int = None, file_type: str = None, file_hash: str = None) -> Document:
        """创建文档记录"""
        try:
            db = default_manager.session_factory()
            try:
                # 创建新文档记录
                new_document = Document(
                    user_id=user_id,
                    file_name=file_name,
                    file_path=file_path,
                    file_size=file_size,
                    file_type=file_type,
                    file_hash=file_hash,
                    status='uploading'
                )
                
                db.add(new_document)
                db.commit()
                db.refresh(new_document)
                
                return new_document
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"创建文档记录失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建文档记录失败: {str(e)}"
            )
    
    def update_document_status(self, document_id: str, status: str, 
                             chunk_count: int = None, error_message: str = None) -> Document:
        """更新文档状态"""
        try:
            db = default_manager.session_factory()
            try:
                document = db.query(Document).filter(Document.document_id == document_id).first()
                if not document:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="文档不存在"
                    )
                
                document.status = status
                document.updated_at = int(time.time())
                
                if chunk_count is not None:
                    document.chunk_count = chunk_count
                if error_message is not None:
                    document.error_message = error_message
                
                db.commit()
                db.refresh(document)
                
                return document
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"更新文档状态失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"更新文档状态失败: {str(e)}"
            )
    
    def process_document_to_vector_store(self, file_path: str, file_name: str, user_id: str) -> int:
        """处理文档并存入Milvus向量数据库"""
        try:
            import time
            from service.core.file_parse import parse
            from service.core.rag.nlp.model import generate_embedding
            from services.milvus.milvus_service import MilvusService
            from services.milvus.models import DocumentChunk, CollectionConfig
            import xxhash

            print(f"开始处理文档: {file_name} 用户ID: {user_id}")

            # 解析文档
            chunks = parse(file_path)
            if not chunks:
                raise ValueError("文档解析失败，没有获取到任何内容")

            print(f"文档解析成功，获得 {len(chunks)} 个分块")


            # 初始化Milvus服务
            try:
                milvus_service = MilvusService(
                    host=os.getenv("MILVUS_HOST", "milvus-standalone"),
                    port=os.getenv("MILVUS_PORT", "19530")
                )

                # 连接Milvus（使用同步方法）
                connected = milvus_service.connect_sync()
                if connected:
                    print("✅ Milvus连接成功")
                    use_milvus = True
                else:
                    print("❌ Milvus连接失败")
                    use_milvus = False
            except Exception as e:
                print(f"Milvus初始化失败: {e}")
                use_milvus = False

            # 构建集合名称
            collection_name = f"user_collection_{user_id}".replace("-", "_")
            print(f"集合名称: {collection_name}")

            # 确保Milvus集合存在 - 使用全局连接
            if use_milvus:
                try:
                    # 使用全局连接名称连接
                    from pymilvus import connections, utility

                    # 确保使用默认连接
                    if not connections.has_connection("default"):
                        print("创建默认Milvus连接...")
                        connections.connect(
                            alias="default",
                            host=os.getenv("MILVUS_HOST", "milvus-standalone"),
                            port=os.getenv("MILVUS_PORT", "19530")
                        )

                    print(f"🔍 检查Milvus集合: {collection_name}")

                    # 强制调用create_collection_sync来检查和可能重建集合
                    # 无论集合是否存在，都要检查schema是否正确
                    config = CollectionConfig(collection_name=collection_name)
                    success = milvus_service.create_collection_sync(collection_name, config)

                    if success:
                        if not utility.has_collection(collection_name):
                            print("✅ Milvus集合创建成功")
                        else:
                            print("✅ Milvus集合检查/重建成功")

                        # 创建索引（如果需要）
                        index_success = milvus_service.create_index_sync(collection_name, "vector")
                        if index_success:
                            print("✅ Milvus索引创建成功")
                        else:
                            print("❌ Milvus索引创建失败")
                    else:
                        print("❌ Milvus集合创建失败")
                except Exception as e:
                    print(f"Milvus集合操作失败: {e}")
                    use_milvus = False

            # 处理每个分块
            milvus_chunks = []

            for i, chunk_data in enumerate(chunks):
                try:
                    print(f"处理分块 {i+1}/{len(chunks)}...")
                    print(chunk_data)

                    # 生成唯一的chunk_id，包含文档唯一标识和分块索引
                    doc_unique_id = chunk_data.get('doc_id', file_name) or file_name
                    unique_string = f"{doc_unique_id}_{user_id}_{i}_{chunk_data['content_with_weight']}"
                    chunk_id = xxhash.xxh64(unique_string.encode("utf-8")).hexdigest()

                    # 生成向量嵌入
                    embedding = generate_embedding(chunk_data['content_with_weight'])

                    # 构建Milvus分块
                    if use_milvus:
                        milvus_chunk = DocumentChunk(
                            vector=embedding,
                            content=chunk_data['content_with_weight'],
                            content_ltks=chunk_data.get('content_ltks', ''),
                            doc_id=chunk_data.get('doc_id', chunk_data.get('docnm_kwd', '')),
                            doc_name=file_name,
                            kb_id=user_id,
                            chunk_id=chunk_id,
                            category="document",
                            timestamp=int(time.time()),
                            source=file_name,
                            keywords="",
                            metadata={"chunk_index": i, "chunk_id": chunk_id}
                        )
                        milvus_chunks.append(milvus_chunk)

                except Exception as e:
                    print(f"处理分块 {i} 失败: {e}")
                    continue

            print(f"处理完成, Milvus分块: {len(milvus_chunks)}")

            # 批量插入到Milvus
            if use_milvus and milvus_chunks:
                print(f"插入数据到Milvus，共 {len(milvus_chunks)} 条...")
                success = milvus_service.insert_data_sync(collection_name, milvus_chunks)
                if success:
                    print("✅ Milvus插入成功")
                else:
                    print("❌ Milvus插入失败")
                    # 如果Milvus插入失败，清空milvus_chunks表示处理失败
                    milvus_chunks = []

            print(f"文档处理完成，总共处理 {len(milvus_chunks)} 个分块")

            # 返回成功处理的块数
            return len(milvus_chunks)

        except Exception as e:
            print(f"文档处理失败: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"文档处理失败: {str(e)}"
            )

    async def search_documents_with_milvus(self, user_id: str, query: str, top_k: int = 10,
                                         similarity_threshold: float = 0.2, category: Optional[str] = None,
                                         enable_hybrid_search: bool = False,
                                         vector_weight: float = 0.5,
                                         text_threshold: float = 0.3) -> MilvusSearchResponse:
        """使用Milvus进行向量搜索或混合搜索（向量+文本）

        Args:
            user_id: 用户ID
            query: 搜索查询文本
            top_k: 返回结果数量
            similarity_threshold: 向量相似度阈值
            category: 文档类别过滤
            enable_hybrid_search: 是否启用混合检索
            vector_weight: 向量检索权重，范围0-1，文本权重自动计算为1-vector_weight
            text_threshold: 文本相关性阈值

        Returns:
            MilvusSearchResponse: 搜索结果响应
        """
        try:
            import time
            import os
            from services.milvus.milvus_service import MilvusService

            search_type = "hybrid" if enable_hybrid_search else "vector"
            print(f"开始{search_type}搜索: {query}")
            print(f"🔧 混合搜索参数调试:")
            print(f"  enable_hybrid_search: {enable_hybrid_search}")
            print(f"  vector_weight: {vector_weight}")
            print(f"  text_threshold: {text_threshold}")
            if enable_hybrid_search:
                text_weight = 1.0 - vector_weight
                print(f"混合搜索参数 - 向量权重: {vector_weight}, 文本权重: {text_weight:.3f}, 文本阈值: {text_threshold}")

            # 初始化Milvus服务
            milvus_service = MilvusService(
                host=os.getenv("MILVUS_HOST", "milvus-standalone"),
                port=os.getenv("MILVUS_PORT", "19530")
            )

            # 连接Milvus
            if not await milvus_service.connect():
                print("❌ 无法连接到Milvus服务")
                return MilvusSearchResponse(
                    query=query,
                    total=0,
                    results=[],
                    search_time=0.0,
                    search_type=search_type,
                    vector_results_count=0,
                    text_results_count=0
                )

            # 构建集合名称
            collection_name = f"user_collection_{user_id}".replace("-", "_")

            # 检查集合是否存在
            from pymilvus import utility
            if not utility.has_collection(collection_name):
                print(f"集合 {collection_name} 不存在")
                return MilvusSearchResponse(
                    query=query,
                    total=0,
                    results=[],
                    search_time=0.0,
                    search_type=search_type,
                    vector_results_count=0,
                    text_results_count=0
                )

            # 自动计算文本权重
            text_weight = 1.0 - vector_weight
            print(f"⚖️  权重分配: vector_weight={vector_weight}, text_weight={text_weight:.3f}")

            # 检查权重有效性
            if vector_weight < 0 or vector_weight > 1:
                print("⚠️  向量权重超出范围0-1")
                return MilvusSearchResponse(
                    query=query,
                    total=0,
                    results=[],
                    search_time=0.0,
                    search_type="error",
                    vector_results_count=0,
                    text_results_count=0
                )

            # 导入必要的类（避免条件导入导致的问题）
            from schemas.document import MilvusSearchResult

            # 初始化变量
            vector_filtered_results = []
            search_time = 0.0

            # 根据权重决定是否执行向量搜索
            if vector_weight > 0:
                print(f"🔄 开始执行向量搜索...")

                start_time = time.time()

                # 生成查询向量
                try:
                    from service.core.rag.nlp.model import generate_embedding
                    embed_start = time.time()
                    query_vector = generate_embedding(query)
                    embed_time = time.time() - embed_start
                    print(f"✅ 查询向量生成成功，维度: {len(query_vector)} (耗时: {embed_time:.3f}s)")
                except Exception as e:
                    print(f"❌ 生成查询向量失败: {e}")
                    if not enable_hybrid_search:
                        # 纯向量搜索失败，直接返回错误
                        return MilvusSearchResponse(
                            query=query,
                            total=0,
                            results=[],
                            search_time=0.0,
                            search_type=search_type,
                            vector_results_count=0,
                            text_results_count=0
                        )
                    else:
                        # 混合搜索模式，继续执行文本搜索
                        query_vector = None

                # 构建过滤条件
                filter_parts = []
                if category:
                    filter_parts.append(f'category == "{category}"')

                filter_expr = " AND ".join(filter_parts) if filter_parts else None

                # 执行向量搜索
                from services.milvus.models import SearchResult as MilvusEntityResult

                if query_vector:
                    # 确定向量搜索获取足够的候选结果
                    # 混合搜索时获取更多候选进行rerank，纯向量搜索时使用top_k
                    vector_search_size = top_k if not enable_hybrid_search else min(50, top_k * 3)
                    
                    milvus_start = time.time()
                    search_results = await milvus_service.search(
                        collection_name=collection_name,
                        query_vector=query_vector,
                        top_k=vector_search_size,
                        filter_expr=filter_expr,
                        output_fields=["content", "doc_id", "doc_name", "category", "source", "metadata", "chunk_id"],
                        search_params={
                            "metric_type": "COSINE",
                            "params": {"ef": 64}
                        }
                    )
                    milvus_time = time.time() - milvus_start
                    print(f"✅ Milvus搜索执行完成 (耗时: {milvus_time:.3f}s)")

                    search_time = time.time() - start_time

                    # 对于混合搜索，不在这里过滤，让rerank决定最终结果
                    # 对于纯向量搜索，仍然应用阈值过滤
                    if enable_hybrid_search:
                        vector_filtered_results = search_results  # 混合搜索时不应用阈值，让rerank决定
                    else:
                        # 纯向量搜索时应用相似度阈值过滤
                        vector_filtered_results = [
                            result for result in search_results
                            if result.score >= similarity_threshold
                        ]
                        vector_filtered_results = vector_filtered_results[:top_k]
                    print(f"✅ 向量搜索完成，找到 {len(vector_filtered_results)} 个结果")
                else:
                    print(f"⚠️  跳过向量搜索（查询向量生成失败）")
            else:
                print(f"⏭️  向量权重为0，跳过向量搜索")

            # 如果启用混合搜索，根据权重决定执行哪些搜索并合并结果
            text_search_results = []
            hybrid_results = vector_filtered_results

            print(f"🔍 混合搜索条件检查: enable_hybrid_search={enable_hybrid_search}")

            if enable_hybrid_search:
                try:
                    # 根据权重决定是否执行文本搜索
                    if text_weight > 0:
                        print(f"🔄 开始执行BM25文本搜索...")
                        # 文本搜索也获取top_k个结果
                        text_search_results = self._perform_text_search(
                            user_id, query, top_k, text_threshold
                        )
                        print(f"✅ BM25文本搜索完成，找到 {len(text_search_results)} 个结果")
                    else:
                        print(f"⏭️  文本权重为0，跳过BM25文本搜索")

                    # 合并搜索结果，应用混合得分阈值过滤
                    hybrid_results = self._merge_search_results(
                        vector_filtered_results,
                        text_search_results,
                        vector_weight,
                        text_weight,
                        top_k,
                        query,  # 添加 query 参数
                        hybrid_threshold=text_threshold  # 使用text_threshold作为混合得分阈值
                    )
                    print(f"✅ 混合搜索完成，合并后得到 {len(hybrid_results)} 个结果")

                except Exception as hybrid_error:
                    print(f"⚠️  混合搜索失败，回退到向量搜索: {hybrid_error}")
                    hybrid_results = vector_filtered_results

            # 转换结果格式
            milvus_results = []
            for result in hybrid_results:
                # 处理不同类型的结果对象（可能是对象或字典）
                if isinstance(result, dict):
                    # 字典类型的处理
                    milvus_result = MilvusSearchResult(
                        id=result.get('id', 0),
                        score=result.get('score', 0.0),
                        content=result.get('content', ''),
                        doc_id=result.get('doc_id', ''),
                        doc_name=result.get('doc_name', ''),
                        category=result.get('category', ''),
                        source=result.get('source', ''),
                        chunk_id=result.get('chunk_id', ''),
                        text_score=result.get('text_score', 0.0),
                        hybrid_score=result.get('hybrid_score', result.get('score', 0.0))
                    )
                else:
                    # 对象类型的处理
                    hybrid_score = getattr(result, 'hybrid_score', getattr(result, 'score', 0.0))

                    milvus_result = MilvusSearchResult(
                        id=getattr(result, 'id', 0),
                        score=hybrid_score,
                        content=getattr(result, 'content', ''),
                        doc_id=getattr(result, 'doc_id', ''),
                        doc_name=getattr(result, 'doc_name', ''),
                        category=getattr(result, 'category', ''),
                        source=getattr(result, 'source', ''),
                        chunk_id=getattr(result, 'chunk_id', ''),
                        text_score=getattr(result, 'text_score', 0.0),
                        hybrid_score=hybrid_score
                    )
                milvus_results.append(milvus_result)

            return MilvusSearchResponse(
                query=query,
                total=len(milvus_results),
                results=milvus_results,
                search_time=search_time,
                search_type=search_type,
                vector_results_count=len(vector_filtered_results),
                text_results_count=len(text_search_results)
            )

        except Exception as e:
            print(f"Milvus向量搜索失败: {e}")
            import traceback
            traceback.print_exc()
            return MilvusSearchResponse(
                query=query,
                total=0,
                results=[],
                search_time=0.0,
                search_type="error",
                vector_results_count=0,
                text_results_count=0
            )

    def _perform_text_search(self, user_id: str, query: str, top_k: int, text_threshold: float) -> List[dict]:
        """执行基于BM25的文本搜索（优化版本）"""
        print(f"🔍 开始BM25文本搜索: '{query}' (阈值: {text_threshold})")
        
        import time
        text_search_start = time.time()
        
        try:
            from pymilvus import Collection, utility
            import sys
            from pathlib import Path
            
            # 导入BM25搜索器
            sys.path.append(str(Path(__file__).parent.parent))
            from utils.bm25_searcher import BM25Searcher
            
            collection_name = f"user_collection_{user_id}".replace("-", "_")
            collection = Collection(collection_name)
            
            # 优化1：检查加载状态，避免重复加载
            try:
                load_start = time.time()
                load_state = utility.load_state(collection_name)
                if load_state.name not in ['Loaded', 'Loading']:
                    collection.load()
                load_time = time.time() - load_start
                if load_time > 1.0:
                    print(f"⚠️ 集合加载检查/加载耗时: {load_time:.3f}s")
            except:
                collection.load()
            
            # 优化2：智能候选文档选择策略
            # 先通过向量搜索获取相关候选，再对候选进行BM25评分
            candidate_limit = min(50, top_k * 5)  # 动态调整，但最多50个
            
            # 策略1：先进行快速向量搜索获取相关候选文档
            print(f"🔍 使用向量搜索预筛选候选文档...")
            
            pre_filter_start = time.time()
            try:
                # 生成查询向量
                from service.core.rag.nlp.model import generate_embedding
                
                embed_start = time.time()
                query_vector = generate_embedding(query)
                embed_time = time.time() - embed_start
                
                # 直接使用 Collection 进行同步向量搜索
                search_params = {
                    "metric_type": "COSINE",
                    "params": {"ef": 32}  # 降低ef参数，提高速度
                }
                
                # 执行向量搜索
                vec_search_start = time.time()
                search_results = collection.search(
                    data=[query_vector],
                    anns_field="vector",
                    param=search_params,
                    limit=candidate_limit,
                    output_fields=["id", "content", "content_ltks", "doc_id", "doc_name", "category", "source", "metadata"]
                )
                vec_search_time = time.time() - vec_search_start
                
                # 提取搜索结果
                if search_results and len(search_results) > 0:
                    results = []
                    for hit in search_results[0]:
                        # 优先使用chunk_id作为唯一标识，如果没有则使用Milvus内部ID
                        chunk_id = hit.entity.get('chunk_id', '')
                        unique_id = chunk_id if chunk_id else str(hit.id)

                        result_dict = {
                            'id': unique_id,
                            'content': hit.entity.get('content', ''),
                            'content_ltks': hit.entity.get('content_ltks', ''),
                            'doc_id': hit.entity.get('doc_id', ''),
                            'doc_name': hit.entity.get('doc_name', ''),
                            'category': hit.entity.get('category', ''),
                            'source': hit.entity.get('source', ''),
                            'metadata': hit.entity.get('metadata', {})
                        }
                        results.append(result_dict)
                    
                    pre_filter_time = time.time() - pre_filter_start
                    print(f"✅ 向量预筛选获得 {len(results)} 个候选文档 (总耗时: {pre_filter_time:.3f}s, Embedding: {embed_time:.3f}s, 搜索: {vec_search_time:.3f}s)")
                else:
                    results = []
                    
            except Exception as e:
                print(f"⚠️ 向量预筛选失败，使用随机候选: {e}")
                import traceback
                traceback.print_exc()
                # 降级方案：随机选择
                results = collection.query(
                    expr="id >= 0",
                    output_fields=["id", "content", "content_ltks", "doc_id", "doc_name", "category", "source", "metadata"],
                    limit=candidate_limit
                )
            
            if not results:
                return []
            
            # 使用BM25算法进行文本搜索
            print(f"📊 使用BM25算法处理 {len(results)} 个候选文档")
            
            bm25_start = time.time()
            bm25_searcher = BM25Searcher(k1=1.2, b=0.75)
            
            # 执行BM25搜索，不使用阈值过滤，获取所有候选进行rerank
            scored_results = bm25_searcher.search_documents(
                query=query,
                documents=results,
                text_threshold=0.0  # 不进行阈值过滤，让rerank决定
            )
            bm25_time = time.time() - bm25_start
            
            # 处理BM25搜索结果
            text_results = []
            for result in scored_results[:top_k]:
                # 确保所有必需的字段都存在
                enhanced_result = result.copy()
                enhanced_result['chunk_id'] = result.get('metadata', {}).get('chunk_id', str(result.get('id', '')))
                
                text_results.append(enhanced_result)
            
            text_search_total_time = time.time() - text_search_start
            print(f"✅ BM25搜索完成，找到 {len(text_results)} 个匹配结果 (BM25计算耗时: {bm25_time:.3f}s, 总耗时: {text_search_total_time:.3f}s)")
            
            return text_results

        except Exception as e:
            print(f"❌ BM25文本搜索失败: {e}")
            return []

    def _merge_search_results(self, vector_results: List, text_results: List,
                            vector_weight: float, text_weight: float, top_k: int,
                            query: str, hybrid_threshold: float = None) -> List:
        """合并向量和文本搜索结果"""
        try:
            # 创建结果字典用于去重
            merged_dict = {}

            # 处理向量搜索结果，使用内容去重
            for i, result in enumerate(vector_results):
                chunk_id = getattr(result, 'id', f"vector_{i}")
                content = result.content
                
                # 使用内容作为去重键，避免相同内容的不同chunk_id
                content_key = content[:200] if len(content) > 200 else content  # 使用前200字符作为去重键
                
                # 如果内容已存在，保留得分更高的
                if content_key in merged_dict:
                    existing_score = merged_dict[content_key]['vector_score']
                    if result.score > existing_score:
                        merged_dict[content_key] = {
                            'result': result,
                            'vector_score': result.score,
                            'text_score': 0.0,
                            'hybrid_score': result.score * vector_weight,
                            'source': 'vector'
                        }
                else:
                    merged_dict[content_key] = {
                        'result': result,
                        'vector_score': result.score,
                        'text_score': 0.0,
                        'hybrid_score': result.score * vector_weight,
                        'source': 'vector'
                    }

            # 处理文本搜索结果，使用内容去重
            for text_result in text_results:
                text_content = text_result.get('content', '')
                text_id = text_result.get('id')
                
                # 使用内容作为去重键
                content_key = text_content[:200] if len(text_content) > 200 else text_content
                
                # 检查是否已存在相同内容
                if content_key in merged_dict:
                    # 如果已存在，更新文本得分（保留更高的得分）
                    existing_text_score = merged_dict[content_key]['text_score']
                    new_text_score = text_result.get('text_score', 0.0)
                    
                    if new_text_score > existing_text_score:
                        merged_item = merged_dict[content_key]
                        merged_item['text_score'] = new_text_score
                        merged_item['hybrid_score'] = (
                            merged_item['vector_score'] * vector_weight +
                            merged_item['text_score'] * text_weight
                        )
                        merged_item['source'] = 'hybrid'
                else:
                    # 如果不存在，添加新的文本结果
                    from services.milvus.models import SearchResult
                    pseudo_result = SearchResult(
                        id=text_id,
                        score=text_result.get('text_score', 0.0),
                        content=text_content,
                        doc_id=text_result.get('doc_id', ''),
                        doc_name=text_result.get('doc_name', ''),
                        category=text_result.get('category', ''),
                        source=text_result.get('source', ''),
                        metadata=text_result.get('metadata', {})
                    )

                    merged_dict[content_key] = {
                        'result': pseudo_result,
                        'vector_score': 0.0,
                        'text_score': text_result.get('text_score', 0.0),
                        'hybrid_score': text_result.get('text_score', 0.0) * text_weight,
                        'source': 'text'
                    }

            # 使用阿里 DashScope Rerank 模型进行智能重排
            print(f"🔄 使用 DashScope Rerank 模型重排: 合并 {len(merged_dict)} 个结果")
            
            try:
                # 准备重排数据
                rerank_candidates = []
                for item in merged_dict.values():
                    rerank_candidates.append({
                        'content': item['result'].content,
                        'item': item
                    })
                
                # 调用阿里 DashScope Rerank
                from service.core.rag.nlp.model import rerank_similarity
                texts = [candidate['content'] for candidate in rerank_candidates]
                rerank_scores, _ = rerank_similarity(query, texts)
                
                # 完全使用 DashScope Rerank 的结果
                for i, candidate in enumerate(rerank_candidates):
                    rerank_score = float(rerank_scores[i])
                    
                    # 直接使用 rerank 得分作为最终得分
                    candidate['item']['hybrid_score'] = rerank_score
                    candidate['item']['rerank_score'] = rerank_score
                
                # 按最终得分排序
                sorted_results = sorted(
                    [candidate['item'] for candidate in rerank_candidates],
                    key=lambda x: x['hybrid_score'],
                    reverse=True
                )
                
                print(f"✅ DashScope Rerank 完成，取前 {top_k} 个结果")
                
            except Exception as e:
                print(f"⚠️ DashScope Rerank 失败，使用简单重排: {e}")
                # 降级到简单重排
                sorted_results = sorted(
                    merged_dict.values(),
                    key=lambda x: x['hybrid_score'],
                    reverse=True
                )
                print(f"🔄 简单重排: 合并 {len(merged_dict)} 个结果，取前 {top_k} 个")

            # 更新原始结果的分数并返回
            final_results = []
            for item in sorted_results[:top_k]:
                result = item['result']
                # 更新分数信息
                result.score = item['hybrid_score']
                # 将额外信息存储到metadata中
                if not hasattr(result, 'metadata') or not result.metadata:
                    result.metadata = {}
                result.metadata.update({
                    'vector_score': item['vector_score'],
                    'text_score': item['text_score'],
                    'hybrid_score': item['hybrid_score'],
                    'source_type': item['source']
                })
                
                # 如果使用了 DashScope Rerank，添加 rerank 得分
                if 'rerank_score' in item:
                    result.metadata['rerank_score'] = item['rerank_score']
                final_results.append(result)

            return final_results

        except Exception as e:
            print(f"合并搜索结果失败: {e}")
            import traceback
            traceback.print_exc()
            # 如果合并失败，返回向量搜索结果
            return vector_results

    def get_user_documents(self, user_id: str, page: int = 1, page_size: int = 10) -> dict:
        try:
            db = default_manager.session_factory()
            try:
                # 计算偏移量
                offset = (page - 1) * page_size
                
                # 获取总数
                total = db.query(Document).filter(Document.user_id == user_id).count()
                
                # 获取分页数据
                documents = db.query(Document).filter(
                    Document.user_id == user_id
                ).order_by(
                    Document.created_at.desc()
                ).offset(offset).limit(page_size).all()
                
                # 转换为字典列表
                docs_list = [doc.to_dict() for doc in documents]
                
                return {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "documents": docs_list
                }
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"获取用户文档列表失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取用户文档列表失败: {str(e)}"
            )
    
    def get_document_by_id(self, document_id: str, user_id: str) -> Document:
        """根据ID获取文档（确保用户权限）"""
        try:
            db = default_manager.session_factory()
            try:
                document = db.query(Document).filter(
                    Document.document_id == document_id,
                    Document.user_id == user_id
                ).first()
                
                if not document:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="文档不存在或无权限访问"
                    )
                
                return document
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"获取文档失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取文档失败: {str(e)}"
            )
    
    def delete_document(self, document_id: str, user_id: str) -> dict:
        """
        删除文档（删除PG、Milvus和物理文件）
        采用最大努力删除策略，记录过程中的问题但不阻止删除
        """
        deletion_results = {
            'document_deleted': False,
            'milvus_deleted': False,
            'es_deleted': False,
            'file_deleted': False,
            'errors': []
        }
        
        try:
            db = default_manager.session_factory()
            try:
                # 获取文档信息
                document = db.query(Document).filter(
                    Document.document_id == document_id,
                    Document.user_id == user_id
                ).first()
                
                if not document:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="文档不存在或无权限删除"
                    )
  
                # 1. 尝试删除Milvus中的数据
                try:
                    from services.milvus.milvus_service import MilvusService
                    import os

                    collection_name = f"user_collection_{user_id}".replace("-", "_")
                    print(f"尝试删除Milvus集合 {collection_name} 中文档 {document.file_name} 的数据")

                    # 初始化Milvus服务
                    milvus_service = MilvusService(
                        host=os.getenv("MILVUS_HOST", "milvus-standalone"),
                        port=os.getenv("MILVUS_PORT", "19530")
                    )

                    # 连接Milvus
                    connected = milvus_service.connect_sync()
                    if connected:
                        # 删除指定文档名的所有向量数据
                        delete_expr = f'doc_name == "{document.file_name}"'
                        deleted_count = milvus_service.delete_data_sync(collection_name, delete_expr)

                        if deleted_count > 0:
                            deletion_results['milvus_deleted'] = True
                            print(f"✅ 成功从Milvus删除 {deleted_count} 条向量数据")
                        else:
                            deletion_results['milvus_deleted'] = True  # 没有数据也算成功
                            print(f"✅ Milvus中没有找到匹配的向量数据")
                    else:
                        deletion_results['errors'].append("Milvus连接失败，无法删除向量数据")
                        print("❌ Milvus连接失败")

                except Exception as milvus_error:
                    deletion_results['errors'].append(f"Milvus删除失败: {str(milvus_error)}")
                    print(f"删除Milvus数据失败: {milvus_error}")

                # 2. 尝试删除ES中的数据（使用智能删除策略）
                try:
                    from service.core.file_parse import get_es_connection
                    es_connection = get_es_connection()
                    
                    if es_connection.es_available:
                        # 使用新的智能删除方法
                        es_result = es_connection.delete_user_document_data(
                            file_name=document.file_name,
                            index_name=user_id
                        )
                        
                        # 分析删除结果
                        if es_result['strategy_used'] in ['index_not_exists', 'index_empty']:
                            # 索引不存在或为空，这实际上是正常的
                            deletion_results['es_deleted'] = True
                            deletion_results['errors'].append(f"ES状态: {es_result['strategy_used']}")
                        elif es_result['deleted_count'] > 0:
                            # 成功删除了文档
                            deletion_results['es_deleted'] = True
                        elif es_result['errors']:
                            # 有错误发生
                            deletion_results['es_deleted'] = False
                            deletion_results['errors'].extend(es_result['errors'])
                        else:
                            # 没有找到匹配的文档，但这不算错误
                            deletion_results['es_deleted'] = True
                            deletion_results['errors'].append("ES中未找到匹配文档")
                            
                        print(f"ES删除结果: {es_result}")
                    else:
                        deletion_results['errors'].append("ES连接不可用")
                        deletion_results['es_deleted'] = False
                        
                except Exception as es_error:
                    deletion_results['errors'].append(f"ES删除失败: {str(es_error)}")
                    deletion_results['es_deleted'] = False
                    print(f"删除ES数据失败: {es_error}")
                
                # 2. 尝试删除物理文件
                try:
                    if os.path.exists(document.file_path):
                        os.remove(document.file_path)
                        deletion_results['file_deleted'] = True
                    else:
                        deletion_results['errors'].append("物理文件不存在")
                except Exception as file_error:
                    deletion_results['errors'].append(f"物理文件删除失败: {str(file_error)}")
                    print(f"删除物理文件失败: {file_error}")
                
                # 3. 删除PG数据库记录（这是最重要的）
                db.delete(document)
                db.commit()
                deletion_results['document_deleted'] = True
                
                print(f"文档删除完成: {document_id}, 结果: {deletion_results}")
                return deletion_results
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"删除文档失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除文档失败: {str(e)}"
            )
    
    def process_document_to_es(self, file_path: str, file_name: str, user_id: str) -> int:
        """处理文档到ES（不涉及PG数据库）"""
        try:
            # 使用file_parse.py处理文档
            result = execute_insert_process(
                file_path=file_path,
                file_name=file_name,
                session_id=user_id,  # 使用用户ID作为ES索引名
                index_name=user_id   # 确保ES索引名是用户ID
            )
            
            # 返回处理结果
            return len(result) if result else 0
            
        except Exception as e:
            print(f"处理文档到ES失败: {e}")
            raise e
    
    def process_document(self, document_id: str, user_id: str) -> bool:
        """处理文档（解析并存入ES）"""
        try:
            db = default_manager.session_factory()
            try:
                # 获取文档信息
                document = db.query(Document).filter(
                    Document.document_id == document_id,
                    Document.user_id == user_id
                ).first()
                
                if not document:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="文档不存在或无权限访问"
                    )
                
                # 更新状态为处理中
                document.status = 'processing'
                document.updated_at = int(time.time())
                db.commit()
                
                try:
                    # 使用file_parse.py处理文档
                    result = execute_insert_process(
                        file_path=document.file_path,
                        file_name=document.file_name,
                        session_id=user_id,  # 使用用户ID作为ES索引名
                        index_name=user_id   # 确保ES索引名是用户ID
                    )
                    
                    # 更新状态为完成
                    document.status = 'completed'
                    document.chunk_count = len(result) if result else 0
                    document.updated_at = int(time.time())
                    db.commit()
                    
                    return len(result) if result else 0
                    
                except Exception as process_error:
                    # 处理失败，更新状态
                    document.status = 'failed'
                    document.error_message = str(process_error)
                    document.updated_at = int(time.time())
                    db.commit()
                    
                    raise process_error
                
            finally:
                db.close()

        except Exception as e:
            print(f"处理文档失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"处理文档失败: {str(e)}"
            )

  