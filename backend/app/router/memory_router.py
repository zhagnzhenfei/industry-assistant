"""
记忆管理API路由
"""
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from services.memory.memory_factory import get_memory_service
from services.memory.custom_memory_service import CustomMemoryService
from service.auth_service import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])


# Pydantic模型
class AddMemoryRequest(BaseModel):
    """添加记忆请求"""
    content: str = Field(..., description="记忆内容", min_length=1)
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")
    infer: bool = Field(default=True, description="是否使用LLM智能抽取")


class AddMemoryResponse(BaseModel):
    """添加记忆响应"""
    success: bool
    message: str
    result: Optional[Dict[str, Any]] = None


class SearchMemoriesRequest(BaseModel):
    """搜索记忆请求"""
    query: str = Field(..., description="搜索查询")
    limit: int = Field(default=10, ge=1, le=100, description="返回数量")


class MemoryItem(BaseModel):
    """记忆项"""
    id: Optional[str] = None
    memory: Any
    metadata: Optional[Dict[str, Any]] = None
    score: Optional[float] = None


class SearchMemoriesResponse(BaseModel):
    """搜索记忆响应"""
    success: bool
    memories: List[MemoryItem]
    total: int


class ContextResponse(BaseModel):
    """上下文响应"""
    success: bool
    context: str
    memory_count: int


class DeleteMemoryResponse(BaseModel):
    """删除记忆响应"""
    success: bool
    message: str


@router.post("/add", response_model=AddMemoryResponse, status_code=status.HTTP_201_CREATED)
async def add_memory(
    request: AddMemoryRequest,
    current_user: dict = Depends(get_current_user),
    memory_service: Optional[CustomMemoryService] = Depends(get_memory_service)
):
    """
    添加记忆
    
    Args:
        request: 添加记忆请求
        current_user: 当前用户
        memory_service: 记忆服务
        
    Returns:
        添加结果
    """
    if not memory_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="记忆服务未启用或不可用"
        )
    
    try:
        user_id = current_user.user_id if hasattr(current_user, 'user_id') else str(current_user.get('user_id'))
        
        result = await memory_service.add_memory(
            user_id=user_id,
            content=request.content,
            metadata=request.metadata,
            infer=request.infer
        )
        
        if result.get("success"):
            return AddMemoryResponse(
                success=True,
                message="记忆添加成功",
                result=result.get("result")
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"添加记忆失败: {result.get('error')}"
            )
            
    except Exception as e:
        logger.error(f"添加记忆API错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加记忆失败: {str(e)}"
        )


@router.post("/search", response_model=SearchMemoriesResponse)
async def search_memories(
    request: SearchMemoriesRequest,
    current_user: dict = Depends(get_current_user),
    memory_service: Optional[CustomMemoryService] = Depends(get_memory_service)
):
    """
    搜索记忆
    
    Args:
        request: 搜索请求
        current_user: 当前用户
        memory_service: 记忆服务
        
    Returns:
        搜索结果
    """
    if not memory_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="记忆服务未启用或不可用"
        )
    
    try:
        user_id = current_user.user_id if hasattr(current_user, 'user_id') else str(current_user.get('user_id'))
        
        result = await memory_service.search_memories(
            user_id=user_id,
            query=request.query,
            limit=request.limit
        )
        
        # result 是字典，包含 success, memories, total
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "搜索记忆失败")
            )
        
        memories_list = result.get("memories", [])
        
        # 转换为MemoryItem
        memory_items = []
        for mem in memories_list:
            memory_items.append(MemoryItem(
                id=mem.get("id"),
                memory=mem.get("memory"),
                metadata=mem.get("metadata"),
                score=mem.get("score")
            ))
        
        return SearchMemoriesResponse(
            success=True,
            memories=memory_items,
            total=result.get("total", len(memory_items))
        )
            
    except Exception as e:
        logger.error(f"搜索记忆API错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索记忆失败: {str(e)}"
        )


@router.get("/list", response_model=SearchMemoriesResponse)
async def list_memories(
    limit: int = Query(default=20, ge=1, le=100, description="返回数量"),
    current_user: dict = Depends(get_current_user),
    memory_service: Optional[CustomMemoryService] = Depends(get_memory_service)
):
    """
    获取用户所有记忆
    
    Args:
        limit: 返回数量
        current_user: 当前用户
        memory_service: 记忆服务
        
    Returns:
        记忆列表
    """
    if not memory_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="记忆服务未启用或不可用"
        )
    
    try:
        user_id = current_user.user_id if hasattr(current_user, 'user_id') else str(current_user.get('user_id'))
        
        memories = await memory_service.get_all_memories(
            user_id=user_id,
            limit=limit
        )
        
        # 转换为MemoryItem
        memory_items = []
        for mem in memories:
            memory_items.append(MemoryItem(
                id=mem.get("id"),
                memory=mem.get("memory"),
                metadata=mem.get("metadata")
            ))
        
        return SearchMemoriesResponse(
            success=True,
            memories=memory_items,
            total=len(memory_items)
        )
            
    except Exception as e:
        logger.error(f"获取记忆列表API错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取记忆列表失败: {str(e)}"
        )


@router.get("/context", response_model=ContextResponse)
async def get_context(
    query: Optional[str] = Query(default=None, description="可选的查询，用于获取相关上下文"),
    limit: int = Query(default=20, ge=1, le=100, description="上下文记忆数量"),
    current_user: dict = Depends(get_current_user),
    memory_service: Optional[CustomMemoryService] = Depends(get_memory_service)
):
    """
    获取用户上下文（用于AI对话）
    
    Args:
        query: 可选查询
        limit: 数量限制
        current_user: 当前用户
        memory_service: 记忆服务
        
    Returns:
        用户上下文
    """
    if not memory_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="记忆服务未启用或不可用"
        )
    
    try:
        user_id = current_user.user_id if hasattr(current_user, 'user_id') else str(current_user.get('user_id'))
        
        context = await memory_service.get_user_context(
            user_id=user_id,
            query=query,
            limit=limit
        )
        
        # 计算记忆数量
        memory_count = len(context.split('\n')) if context else 0
        
        return ContextResponse(
            success=True,
            context=context,
            memory_count=memory_count
        )
            
    except Exception as e:
        logger.error(f"获取用户上下文API错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户上下文失败: {str(e)}"
        )


@router.delete("/memories/{memory_id}", response_model=DeleteMemoryResponse)
async def delete_memory(
    memory_id: str,
    current_user: dict = Depends(get_current_user),
    memory_service: Optional[CustomMemoryService] = Depends(get_memory_service)
):
    """
    删除指定记忆
    
    Args:
        memory_id: 记忆ID
        current_user: 当前用户
        memory_service: 记忆服务
        
    Returns:
        删除结果
    """
    if not memory_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="记忆服务未启用或不可用"
        )
    
    try:
        user_id = current_user.user_id if hasattr(current_user, 'user_id') else str(current_user.get('user_id'))
        
        result = await memory_service.delete_memory(
            memory_id=memory_id,
            user_id=user_id
        )
        
        if result.get("success"):
            return DeleteMemoryResponse(
                success=True,
                message="记忆删除成功"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除记忆失败: {result.get('error')}"
            )
            
    except Exception as e:
        logger.error(f"删除记忆API错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除记忆失败: {str(e)}"
        )


@router.get("/health")
async def health_check(
    memory_service: Optional[CustomMemoryService] = Depends(get_memory_service)
):
    """
    健康检查
    
    Returns:
        服务状态
    """
    if not memory_service:
        return {
            "status": "disabled",
            "message": "记忆服务未启用"
        }
    
    return {
        "status": "healthy",
        "message": "记忆服务正常运行"
    }

