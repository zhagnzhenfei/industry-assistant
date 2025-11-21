"""
简化的配置管理器
仅管理MCP服务器连接配置
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from app.models.mcp_models import MCPServerConfig
from app.core.config import settings

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器"""

    def __init__(self):
        self.config_file = Path(settings.config_dir) / "mcp_servers.json"
        self.servers: Dict[str, MCPServerConfig] = {}
        logger.info(f"配置文件路径: {self.config_file.absolute()}")
        logger.info(f"配置文件是否存在: {self.config_file.exists()}")
        self.load_config()

    def load_config(self):
        """从配置文件加载服务器配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                servers_data = config_data.get("servers", {})
                for server_id, server_data in servers_data.items():
                    try:
                        # 确保ID一致
                        server_data["id"] = server_id
                        server_config = MCPServerConfig(**server_data)
                        self.servers[server_id] = server_config
                        logger.info(f"加载服务器配置: {server_config.name}")
                    except Exception as e:
                        logger.error(f"加载服务器配置失败 {server_id}: {e}")

                logger.info(f"成功加载 {len(self.servers)} 个服务器配置")
            else:
                logger.warning(f"配置文件不存在: {self.config_file}")
                self._create_default_config()

        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            self._create_default_config()

    def _create_default_config(self):
        """创建默认配置"""
        default_config = {
            "servers": {
                "postgres-server": {
                    "id": "postgres-server",
                    "name": "PostgreSQL数据库服务器",
                    "description": "提供数据库操作工具的MCP服务器",
                    "type": "stdio",
                    "command": "python",
                    "args": ["-m", "app.services.postgres_server"],
                    "env": {
                        "POSTGRES_HOST": "postgres",
                        "POSTGRES_PORT": "5432",
                        "POSTGRES_USER": "postgres",
                        "POSTGRES_PASSWORD": "",
                        "POSTGRES_DB": "postgres"
                    },
                    "timeout": 60,
                    "retry_count": 3,
                    "is_active": True
                }
            }
        }

        try:
            # 确保目录存在
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)

            logger.info(f"创建默认配置文件: {self.config_file}")
            self.load_config()

        except Exception as e:
            logger.error(f"创建默认配置文件失败: {e}")

    def save_config(self):
        """保存配置到文件"""
        try:
            config_data = {
                "servers": {
                    server_id: server_config.model_dump()
                    for server_id, server_config in self.servers.items()
                }
            }

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            logger.info(f"配置文件已保存: {self.config_file}")

        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")

    def add_server(self, server_config: MCPServerConfig) -> bool:
        """添加服务器配置"""
        try:
            if server_config.id in self.servers:
                logger.warning(f"服务器配置已存在: {server_config.id}")
                return False

            self.servers[server_config.id] = server_config
            self.save_config()
            logger.info(f"添加服务器配置: {server_config.id}")
            return True

        except Exception as e:
            logger.error(f"添加服务器配置失败: {e}")
            return False

    def remove_server(self, server_id: str) -> bool:
        """移除服务器配置"""
        try:
            if server_id not in self.servers:
                logger.warning(f"服务器配置不存在: {server_id}")
                return False

            del self.servers[server_id]
            self.save_config()
            logger.info(f"移除服务器配置: {server_id}")
            return True

        except Exception as e:
            logger.error(f"移除服务器配置失败: {e}")
            return False

    def update_server(self, server_id: str, updates: Dict[str, Any]) -> bool:
        """更新服务器配置"""
        try:
            if server_id not in self.servers:
                logger.warning(f"服务器配置不存在: {server_id}")
                return False

            current_config = self.servers[server_id]
            update_data = current_config.model_dump()
            update_data.update(updates)

            self.servers[server_id] = MCPServerConfig(**update_data)
            self.save_config()
            logger.info(f"更新服务器配置: {server_id}")
            return True

        except Exception as e:
            logger.error(f"更新服务器配置失败: {e}")
            return False

    def get_server(self, server_id: str) -> Optional[MCPServerConfig]:
        """获取服务器配置"""
        return self.servers.get(server_id)

    def get_all_servers(self) -> List[MCPServerConfig]:
        """获取所有服务器配置"""
        return list(self.servers.values())

    def get_active_servers(self) -> List[MCPServerConfig]:
        """获取活跃服务器配置"""
        return [server for server in self.servers.values() if server.is_active]

    def reload_config(self):
        """重新加载配置"""
        self.servers.clear()
        self.load_config()
        logger.info("配置已重新加载")

    def export_config(self) -> Dict[str, Any]:
        """导出配置"""
        return {
            "servers": {
                server_id: server_config.model_dump()
                for server_id, server_config in self.servers.items()
            }
        }

    def import_config(self, config_data: Dict[str, Any]) -> bool:
        """导入配置"""
        try:
            servers_data = config_data.get("servers", {})
            imported_count = 0

            for server_id, server_data in servers_data.items():
                try:
                    server_data["id"] = server_id
                    server_config = MCPServerConfig(**server_data)
                    self.servers[server_id] = server_config
                    imported_count += 1
                except Exception as e:
                    logger.error(f"导入服务器配置失败 {server_id}: {e}")

            if imported_count > 0:
                self.save_config()
                logger.info(f"成功导入 {imported_count} 个服务器配置")
                return True

            return False

        except Exception as e:
            logger.error(f"导入配置失败: {e}")
            return False