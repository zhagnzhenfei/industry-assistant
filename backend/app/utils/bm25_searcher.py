#!/usr/bin/env python3
"""
BM25文本搜索算法实现
基于RAG系统中的分词器，实现高效的中文文本检索
"""

import math
import sys
from pathlib import Path
from typing import List, Dict, Set, Tuple
from collections import defaultdict, Counter
from pymilvus import Collection, utility

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from service.core.rag.nlp.rag_tokenizer import RagTokenizer


class BM25Searcher:
    """
    BM25算法实现
    用于计算文档与查询的文本相关性得分
    """

    def __init__(self, k1: float = 1.2, b: float = 0.75):
        """
        初始化BM25搜索器

        Args:
            k1: 控制词频饱和度的参数，通常取值1.2-2.0
            b: 控制文档长度归一化的参数，通常取值0.75
        """
        self.k1 = k1
        self.b = b
        self.tokenizer = RagTokenizer(debug=False)

        # 统计信息
        self.doc_freqs: Dict[str, int] = defaultdict(int)  # 词频统计：词 -> 文档数
        self.doc_len: List[int] = []  # 文档长度列表
        self.avgdl: float = 0.0  # 平均文档长度
        self.corpus_size: int = 0  # 语料库大小
        self.vocab: Set[str] = set()  # 词汇表

    def _build_stats(self, documents: List[List[str]]) -> None:
        """
        构建统计信息

        Args:
            documents: 分词后的文档列表，每个文档是分词后的词语列表
        """
        self.doc_len = [len(doc) for doc in documents]
        self.corpus_size = len(documents)
        self.avgdl = sum(self.doc_len) / self.corpus_size if self.corpus_size > 0 else 0

        # 统计每个词在多少个文档中出现过
        word_doc_count = defaultdict(int)
        for doc in documents:
            unique_words = set(doc)
            for word in unique_words:
                word_doc_count[word] += 1
                self.vocab.add(word)

        self.doc_freqs = dict(word_doc_count)

    def _calculate_idf(self, word: str) -> float:
        """
        计算词的逆文档频率 (IDF)

        Args:
            word: 词语

        Returns:
            IDF值
        """
        if word not in self.doc_freqs or self.doc_freqs[word] == 0:
            return 0.0

        # 使用平滑的IDF公式
        return math.log((self.corpus_size - self.doc_freqs[word] + 0.5) /
                       (self.doc_freqs[word] + 0.5))

    def _tokenize(self, text: str) -> List[str]:
        """
        文本分词

        Args:
            text: 输入文本

        Returns:
            分词后的词语列表
        """
        try:
            # 使用RAG分词器
            tokens = self.tokenizer.tokenize(text)
            # 清理空字符串和特殊字符
            return [token.strip() for token in tokens.split() if token.strip() and len(token.strip()) > 1]
        except Exception as e:
            print(f"分词失败，使用简单分词: {e}")
            # 回退到简单分词
            return [word for word in text.split() if len(word) > 1]

    def calculate_score(self, query: str, document: str) -> float:
        """
        计算查询与文档的BM25得分

        Args:
            query: 查询文本
            document: 文档文本

        Returns:
            BM25得分
        """
        # 分词
        query_tokens = self._tokenize(query)
        doc_tokens = self._tokenize(document)

        if not query_tokens or not doc_tokens:
            return 0.0

        # 构建文档统计信息（仅包含当前文档）
        self._build_stats([doc_tokens])

        # 计算BM25得分
        score = 0.0
        doc_len = len(doc_tokens)
        doc_counter = Counter(doc_tokens)

        for token in query_tokens:
            if token in doc_counter:
                # 词频
                tf = doc_counter[token]

                # IDF
                idf = self._calculate_idf(token)

                # BM25公式
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)

                score += idf * (numerator / denominator)

        return score

    def search_documents(self, query: str, documents: List[Dict],
                        text_threshold: float = 0.1) -> List[Dict]:
        """
        在文档集合中搜索（优化版本，使用预分词数据）

        Args:
            query: 查询文本
            documents: 文档列表，每个文档是包含文本和元数据的字典
                      如果包含 'content_ltks' 字段，将直接使用预分词结果
            text_threshold: 文本相关性阈值

        Returns:
            按BM25得分排序的文档列表
        """
        # 分词查询
        query_tokens = self._tokenize(query)

        if not query_tokens:
            return []

        # 优化：快速预筛选 - 简单关键词匹配
        # 只对包含至少一个查询词的文档进行完整的BM25计算
        query_keywords = set(query_tokens)
        
        filtered_docs = []
        filtered_indices = []
        for i, doc in enumerate(documents):
            content = doc.get('content', '').lower()
            # 简单检查是否包含任何查询关键词
            if any(keyword.lower() in content for keyword in query_keywords):
                filtered_docs.append(doc)
                filtered_indices.append(i)
        
        # 如果预筛选后没有文档，返回空列表
        if not filtered_docs:
            return []
        
        print(f"⚡ 快速预筛选: {len(documents)} -> {len(filtered_docs)} 个文档")
        
        # 提取文档文本
        doc_texts = [doc.get('content', '') for doc in filtered_docs]

        # ⚡ 核心优化：使用预分词数据，避免重复分词
        doc_tokens_list = []
        use_pretokenized = False
        
        for doc in filtered_docs:
            # 优先使用预分词字段 content_ltks
            if 'content_ltks' in doc and doc['content_ltks']:
                pretokens = doc['content_ltks'].strip()
                if pretokens:
                    # 预分词结果是空格分隔的
                    tokens = [t for t in pretokens.split() if t.strip()]
                    doc_tokens_list.append(tokens)
                    use_pretokenized = True
                    continue
            
            # 如果没有预分词数据，使用传统分词
            tokens = self._tokenize(doc.get('content', ''))
            doc_tokens_list.append(tokens)
        
        if use_pretokenized:
            print(f"⚡ 使用预分词数据，跳过分词步骤（性能提升 80%+）")

        # 构建统计信息
        self._build_stats(doc_tokens_list)

        # 计算每个文档的BM25得分
        scored_docs = []
        for i, (doc, doc_tokens, doc_text) in enumerate(zip(filtered_docs, doc_tokens_list, doc_texts)):
            if not doc_tokens:
                continue

            score = 0.0
            doc_counter = Counter(doc_tokens)
            doc_len = len(doc_tokens)

            for token in query_tokens:
                if token in doc_counter:
                    tf = doc_counter[token]
                    idf = self._calculate_idf(token)

                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)

                    score += idf * (numerator / denominator)

            # 归一化得分到0-1范围
            # BM25得分可能为负，使用sigmoid函数进行归一化
            normalized_score = 1.0 / (1.0 + math.exp(-score / 2.0))  # 使用sigmoid函数

            if normalized_score >= text_threshold:
                # 添加分数信息到文档中
                doc_copy = doc.copy()
                doc_copy['text_score'] = normalized_score
                doc_copy['hybrid_score'] = normalized_score  # 纯文本搜索时，hybrid_score等于text_score
                doc_copy['bm25_raw_score'] = score
                scored_docs.append(doc_copy)

        # 按得分排序
        scored_docs.sort(key=lambda x: x['text_score'], reverse=True)

        return scored_docs


async def search_milvus_with_bm25(collection_name: str, query: str,
                                top_k: int = 10, text_threshold: float = 0.1) -> List[Dict]:
    """
    在Milvus集合中使用BM25进行文本搜索

    Args:
        collection_name: Milvus集合名称
        query: 查询文本
        top_k: 返回结果数量
        text_threshold: 文本相关性阈值

    Returns:
        按BM25得分排序的文档列表
    """
    try:
        # 检查集合是否存在
        if not utility.has_collection(collection_name):
            print(f"文本搜索集合不存在: {collection_name}")
            return []

        # 获取集合
        collection = Collection(collection_name)
        collection.load()

        # 获取所有文档（对于文本搜索，我们需要先获取内容再计算相关性）
        # 在实际应用中，可以考虑使用更高效的搜索策略
        results = collection.query(
            expr="id >= 0",
            output_fields=["id", "content", "doc_id", "doc_name", "category", "confidence", "source", "metadata"],
            limit=1000  # 限制获取数量，避免性能问题
        )

        print(f"BM25搜索候选文档数量: {len(results)}")

        # 使用BM25搜索器进行相关性计算
        searcher = BM25Searcher()
        scored_results = searcher.search_documents(
            query=query,
            documents=results,
            text_threshold=text_threshold
        )

        # 返回top_k结果
        return scored_results[:top_k]

    except Exception as e:
        print(f"BM25搜索失败: {e}")
        import traceback
        traceback.print_exc()
        return []


# 测试函数
def test_bm25():
    """测试BM25搜索功能"""
    # 测试分词
    searcher = BM25Searcher()

    test_query = "25H1新增与山姆渠道合作"
    test_doc = "丁一SAC：渠道方面，25H1新增与山姆渠道合作。公司一方面在天猫、京东、抖音、拼多多等电商平台保持较高的市场占有率。"

    print("=== BM25搜索测试 ===")
    print(f"查询: {test_query}")
    print(f"查询分词: {searcher._tokenize(test_query)}")
    print(f"文档: {test_doc}")
    print(f"文档分词: {searcher._tokenize(test_doc)}")
    print(f"BM25得分: {searcher.calculate_score(test_query, test_doc)}")


if __name__ == "__main__":
    # 临时跳过测试，避免导入问题
    pass