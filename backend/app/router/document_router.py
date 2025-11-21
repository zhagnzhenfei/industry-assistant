import os
import time
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, BackgroundTasks
from starlette.status import HTTP_200_OK, HTTP_500_INTERNAL_SERVER_ERROR

from service.document_management_service import DocumentManagementService
from service.auth_service import get_current_user
from models import User
from schemas.document import (
    DocumentUploadResponse,
    DocumentListResponse,
    DocumentDeleteRequest,
    DocumentDeleteResponse,
    MilvusSearchRequest,
    MilvusSearchResponse
)

# Create router instance
router = APIRouter(prefix="/documents", tags=["documents"])

# Get document management service
def get_document_service():
    return DocumentManagementService()

@router.post("/upload", status_code=HTTP_200_OK, response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    doc_service: DocumentManagementService = Depends(get_document_service)
):
    """
    上传文档，解析并存入milvus数据库
    
    Args:
        file: 要上传的文档文件
        current_user: 当前认证用户
        doc_service: 文档管理服务
    
    Returns:
        JSON响应，包含上传状态和文档详情
    """
    try:
        # 创建上传目录
        upload_dir = f"/tmp/uploads/{current_user.user_id}"
        os.makedirs(upload_dir, exist_ok=True)
        
        # 生成唯一文件名
        timestamp = int(time.time())
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        # 保存上传文件
        with open(file_path, "wb") as temp_file:
            content = await file.read()
            temp_file.write(content)
        
        # 计算文件名哈希值
        file_hash = doc_service.calculate_file_hash(file.filename)

        # 检查是否已经上传过相同内容的文件
        existing_doc = doc_service.check_duplicate_file(current_user.user_id, file_hash)
        if existing_doc:
            # 删除临时文件
            os.remove(file_path)
            return DocumentUploadResponse(
                status="success",
                message=f"文件已存在，无需重复上传",
                document_id=existing_doc.document_id,
                file_name=existing_doc.file_name
            )

        # 先处理文档（解析并存入Milvus）
        try:
            chunk_count = doc_service.process_document_to_vector_store(
                file_path=file_path,
                file_name=file.filename,
                user_id=current_user.user_id
            )

            # 只有在文档处理成功后才创建数据库记录
            if chunk_count > 0:
                # 处理成功后，在PG数据库中创建文档记录
                document = doc_service.create_document(
                    user_id=current_user.user_id,
                    file_name=file.filename,
                    file_path=file_path,
                    file_size=len(content),
                    file_type=file.content_type,
                    file_hash=file_hash
                )

                # 更新文档状态为完成
                doc_service.update_document_status(
                    document.document_id,
                    "completed",
                    chunk_count=chunk_count
                )

                return DocumentUploadResponse(
                    status="success",
                    message=f"Successfully processed and inserted {chunk_count} documents",
                    document_id=document.document_id,
                    file_name=file.filename
                )
            else:
                # 处理失败，删除临时文件并抛出异常
                os.remove(file_path)
                raise HTTPException(
                    status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="文档处理失败：未能成功处理任何文档块"
                )

        except HTTPException as http_exc:
            # 重新抛出HTTP异常
            raise http_exc
        except Exception as e:
            # 如果处理失败，删除临时文件
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"文档处理失败: {str(e)}"
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文档上传失败: {str(e)}"
        )

@router.get("/list", status_code=HTTP_200_OK, response_model=DocumentListResponse)
async def get_user_documents(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    current_user: User = Depends(get_current_user),
    doc_service: DocumentManagementService = Depends(get_document_service)
):
    """
    获取当前用户的文档列表
    
    Args:
        page: 页码，从1开始
        page_size: 每页数量
        current_user: 当前认证用户
        doc_service: 文档管理服务
        
    Returns:
        JSON响应，包含用户的文档列表
    """
    try:
        result = doc_service.get_user_documents(
            user_id=current_user.user_id,
            page=page,
            page_size=page_size
        )
        
        return DocumentListResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文档列表失败: {str(e)}"
        )

@router.post("/delete", status_code=HTTP_200_OK, response_model=DocumentDeleteResponse)
async def delete_user_documents(
    request: DocumentDeleteRequest,
    current_user: User = Depends(get_current_user),
    doc_service: DocumentManagementService = Depends(get_document_service)
):
    """
    删除用户的文档（同时删除PG、Milvus和物理文件）

    Args:
        request: 包含要删除的文档ID列表
        current_user: 当前认证用户
        doc_service: 文档管理服务

    Returns:
        JSON响应，包含删除状态
    """
    try:
        deleted_count = 0
        deletion_details = []
        
        for document_id in request.document_ids:
            try:
                # 删除文档（返回详细的删除结果）
                deletion_result = doc_service.delete_document(document_id, current_user.user_id)
                
                # 只要PG记录删除成功就算删除成功
                if deletion_result['document_deleted']:
                    deleted_count += 1
                    
                    # 记录删除详情
                    detail = f"文档 {document_id}"
                    if deletion_result['errors']:
                        detail += f" (部分失败: {'; '.join(deletion_result['errors'])})"
                    deletion_details.append(detail)
                else:
                    deletion_details.append(f"文档 {document_id} 删除失败")
                    
            except Exception as e:
                print(f"删除文档 {document_id} 失败: {e}")
                deletion_details.append(f"文档 {document_id} 删除失败: {str(e)}")
        
        # 构建返回消息
        if deleted_count == len(request.document_ids):
            status_msg = "success"
            message = f"成功删除 {deleted_count} 个文档"
        elif deleted_count > 0:
            status_msg = "partial_success"  
            failed_count = len(request.document_ids) - deleted_count
            message = f"成功删除 {deleted_count} 个文档，{failed_count} 个文档删除失败"
        else:
            status_msg = "failed"
            message = f"删除失败，0 个文档被删除"
        
        return DocumentDeleteResponse(
            status=status_msg,
            message=message,
            deleted_count=deleted_count
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除文档失败: {str(e)}"
        )

@router.post("/search", status_code=HTTP_200_OK, response_model=MilvusSearchResponse)
async def search_documents(
    request: MilvusSearchRequest,
    current_user: User = Depends(get_current_user),
    doc_service: DocumentManagementService = Depends(get_document_service)
):
    """
    在用户文档中进行向量搜索或混合搜索（向量+文本）

    Args:
        request: 搜索请求（支持向量和混合搜索的所有参数）
        current_user: 当前认证用户
        doc_service: 文档管理服务

    Returns:
        JSON响应，包含搜索结果和混合搜索统计信息
    """
    try:
        # 直接使用文档服务中的搜索功能（支持混合搜索）
        return await doc_service.search_documents_with_milvus(
            user_id=current_user.user_id,
            query=request.query,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
            category=request.category,
            enable_hybrid_search=request.enable_hybrid_search,
            vector_weight=request.vector_weight,
            text_threshold=request.text_threshold
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索文档失败: {str(e)}"
        )




