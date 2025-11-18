"""
图表存储抽象层
"""
from abc import ABC, abstractmethod
from typing import Optional
import uuid
from pathlib import Path
from datetime import datetime


class ChartStorage(ABC):
    """图表存储抽象基类"""
    
    @abstractmethod
    async def save(self, image_data: bytes, format: str = "png") -> str:
        """
        保存图片，返回ID
        
        Args:
            image_data: 图片二进制数据
            format: 图片格式（png, jpg等）
            
        Returns:
            图片ID
        """
        pass
    
    @abstractmethod
    async def get(self, chart_id: str) -> Optional[bytes]:
        """
        根据ID获取图片
        
        Args:
            chart_id: 图片ID
            
        Returns:
            图片二进制数据，不存在则返回None
        """
        pass
    
    @abstractmethod
    async def delete(self, chart_id: str) -> bool:
        """
        删除图片
        
        Args:
            chart_id: 图片ID
            
        Returns:
            是否成功删除
        """
        pass


class FileSystemStorage(ChartStorage):
    """文件系统存储实现"""
    
    def __init__(self, base_dir: str = "./data/charts"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    async def save(self, image_data: bytes, format: str = "png") -> str:
        """
        保存到文件系统，文件名包含时间戳
        格式：YYYYMMDD_HHMMSS_uuid.png
        """
        # 生成带时间戳的文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]  # 取前8位
        chart_id = f"{timestamp}_{unique_id}"
        
        filepath = self.base_dir / f"{chart_id}.{format}"
        
        # 异步写入
        try:
            import aiofiles
            async with aiofiles.open(filepath, 'wb') as f:
                await f.write(image_data)
        except ImportError:
            # 如果aiofiles未安装，使用同步方式
            with open(filepath, 'wb') as f:
                f.write(image_data)
        
        return chart_id
    
    async def get(self, chart_id: str) -> Optional[bytes]:
        """从文件系统读取"""
        # 尝试多种格式
        for ext in ['png', 'jpg', 'jpeg', 'svg']:
            filepath = self.base_dir / f"{chart_id}.{ext}"
            if filepath.exists():
                try:
                    import aiofiles
                    async with aiofiles.open(filepath, 'rb') as f:
                        return await f.read()
                except ImportError:
                    # 如果aiofiles未安装，使用同步方式
                    with open(filepath, 'rb') as f:
                        return f.read()
        
        return None
    
    async def delete(self, chart_id: str) -> bool:
        """删除文件"""
        for ext in ['png', 'jpg', 'jpeg', 'svg']:
            filepath = self.base_dir / f"{chart_id}.{ext}"
            if filepath.exists():
                filepath.unlink()
                return True
        return False

