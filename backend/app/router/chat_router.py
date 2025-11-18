from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
import os

from service import DocumentManagementService, WebSearchService, ChatService, SessionService, ServiceConfig, PolicySearchService
from service.chat_service_v2 import ChatServiceV2
from schemas import ChatRequest, SessionRequest, SessionResponse

# Create router instance
router = APIRouter(prefix="/chat", tags=["chat"])

# Get service instances
def get_services():
    config = ServiceConfig.get_api_config()
    doc_service = DocumentManagementService()
    web_service = WebSearchService(api_key=config.get('serper_api_key'))
    session_service = SessionService()
    chat_service = ChatService(doc_service, web_service, session_service)
    return {
        "chat_service": chat_service, 
        "session_service": session_service,
        "default_dataset_id": config['default_dataset_id']
    }

# Get v2 service instances
def get_services_v2():
    config = ServiceConfig.get_api_config()
    doc_service = DocumentManagementService()
    web_service = WebSearchService(api_key=config.get('serper_api_key'))
    session_service = SessionService()
    policy_service = PolicySearchService(
        es_host=os.environ.get('ES_HOST', 'host.docker.internal'),
        es_port=int(os.environ.get('ES_PORT', '1200')),
        index_name=os.environ.get('POLICY_INDEX', 'policy_documents'),
        es_user=os.environ.get('ES_USER', 'elastic'),
        es_password=os.environ.get('ES_PASSWORD', 'infini_rag_flow')
    )
    chat_service_v2 = ChatServiceV2(doc_service, web_service, session_service, policy_service)
    return {
        "chat_service": chat_service_v2, 
        "session_service": session_service,
        "default_dataset_id": config['default_dataset_id']
    }

@router.post("/session", response_model=SessionResponse, status_code=HTTP_200_OK)
async def create_session(
    services: Dict[str, Any] = Depends(get_services)
):
    """
    创建新的聊天会话
    
    Returns:
        新创建的会话信息
    """
    session_service = services["session_service"]
    
    try:
        session_data = session_service.create_session()
        return SessionResponse(**session_data)
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建会话失败: {str(e)}"
        )

@router.post("/completion/v1", status_code=HTTP_200_OK)
async def chat_completion(
    request: ChatRequest,
    services: Dict[str, Any] = Depends(get_services)
):
    """
    聊天补全接口，结合知识库检索和Web搜索，进行问答
    
    Args:
        request: 包含用户问题和会话信息的请求体
        
    Returns:
        流式响应，包含检索内容和模型生成内容
    """
    chat_service = services["chat_service"]
    default_dataset_id = services["default_dataset_id"]
    session_service = services["session_service"]
    
    # 验证会话ID（如果提供）
    if request.session_id:
        session = session_service.get_session(request.session_id)
        if not session:
            # 如果会话不存在，创建新会话
            session_data = session_service.create_session()
            request.session_id = session_data["session_id"]
    
    # 创建异步生成器函数
    async def generate_response():
        try:
            # 从知识库检索文档
            knowledge_docs = []
            if request.search_knowledge:
                knowledge_docs = chat_service.retrieve_from_knowledge_base(
                    question=request.question,
                    dataset_id=default_dataset_id
                )
            
            # 从Web搜索检索信息
            web_docs = []
            if request.search_web:
                web_docs = chat_service.retrieve_from_web(
                    question=request.question
                )
            
            # 合并文档并重排
            all_docs = knowledge_docs + web_docs
            reranked_docs = chat_service.rerank_documents(
                question=request.question, 
                documents=all_docs
            )
            
            # 生成流式回答
            for message_chunk in chat_service.get_chat_completion(
                session_id=request.session_id,
                question=request.question,
                retrieved_content=reranked_docs
            ):
                yield message_chunk
                
        except Exception as e:
            # 错误处理
            error_message = f"event: error\ndata: {str(e)}\n\n"
            yield error_message
    
    # 返回流式响应
    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream"
    )

@router.post("/completion", status_code=HTTP_200_OK)
async def chat_completion_v2(
    request: ChatRequest,
    services: Dict[str, Any] = Depends(get_services_v2)
):
    """
    聊天补全接口v2版本，使用政策文档索引进行检索，结合知识库检索和Web搜索，进行问答
    
    Args:
        request: 包含用户问题和会话信息的请求体
        
    Returns:
        流式响应，包含检索内容和模型生成内容
    """
    chat_service = services["chat_service"]
    default_dataset_id = services["default_dataset_id"]
    session_service = services["session_service"]
    
    # 验证会话ID（如果提供）
    if request.session_id:
        session = session_service.get_session(request.session_id)
        if not session:
            # 如果会话不存在，创建新会话
            session_data = session_service.create_session()
            request.session_id = session_data["session_id"]
    
    # 创建异步生成器函数
    async def generate_response():
        try:
            # 从政策文档索引检索
            policy_docs = []
            if request.search_knowledge:
                policy_docs = chat_service.retrieve_from_policy_documents(
                    question=request.question
                )
            
            # 从Web搜索检索信息
            web_docs = []
            if request.search_web:
                web_docs = chat_service.retrieve_from_web(
                    question=request.question
                )
            
            # 合并文档并重排
            all_docs = policy_docs + web_docs
            reranked_docs = chat_service.rerank_documents(
                question=request.question, 
                documents=all_docs
            )
            
            # 生成流式回答
            for message_chunk in chat_service.get_chat_completion(
                session_id=request.session_id,
                question=request.question,
                retrieved_content=reranked_docs
            ):
                yield message_chunk
                
        except Exception as e:
            # 错误处理
            error_message = f"event: error\ndata: {str(e)}\n\n"
            yield error_message
    
    # 返回流式响应
    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream"
    )
