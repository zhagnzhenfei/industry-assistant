from typing import Optional
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND
import uuid
import time

from service.assistant_service import AssistantService
from service.mcp_service_manager import MCPServiceManager
from service.auth_service import get_current_user
from models import User
from schemas.assistant import (
    AssistantCreateRequest,
    AssistantUpdateRequest,
    AssistantResponse,
    AssistantListResponse,
    AssistantDeleteResponse,
    AssistantDetailResponse
)

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由实例
router = APIRouter(prefix="/assistants", tags=["assistants"])

# 获取智能体服务实例
def get_assistant_service():
    return AssistantService()

# 获取MCP服务管理器实例
def get_mcp_service_manager():
    return MCPServiceManager()


@router.post("", status_code=HTTP_201_CREATED, response_model=AssistantResponse)
async def create_assistant(
    request: AssistantCreateRequest,
    current_user: User = Depends(get_current_user),
    assistant_service: AssistantService = Depends(get_assistant_service)
):
    """
    创建新的智能体
    
    Args:
        request: 智能体创建请求
        current_user: 当前认证用户
        assistant_service: 智能体服务
        
    Returns:
        创建的智能体信息
    """
    logger.info(f"用户 {current_user.user_id} 开始创建智能体: name={request.name}")
    try:
        # 创建智能体
        result = await assistant_service.create_assistant(
            user_id=current_user.user_id,
            name=request.name,
            prompt=request.prompt,
            description=request.description,
            enable_knowledge_base=request.enable_knowledge_base,
            knowledge_base=request.knowledge_base,
            mcp_services=request.mcp_services
        )
        
        logger.info(f"智能体创建成功: assistant_id={result['assistant_id']}")
        return AssistantResponse(**result)
        
    except Exception as e:
        logger.error(f"创建智能体失败: user_id={current_user.user_id}, error={str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建智能体失败: {str(e)}"
        )


@router.get("", status_code=HTTP_200_OK, response_model=AssistantListResponse)
async def get_user_assistants(
    page: int = Query(1, description="页码", ge=1),
    page_size: int = Query(10, description="每页数量", ge=1, le=100),
    search: Optional[str] = Query(None, description="搜索关键词，支持智能体名称和描述的模糊匹配"),
    current_user: User = Depends(get_current_user),
    assistant_service: AssistantService = Depends(get_assistant_service)
):
    """
    获取当前用户的智能体列表
    
    Args:
        page: 页码，从1开始
        page_size: 每页数量
        search: 搜索关键词，可选
        current_user: 当前认证用户
        assistant_service: 智能体服务
        
    Returns:
        智能体列表响应
    """
    try:
        result = assistant_service.get_user_assistants(
            user_id=current_user.user_id,
            page=page,
            page_size=page_size,
            search=search
        )
        
        return AssistantListResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取智能体列表失败: {str(e)}"
        )


@router.get("/{assistant_id}", status_code=HTTP_200_OK, response_model=AssistantDetailResponse)
async def get_assistant_detail(
    assistant_id: str,
    current_user: User = Depends(get_current_user),
    assistant_service: AssistantService = Depends(get_assistant_service)
):
    """
    获取智能体详情
    
    Args:
        assistant_id: 智能体ID
        current_user: 当前认证用户
        assistant_service: 智能体服务
        
    Returns:
        智能体详细信息
    """
    try:
        result = assistant_service.get_assistant_detail(assistant_id, current_user.user_id)
        
        if not result:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail="智能体不存在或无权限访问"
            )
        
        return AssistantDetailResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取智能体详情失败: {str(e)}"
        )


@router.put("/{assistant_id}", status_code=HTTP_200_OK, response_model=AssistantResponse)
async def update_assistant(
    assistant_id: str,
    request: AssistantUpdateRequest,
    current_user: User = Depends(get_current_user),
    assistant_service: AssistantService = Depends(get_assistant_service)
):
    """
    更新智能体信息
    
    Args:
        assistant_id: 智能体ID
        request: 更新请求
        current_user: 当前认证用户
        assistant_service: 智能体服务
        
    Returns:
        更新后的智能体信息
    """
    try:
        # 更新智能体
        result = await assistant_service.update_assistant(
            assistant_id=assistant_id,
            user_id=current_user.user_id,
            name=request.name,
            prompt=request.prompt,
            description=request.description,
            is_active=request.is_active,
            enable_knowledge_base=request.enable_knowledge_base,
            knowledge_base=request.knowledge_base,
            mcp_services=request.mcp_services
        )
        
        return AssistantResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新智能体失败: {str(e)}"
        )


@router.delete("/{assistant_id}", status_code=HTTP_200_OK, response_model=AssistantDeleteResponse)
async def delete_assistant(
    assistant_id: str,
    current_user: User = Depends(get_current_user),
    assistant_service: AssistantService = Depends(get_assistant_service)
):
    """
    删除智能体
    
    Args:
        assistant_id: 智能体ID
        current_user: 当前认证用户
        assistant_service: 智能体服务
        
    Returns:
        删除结果
    """
    try:
        # 删除智能体
        assistant_service.delete_assistant(assistant_id, current_user.user_id)
        
        return AssistantDeleteResponse(
            status="success",
            message="智能体删除成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除智能体失败: {str(e)}"
        )


@router.get("/mcp-servers", status_code=HTTP_200_OK)
async def get_mcp_servers(
    current_user: User = Depends(get_current_user),
    mcp_manager: MCPServiceManager = Depends(get_mcp_service_manager)
):
    """
    获取可用的MCP服务列表
    
    Args:
        current_user: 当前认证用户
        mcp_manager: MCP服务管理器
        
    Returns:
        MCP服务列表
    """
    logger.info(f"用户 {current_user.user_id} 请求获取MCP服务列表")
    try:
        servers = await mcp_manager.get_mcp_servers()
        logger.info(f"成功返回MCP服务列表: 数量={len(servers)}")
        return {
            "status": "success",
            "data": servers
        }
    except Exception as e:
        logger.error(f"获取MCP服务列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取MCP服务列表失败: {str(e)}"
        )
