import os
from typing import AsyncGenerator
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()


class DatabaseConfig:
    """数据库配置管理类"""
    
    def __init__(self, 
                 host: str = None,
                 port: int = None,
                 name: str = None,
                 user: str = None,
                 password: str = None):
        """
        初始化数据库配置
        
        Args:
            host: 数据库主机，默认从.env文件读取
            port: 数据库端口，默认从.env文件读取
            name: 数据库名，默认从.env文件读取
            user: 数据库用户，默认从.env文件读取
            password: 数据库密码，默认从.env文件读取
        """
        self.host = host or os.getenv('DB_HOST', 'postgres')
        self.port = port or int(os.getenv('DB_PORT', '5432'))
        self.name = name or os.getenv('DB_NAME', 'app_db')
        self.user = user or os.getenv('DB_USER', 'app_user')
        self.password = password or os.getenv('DB_PASSWORD', 'app_password')
    
    def get_database_url(self) -> str:
        """获取同步数据库连接URL"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
    
    def get_async_database_url(self) -> str:
        """获取异步数据库连接URL"""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
    
    def __repr__(self):
        return f"DatabaseConfig(host='{self.host}', port={self.port}, name='{self.name}', user='{self.user}')"


class DatabaseManager:
    """数据库管理器 - 作为工具类使用"""
    
    def __init__(self, config: DatabaseConfig = None):
        """
        初始化数据库管理器
        
        Args:
            config: 数据库配置，如果为None则使用默认配置
        """
        self.config = config or DatabaseConfig()
        self._engine = None
        self._async_engine = None
        self._session_factory = None
        self._async_session_factory = None
    
    @property
    def engine(self):
        """获取同步数据库引擎（懒加载）"""
        if self._engine is None:
            self._engine = create_engine(
                self.config.get_database_url(), 
                echo=False,
                pool_pre_ping=True,  # 连接前检查
                pool_recycle=3600    # 1小时后回收连接
            )
        return self._engine
    
    @property
    def async_engine(self):
        """获取异步数据库引擎（懒加载）"""
        if self._async_engine is None:
            self._async_engine = create_async_engine(
                self.config.get_async_database_url(),
                echo=False,
                pool_pre_ping=True,
                pool_recycle=3600
            )
        return self._async_engine
    
    @property
    def session_factory(self):
        """获取同步会话工厂（懒加载）"""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                autocommit=False, 
                autoflush=False, 
                bind=self.engine
            )
        return self._session_factory
    
    @property
    def async_session_factory(self):
        """获取异步会话工厂（懒加载）"""
        if self._async_session_factory is None:
            self._async_session_factory = sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                autocommit=False,
                autoflush=False
            )
        return self._async_session_factory
    
    def get_session(self):
        """获取同步数据库会话"""
        db = self.session_factory()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取异步数据库会话"""
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    def close(self):
        """关闭数据库连接"""
        if self._engine:
            self._engine.dispose()
        if self._async_engine:
            import asyncio
            asyncio.create_task(self.async_engine.dispose())


# 创建默认实例
default_config = DatabaseConfig()
default_manager = DatabaseManager(default_config)

# 便捷函数
def get_session():
    """获取同步数据库会话"""
    return default_manager.get_session()

async def get_async_session():
    """获取异步数据库会话"""
    async for session in default_manager.get_async_session():
        yield session

# 创建Base类
Base = declarative_base()

# 元数据
metadata = MetaData()
