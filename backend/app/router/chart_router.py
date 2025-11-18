"""
图表API路由
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from services.visualization.chart_storage import FileSystemStorage
from configs.visualization_config import get_visualization_settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["图表"])

# 全局存储实例
_chart_storage = None


def get_chart_storage():
    """获取图表存储实例"""
    global _chart_storage
    if _chart_storage is None:
        settings = get_visualization_settings()
        _chart_storage = FileSystemStorage(settings.CHART_STORAGE_DIR)
    return _chart_storage


@router.get("/api/charts/{chart_id}")
async def get_chart(chart_id: str):
    """
    获取图表图片
    
    Args:
        chart_id: 图表唯一ID（带时间戳格式：20251010_143025_abc123）
        
    Returns:
        图片二进制数据（PNG格式）
    """
    logger.info(f"[CHART] 获取图表: {chart_id}")
    
    storage = get_chart_storage()
    image_data = await storage.get(chart_id)
    
    if not image_data:
        logger.warning(f"[CHART] 图表不存在: {chart_id}")
        raise HTTPException(status_code=404, detail="图表不存在")
    
    # 返回PNG图片
    return Response(
        content=image_data,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=31536000",  # 缓存1年
            "Content-Disposition": f"inline; filename=chart_{chart_id}.png"
        }
    )


@router.delete("/api/charts/{chart_id}")
async def delete_chart(chart_id: str):
    """
    删除图表（可选，用于手动清理）
    
    Args:
        chart_id: 图表唯一ID
    """
    logger.info(f"[CHART] 删除图表: {chart_id}")
    
    storage = get_chart_storage()
    success = await storage.delete(chart_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="图表不存在")
    
    return {"message": "图表已删除", "chart_id": chart_id}

