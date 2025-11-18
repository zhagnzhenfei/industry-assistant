import xxhash
import datetime
from service.core.rag.app.naive import chunk
from service.core.rag.utils.milvus_conn import MilvusConnection
from service.core.rag.nlp.model import generate_embedding
from service.core.rag.nlp.search_v2 import Dealer

def dummy(prog=None, msg=""):
    pass

def parse(file_path, binary=None, from_page=0, to_page=100000, 
          lang="Chinese", callback=dummy, **kwargs):
    """
    使用自定义的文档解析器解析文件
    
    Args:
        file_path: 文件路径
        binary: 二进制数据（可选）
        from_page: 起始页码（默认0）
        to_page: 结束页码（默认100000）
        lang: 语言（默认"Chinese"）
        callback: 回调函数，用于报告进度（默认dummy函数）
        **kwargs: 额外的参数，可包括：
            - parser_config: 解析器配置字典，如chunk_token_num、delimiter、layout_recognize等
            - section_only: 是否只返回分段不做进一步处理
    
    Returns:
        解析后的文档块列表
    """
    # 透传所有参数给chunk函数
    result = chunk(
        file_path,
        binary=binary,
        from_page=from_page,
        to_page=to_page,
        lang=lang,
        callback=callback,
        **kwargs
    )
    return result


def process_item(item, file_name, session_id):
    """
    处理单条数据
    """
    try:
        # 生成 chunk_id
        chunck_id = xxhash.xxh64((item["content_with_weight"] + session_id).encode("utf-8")).hexdigest()

        # 构建数据字典
        d = {
            "id": chunck_id,
            "content_ltks": item["content_ltks"],
            "content_with_weight": item["content_with_weight"],
            "content_sm_ltks": item["content_sm_ltks"],
            "important_kwd": [],
            "important_tks": [],
            "question_kwd": [],
            "question_tks": [],
            "create_time": str(datetime.datetime.now()).replace("T", " ")[:19],
            "create_timestamp_flt": datetime.datetime.now().timestamp()
        }



        d["kb_id"] = session_id
        d["docnm_kwd"] = item["docnm_kwd"]
        d["title_tks"] = item["title_tks"]
        d["doc_id"] = xxhash.xxh64(file_name.encode("utf-8")).hexdigest()
        d["docnm"] = file_name
        
        v = generate_embedding(item["content_with_weight"])
            
        # 将嵌入向量存储到字典中
        d["q_%d_vec" % len(v)] = v

        return d

    except Exception as e:
        print(f"process_item error: {e}")
        return None

def execute_insert_process(file_path, file_name, session_id, binary=None, from_page=0, to_page=100000,
                          lang="Chinese", callback=dummy, **kwargs):
    """
    执行文档处理和插入 Milvus 的函数

    Args:
        file_path: 文件路径
        file_name: 文件名称
        session_id: 会话ID，用于索引名称
        binary: 二进制数据（可选）
        from_page: 起始页码（默认0）
        to_page: 结束页码（默认100000）
        lang: 语言（默认"Chinese"）
        callback: 回调函数，用于报告进度（默认dummy函数）
        **kwargs: 额外的参数，可包括：
            - parser_config: 解析器配置字典
            - section_only: 是否只返回分段不做进一步处理
            - index_name: 自定义索引名称，如果提供则替代session_id
    """
    # 透传参数到parse函数
    documents = parse(
        file_path,
        binary=binary,
        from_page=from_page,
        to_page=to_page,
        lang=lang,
        callback=callback,
        **kwargs
    )
    
    # 检查parse函数的返回值
    if not documents:
        print(f"文档解析失败或返回空结果: {file_name}")
        return []
    
    if not hasattr(documents, '__iter__'):
        print(f"文档解析返回非可迭代对象: {type(documents)}")
        return []
    
    result = []
    processed_count = 0
    
    try:
        for item in documents:
            if item is None:
                print("跳过空的文档项")
                continue
                
            processed_item = process_item(item, file_name, session_id)
            if processed_item is not None:
                result.append(processed_item)
                processed_count += 1
            else:
                print("process_item返回None，跳过此项")
        
        print(f"文档处理完成: 总计{len(documents)}项，成功处理{processed_count}项")
        
    except Exception as e:
        print(f"文档处理过程中出错: {e}")
        return []
    
    # 只有在有有效结果时才尝试插入Milvus
    if result:
        try:
            # 创建 MilvusConnection 的实例
            milvus_connection = MilvusConnection()
            # 通过实例调用 insert 方法，允许自定义索引名称
            index_name = kwargs.get("index_name", session_id)
            insert_errors = milvus_connection.insert(rows=result, indexName=index_name, knowledgebaseId=session_id)

            if insert_errors:
                print(f"Milvus插入部分失败: {insert_errors}")
            else:
                print(f"Milvus插入成功: {len(result)}个文档块")

        except Exception as e:
            print(f"Milvus插入失败: {e}")
            # Milvus插入失败不影响返回结果，因为数据已经处理成功
    else:
        print("没有有效的文档数据可插入Milvus")
    
    # 返回处理结果
    return result


# 创建全局Milvus连接实例用于检索
_milvus_connection = None

def get_milvus_connection():
    """获取或创建Milvus连接实例"""
    global _milvus_connection
    if _milvus_connection is None:
        _milvus_connection = MilvusConnection()
    return _milvus_connection

def simple_search(query_text, tenant_id, kb_ids, page=1, page_size=10, 
                 similarity_threshold=0.2, doc_ids=None, highlight=False,
                 rerank_model=None, vector_similarity_weight=0.7):
    """
    简化版的文档检索函数
    参考retrieval.py中的检索逻辑

    Args:
        query_text: 查询文本
        tenant_id: 租户ID或ID列表
        kb_ids: 知识库ID列表
        page: 页码，从1开始（默认1）
        page_size: 每页结果数量（默认10）
        similarity_threshold: 相似度阈值（默认0.2）
        doc_ids: 可选的文档ID限制（默认None）
        highlight: 是否高亮匹配内容（默认False）
        rerank_model: 重排模型，用于对检索结果进行重排序（默认None）
        vector_similarity_weight: 向量相似度权重(0.7)，用于混合排序

    Returns:
        包含检索结果的字典，包括总数和结果列表
    """
    # 获取Milvus连接实例
    milvus_connection = get_milvus_connection()

    # 创建Dealer实例
    dealer = Dealer(dataStore=milvus_connection)
    
    # 执行检索 - 参考retrieval.py的调用方式
    results = dealer.retrieval(
        question=query_text,
        embd_mdl=None,  # 使用默认的嵌入模型
        tenant_ids=tenant_id,
        kb_ids=None,  # 参考retrieval.py，设置为None
        page=page,
        page_size=page_size,
        similarity_threshold=similarity_threshold,
        vector_similarity_weight=vector_similarity_weight,
        doc_ids=doc_ids,
        highlight=highlight,
        rerank_mdl=rerank_model
    )
    
    return results


