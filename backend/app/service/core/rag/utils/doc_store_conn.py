#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

from abc import ABC, abstractmethod
from dataclasses import dataclass
import numpy as np

DEFAULT_MATCH_VECTOR_TOPN = 10
DEFAULT_MATCH_SPARSE_TOPN = 10
VEC = list | np.ndarray


@dataclass
class SparseVector:
    """
    稀疏向量表示
    用于高效存储和计算只有少量非零元素的向量
    适用于文本检索中的TF-IDF等表示方法
    """
    indices: list[int]
    values: list[float] | list[int] | None = None

    def __post_init__(self):
        """
        初始化后验证索引和值的长度匹配
        """
        assert (self.values is None) or (len(self.indices) == len(self.values))

    def to_dict_old(self):
        """
        将稀疏向量转换为旧格式的字典
        兼容旧版API
        """
        d = {"indices": self.indices}
        if self.values is not None:
            d["values"] = self.values
        return d

    def to_dict(self):
        """
        将稀疏向量转换为字典格式
        索引作为键，值作为值
        用于序列化和存储
        """
        if self.values is None:
            raise ValueError("SparseVector.values is None")
        result = {}
        for i, v in zip(self.indices, self.values):
            result[str(i)] = v
        return result

    @staticmethod
    def from_dict(d):
        """
        从字典创建稀疏向量
        用于反序列化
        """
        return SparseVector(d["indices"], d.get("values"))

    def __str__(self):
        """
        字符串表示，用于调试
        """
        return f"SparseVector(indices={self.indices}{'' if self.values is None else f', values={self.values}'})"

    def __repr__(self):
        """
        对象表示，用于调试
        """
        return str(self)


class MatchTextExpr(ABC):
    """
    文本匹配表达式
    用于全文检索，支持在多字段上进行文本查询
    可设置匹配的字段、文本、返回结果数量和额外参数
    """
    def __init__(
        self,
        fields: list[str],
        matching_text: str,
        topn: int,
        extra_options: dict = dict(),
    ):
        self.fields = fields
        self.matching_text = matching_text
        self.topn = topn
        self.extra_options = extra_options


class MatchDenseExpr(ABC):
    """
    密集向量匹配表达式
    用于向量相似度搜索，支持不同距离计算方式
    适用于嵌入向量的相似度检索
    """
    def __init__(
        self,
        vector_column_name: str,
        embedding_data: VEC,
        embedding_data_type: str,
        distance_type: str,
        topn: int = DEFAULT_MATCH_VECTOR_TOPN,
        extra_options: dict = dict(),
    ):
        self.vector_column_name = vector_column_name
        self.embedding_data = embedding_data
        self.embedding_data_type = embedding_data_type
        self.distance_type = distance_type
        self.topn = topn
        self.extra_options = extra_options


class MatchSparseExpr(ABC):
    """
    稀疏向量匹配表达式
    用于稀疏向量相似度搜索
    适用于TF-IDF等稀疏表示的相似度检索
    """
    def __init__(
        self,
        vector_column_name: str,
        sparse_data: SparseVector | dict,
        distance_type: str,
        topn: int,
        opt_params: dict | None = None,
    ):
        self.vector_column_name = vector_column_name
        self.sparse_data = sparse_data
        self.distance_type = distance_type
        self.topn = topn
        self.opt_params = opt_params


class MatchTensorExpr(ABC):
    """
    张量匹配表达式
    用于张量计算的相似度搜索
    支持高维数据结构的匹配
    """
    def __init__(
        self,
        column_name: str,
        query_data: VEC,
        query_data_type: str,
        topn: int,
        extra_option: dict | None = None,
    ):
        self.column_name = column_name
        self.query_data = query_data
        self.query_data_type = query_data_type
        self.topn = topn
        self.extra_option = extra_option


class FusionExpr(ABC):
    """
    融合表达式
    用于组合多种匹配方式的结果
    支持不同的融合方法和参数
    """
    def __init__(self, method: str, topn: int, fusion_params: dict | None = None):
        self.method = method
        self.topn = topn
        self.fusion_params = fusion_params


MatchExpr = MatchTextExpr | MatchDenseExpr | MatchSparseExpr | MatchTensorExpr | FusionExpr

class OrderByExpr(ABC):
    """
    排序表达式
    用于指定搜索结果的排序方式
    支持多字段的升序和降序排序
    """
    def __init__(self):
        self.fields = list()
    def asc(self, field: str):
        """
        添加升序排序字段
        """
        self.fields.append((field, 0))
        return self
    def desc(self, field: str):
        """
        添加降序排序字段
        """
        self.fields.append((field, 1))
        return self
    def fields(self):
        """
        获取所有排序字段
        """
        return self.fields

class DocStoreConnection(ABC):
    """
    文档存储连接抽象基类
    定义了文档存储的通用接口
    支持各种数据库操作、检索和管理功能
    """

    @abstractmethod
    def dbType(self) -> str:
        """
        返回数据库类型
        用于标识使用的存储系统
        """
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def health(self) -> dict:
        """
        返回数据库健康状态
        用于监控和诊断
        """
        raise NotImplementedError("Not implemented")

    """
    Table operations
    """

    @abstractmethod
    def createIdx(self, indexName: str, knowledgebaseId: str, vectorSize: int):
        """
        创建索引
        为知识库创建新的索引，指定向量维度
        
        参数:
            indexName: 索引名称
            knowledgebaseId: 知识库ID
            vectorSize: 向量维度大小
        """
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def deleteIdx(self, indexName: str, knowledgebaseId: str):
        """
        删除索引
        移除指定的索引
        
        参数:
            indexName: 索引名称
            knowledgebaseId: 知识库ID
        """
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def indexExist(self, indexName: str, knowledgebaseId: str) -> bool:
        """
        检查索引是否存在
        验证指定索引是否已创建
        
        参数:
            indexName: 索引名称
            knowledgebaseId: 知识库ID
            
        返回:
            布尔值表示索引是否存在
        """
        raise NotImplementedError("Not implemented")

    """
    CRUD operations
    """

    @abstractmethod
    def search(
        self, selectFields: list[str],
            highlightFields: list[str],
            condition: dict,
            matchExprs: list[MatchExpr],
            orderBy: OrderByExpr,
            offset: int,
            limit: int,
            indexNames: str|list[str],
            knowledgebaseIds: list[str],
            aggFields: list[str] = [],
            rank_feature: dict | None = None
    ):
        """
        搜索文档
        支持多种匹配表达式和条件过滤的文档搜索
        
        参数:
            selectFields: 要返回的字段列表
            highlightFields: 要高亮显示的字段列表
            condition: 过滤条件
            matchExprs: 匹配表达式列表
            orderBy: 排序表达式
            offset: 分页偏移量
            limit: 返回结果数量限制
            indexNames: 索引名称或名称列表
            knowledgebaseIds: 知识库ID列表
            aggFields: 聚合字段列表
            rank_feature: 排序特征
        """
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def get(self, chunkId: str, indexName: str, knowledgebaseIds: list[str]) -> dict | None:
        """
        获取单个文档
        通过ID检索特定的文档块
        
        参数:
            chunkId: 文档块ID
            indexName: 索引名称
            knowledgebaseIds: 知识库ID列表
            
        返回:
            文档内容或None
        """
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def insert(self, rows: list[dict], indexName: str, knowledgebaseId: str = None) -> list[str]:
        """
        插入文档
        批量添加或更新文档
        
        参数:
            rows: 文档列表
            indexName: 索引名称
            knowledgebaseId: 知识库ID
            
        返回:
            插入的文档ID列表
        """
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def update(self, condition: dict, newValue: dict, indexName: str, knowledgebaseId: str) -> bool:
        """
        更新文档
        根据条件更新匹配的文档
        
        参数:
            condition: 匹配条件
            newValue: 新值
            indexName: 索引名称
            knowledgebaseId: 知识库ID
            
        返回:
            更新是否成功
        """
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def delete(self, condition: dict, indexName: str, knowledgebaseId: str) -> int:
        """
        删除文档
        根据条件删除匹配的文档
        
        参数:
            condition: 匹配条件
            indexName: 索引名称
            knowledgebaseId: 知识库ID
            
        返回:
            删除的文档数量
        """
        raise NotImplementedError("Not implemented")

    """
    Helper functions for search result
    """

    @abstractmethod
    def getTotal(self, res):
        """
        获取搜索结果总数
        返回匹配的文档总数
        """
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def getChunkIds(self, res):
        """
        获取搜索结果的文档ID
        返回匹配文档的ID列表
        """
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def getFields(self, res, fields: list[str]) -> dict[str, dict]:
        """
        获取搜索结果的指定字段
        从搜索结果中提取特定字段的值
        """
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def getHighlight(self, res, keywords: list[str], fieldnm: str):
        """
        获取高亮信息
        返回搜索结果中的高亮片段
        """
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def getAggregation(self, res, fieldnm: str):
        """
        获取聚合结果
        返回搜索结果的聚合统计
        """
        raise NotImplementedError("Not implemented")

    """
    SQL
    """
    @abstractmethod
    def sql(sql: str, fetch_size: int, format: str):
        """
        执行SQL查询
        运行文本到SQL生成的查询语句
        
        参数:
            sql: SQL查询语句
            fetch_size: 获取的结果数量
            format: 结果格式
        """
        raise NotImplementedError("Not implemented")
