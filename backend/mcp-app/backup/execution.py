"""
工具执行API
"""
from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, List, Optional
from app.models.tool_models import ToolExecutionRequest, ToolExecutionResult
from app.services.execution_service import ToolExecutionService

router = APIRouter()

# 依赖注入
execution_service: Optional[ToolExecutionService] = None

@router.post("/execute")
async def execute_tool(request: ToolExecutionRequest) -> ToolExecutionResult:
    """执行工具"""
    if not execution_service:
        raise HTTPException(status_code=500, detail="Execution service not initialized")
    
    try:
        result = await execution_service.execute_tool(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execute/batch")
async def execute_tools_batch(requests: List[ToolExecutionRequest]) -> List[ToolExecutionResult]:
    """批量执行工具"""
    if not execution_service:
        raise HTTPException(status_code=500, detail="Execution service not initialized")
    
    try:
        results = await execution_service.execute_tools_batch(requests)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cancel/{request_id}")
async def cancel_execution(request_id: str):
    """取消工具执行"""
    if not execution_service:
        raise HTTPException(status_code=500, detail="Execution service not initialized")
    
    success = await execution_service.cancel_execution(request_id)
    if success:
        return {"message": "Execution cancelled successfully"}
    else:
        raise HTTPException(status_code=404, detail="Execution not found")

@router.get("/active")
async def get_active_executions() -> List[str]:
    """获取活跃的执行任务"""
    if not execution_service:
        raise HTTPException(status_code=500, detail="Execution service not initialized")
    
    return execution_service.get_active_executions()

@router.post("/test/{tool_id}")
async def test_tool(tool_id: str, arguments: Dict[str, Any] = Body(...)):
    """测试工具"""
    if not execution_service:
        raise HTTPException(status_code=500, detail="Execution service not initialized")
    
    try:
        # 创建测试请求
        request = ToolExecutionRequest(
            tool_id=tool_id,
            arguments=arguments,
            request_id=f"test_{tool_id}",
            timeout=30  # 测试时使用较短的超时时间
        )
        
        result = await execution_service.execute_tool(request)
        return {
            "tool_id": tool_id,
            "test_result": result.dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
