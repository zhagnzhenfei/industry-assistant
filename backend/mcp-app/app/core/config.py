"""
应用配置管理
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基本配置
    app_name: str = Field(default="Generic MCP Service", description="应用名称")
    app_version: str = Field(default="1.0.0", description="应用版本")
    debug: bool = Field(default=True, description="调试模式")
    
    # 服务器配置
    host: str = Field(default="0.0.0.0", description="服务器主机")
    port: int = Field(default=8000, description="服务器端口")
    
    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别")
    
    # 文件路径配置
    config_dir: str = Field(default="configs", description="配置文件目录")
    logs_dir: str = Field(default="logs", description="日志文件目录")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._setup_directories()
    
    def _setup_directories(self):
        """创建必要的目录"""
        directories = [
            self.config_dir,
            self.logs_dir
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    @property
    def config_path(self) -> Path:
        """配置文件路径"""
        return Path(self.config_dir)
    
    @property
    def logs_path(self) -> Path:
        """日志文件路径"""
        return Path(self.logs_dir)

# 全局配置实例
settings = Settings()
