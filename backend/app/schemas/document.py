from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class DocumentUploadResponse(BaseModel):
    """文档上传响应模型"""
    status: str = Field(..., description="上传状态")
    message: str = Field(..., description="响应消息")
    document_id: str = Field(..., description="文档ID")
    file_name: str = Field(..., description="文件名")


class DocumentInfo(BaseModel):
    """文档信息模型"""
    document_id: str = Field(..., description="文档ID")
    file_name: str = Field(..., description="文件名")
    file_size: Optional[int] = Field(None, description="文件大小")
    file_type: Optional[str] = Field(None, description="文件类型")
    status: str = Field(..., description="处理状态")
    chunk_count: int = Field(0, description="分块数量")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: int = Field(..., description="创建时间戳")
    updated_at: int = Field(..., description="更新时间戳")


class DocumentListResponse(BaseModel):
    """文档列表响应模型"""
    total: int = Field(..., description="总文档数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    documents: List[DocumentInfo] = Field(..., description="文档列表")


class DocumentDeleteRequest(BaseModel):
    """删除文档请求模型"""
    document_ids: List[str] = Field(..., description="要删除的文档ID列表")


class DocumentDeleteResponse(BaseModel):
    """删除文档响应模型"""
    status: str = Field(..., description="删除状态")
    message: str = Field(..., description="响应消息")
    deleted_count: int = Field(..., description="成功删除的文档数量")


class DocumentSearchRequest(BaseModel):
    """文档搜索请求模型"""
    query: str = Field(..., description="搜索查询")
    page: int = Field(1, description="页码，从1开始")
    page_size: int = Field(10, description="每页结果数量")
    similarity_threshold: float = Field(0.2, description="相似度阈值")


class DocumentSearchResponse(BaseModel):
    """文档搜索响应模型"""
    total: int = Field(..., description="搜索结果总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    results: List[dict] = Field(..., description="搜索结果列表")


class MilvusSearchRequest(BaseModel):
    """Milvus向量搜索请求模型"""
    query: str = Field(..., description="搜索查询文本")
    top_k: int = Field(10, description="返回结果数量")
    similarity_threshold: float = Field(0.2, description="相似度阈值")
    category: Optional[str] = Field(None, description="文档类别过滤")
    confidence_min: Optional[float] = Field(None, description="最小置信度过滤")
    # 混合检索参数
    enable_hybrid_search: bool = Field(False, description="是否启用混合检索（向量+文本）")
    vector_weight: float = Field(0.5, description="向量检索权重，范围0-1，文本权重自动计算为1-vector_weight", ge=0, le=1)
    text_threshold: float = Field(0.3, description="文本相关性阈值，范围0-1", ge=0, le=1)

    

class MilvusSearchResult(BaseModel):
    """Milvus搜索结果项模型"""
    id: int = Field(..., description="向量ID")
    score: float = Field(..., description="相似度分数")
    content: str = Field(..., description="文档内容")
    doc_id: str = Field(..., description="文档ID")
    doc_name: str = Field(..., description="文档名称")
    category: Optional[str] = Field(None, description="文档类别")
    confidence: float = Field(..., description="置信度")
    source: Optional[str] = Field(None, description="来源")
    chunk_id: Optional[str] = Field(None, description="分块ID")
    # 混合检索字段
    text_score: Optional[float] = Field(None, description="文本检索分数")
    hybrid_score: Optional[float] = Field(None, description="混合检索综合分数")


class MilvusSearchResponse(BaseModel):
    """Milvus向量搜索响应模型"""
    query: str = Field(..., description="搜索查询")
    total: int = Field(..., description="结果数量")
    results: List[MilvusSearchResult] = Field(..., description="搜索结果列表")
    search_time: float = Field(..., description="搜索耗时(秒)")
    # 混合检索元信息
    search_type: str = Field("vector", description="搜索类型：vector/text/hybrid")
    vector_results_count: int = Field(0, description="向量检索结果数量")
    text_results_count: int = Field(0, description="文本检索结果数量")


class MilvusQueryRequest(BaseModel):
    """Milvus条件查询请求模型"""
    filter_expr: str = Field(..., description="过滤表达式，例如: doc_id == 'xxx' AND confidence > 0.5")
    output_fields: Optional[List[str]] = Field(None, description="输出字段列表")
    limit: int = Field(100, description="返回结果数量限制")


class MilvusQueryResponse(BaseModel):
    """Milvus条件查询响应模型"""
    filter_expr: str = Field(..., description="查询条件")
    total: int = Field(..., description="结果数量")
    results: List[dict] = Field(..., description="查询结果列表")
    query_time: float = Field(..., description="查询耗时(秒)")