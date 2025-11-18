# MCP工具集成文档

## 概述

本文档详细说明如何在Open Deep Research系统中集成Model Context Protocol (MCP)工具，使AI研究者能够调用外部MCP服务器提供的各种工具来增强研究能力。

## 架构设计

### 核心组件

1. **MCP客户端** (`mcp_client.py`) - 与MCP服务器通信
2. **MCP工具管理器** (`mcp_integration.py`) - 工具生命周期管理
3. **MCP服务管理器** (`mcp_service_manager.py`) - 独立服务管理
4. **工具集成层** (`odr_utils.py`) - 与现有研究工具系统集成

### 设计原则

- **按需初始化**: 只在需要时初始化MCP工具，不影响主应用启动
- **容错设计**: MCP服务不可用时，系统仍能正常运行基础功能
- **模块化**: MCP相关功能独立管理，职责清晰
- **懒加载**: 支持运行时动态加载和发现工具

## 实现步骤

### 1. MCP客户端实现

**文件**: `app/services/mcp_client.py`

```python
"""
MCP客户端实现
用于与MCP服务器通信
"""
import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
import aiohttp

logger = logging.getLogger(__name__)

class MCPClient:
    """MCP客户端"""

    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.connected = False

    async def connect(self):
        """连接到MCP服务器"""
        try:
            self.session = aiohttp.ClientSession()

            # 测试连接
            async with self.session.get(f"{self.server_url}/health") as response:
                if response.status == 200:
                    self.connected = True
                    logger.info("MCP服务器连接成功")
                else:
                    raise Exception(f"MCP服务器健康检查失败: {response.status}")

        except Exception as e:
            logger.error(f"MCP服务器连接失败: {e}")
            raise

    async def disconnect(self):
        """断开连接"""
        if self.session:
            await self.session.close()
            self.connected = False
            logger.info("MCP连接已断开")

    async def list_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        if not self.connected:
            raise Exception("未连接到MCP服务器")

        try:
            async with self.session.get(f"{self.server_url}/api/v1/tools") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("tools", [])
                else:
                    raise Exception(f"获取工具列表失败: {response.status}")

        except Exception as e:
            logger.error(f"获取MCP工具列表失败: {e}")
            raise

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """调用MCP工具"""
        if not self.connected:
            raise Exception("未连接到MCP服务器")

        try:
            payload = {
                "tool": tool_name,
                "arguments": arguments
            }

            async with self.session.post(
                f"{self.server_url}/api/v1/execution/execute",
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("result")
                else:
                    error_text = await response.text()
                    raise Exception(f"工具调用失败 {tool_name}: {error_text}")

        except Exception as e:
            logger.error(f"MCP工具调用失败 {tool_name}: {e}")
            raise
```

### 2. MCP工具管理器

**文件**: `app/services/agent_orchestration/mcp_integration.py`

```python
"""
MCP工具集成模块
用于集成Model Context Protocol工具
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from langchain_core.tools import BaseTool, StructuredTool
from langchain_core.runnables import RunnableConfig

from app.services.mcp_client import MCPClient

logger = logging.getLogger(__name__)

class MCPToolManager:
    """MCP工具管理器"""

    def __init__(self, server_url: str = "http://localhost:8000"):
        self.mcp_client = MCPClient(server_url)
        self.available_tools: Dict[str, BaseTool] = {}
        self.initialized = False

    async def initialize(self):
        """初始化MCP工具管理器"""
        try:
            # 连接到MCP服务器
            await self.mcp_client.connect()

            # 获取可用工具列表
            mcp_tools = await self.mcp_client.list_tools()

            # 转换为LangChain工具
            for mcp_tool in mcp_tools:
                try:
                    langchain_tool = self._convert_mcp_to_langchain_tool(mcp_tool)
                    self.available_tools[langchain_tool.name] = langchain_tool
                    logger.info(f"加载MCP工具: {langchain_tool.name}")
                except Exception as e:
                    logger.warning(f"转换MCP工具失败 {mcp_tool.get('name', 'unknown')}: {e}")

            self.initialized = True
            logger.info(f"MCP工具管理器初始化完成，加载了 {len(self.available_tools)} 个工具")

        except Exception as e:
            logger.error(f"MCP工具管理器初始化失败: {e}")
            raise

    def _convert_mcp_to_langchain_tool(self, mcp_tool: Dict[str, Any]) -> BaseTool:
        """将MCP工具转换为LangChain工具"""
        tool_name = mcp_tool["name"]
        tool_description = mcp_tool.get("description", "")

        async def mcp_tool_wrapper(**kwargs):
            """MCP工具包装器"""
            try:
                logger.info(f"调用MCP工具: {tool_name} with args: {kwargs}")

                # 调用MCP工具
                result = await self.mcp_client.call_tool(tool_name, kwargs)

                logger.info(f"MCP工具 {tool_name} 调用成功")
                return result

            except Exception as e:
                logger.error(f"MCP工具调用失败 {tool_name}: {e}")
                return f"工具调用失败: {str(e)}"

        # 创建LangChain工具
        langchain_tool = StructuredTool.from_function(
            func=mcp_tool_wrapper,
            name=tool_name,
            description=tool_description,
            args_schema=mcp_tool.get("input_schema", None)
        )

        # 标记为MCP工具
        langchain_tool._is_mcp_tool = True

        return langchain_tool

    def get_tools(self) -> List[BaseTool]:
        """获取所有可用的MCP工具"""
        if not self.initialized:
            logger.warning("MCP工具管理器未初始化")
            return []

        return list(self.available_tools.values())

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """直接调用MCP工具"""
        if tool_name not in self.available_tools:
            raise ValueError(f"工具 {tool_name} 不存在")

        tool = self.available_tools[tool_name]
        return await tool.ainvoke(args)

    async def cleanup(self):
        """清理资源"""
        if self.initialized:
            await self.mcp_client.disconnect()
            self.initialized = False
            logger.info("MCP工具管理器资源清理完成")
```

### 3. MCP服务管理器

**文件**: `app/services/agent_orchestration/mcp_service_manager.py`

```python
"""
MCP服务管理器
独立管理MCP相关服务的生命周期
"""
import asyncio
import logging
from typing import Dict, Any
from app.services.agent_orchestration.mcp_integration import MCPToolManager

logger = logging.getLogger(__name__)

class MCPServiceManager:
    """MCP服务管理器 - 独立管理MCP相关服务"""

    def __init__(self):
        self.initialized = False
        self.tool_manager: Optional[MCPToolManager] = None
        self.server_url = "http://localhost:8000"

    async def initialize_if_needed(self, server_url: str = None):
        """按需初始化"""
        if not self.initialized:
            await self.initialize(server_url)

    async def initialize(self, server_url: str = None):
        """初始化MCP服务"""
        if server_url:
            self.server_url = server_url

        try:
            logger.info("初始化MCP服务管理器...")

            self.tool_manager = MCPToolManager(self.server_url)
            await self.tool_manager.initialize()

            self.initialized = True
            logger.info("MCP服务管理器初始化完成")

        except Exception as e:
            logger.error(f"MCP服务管理器初始化失败: {e}")
            # 不抛出异常，允许系统继续运行
            self.initialized = False

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        if self.initialized and self.tool_manager and self.tool_manager.initialized:
            tools = self.tool_manager.get_tools()
            return {
                "status": "healthy",
                "server_url": self.server_url,
                "tools_count": len(tools),
                "tools": [tool.name for tool in tools]
            }
        else:
            return {
                "status": "unhealthy",
                "server_url": self.server_url,
                "error": "MCP服务未初始化"
            }

    def get_tools(self):
        """获取可用工具"""
        if self.initialized and self.tool_manager:
            return self.tool_manager.get_tools()
        return []

    async def cleanup(self):
        """清理资源"""
        if self.tool_manager:
            await self.tool_manager.cleanup()
        self.initialized = False
        logger.info("MCP服务管理器已清理")

# 全局实例
mcp_service_manager = MCPServiceManager()
```

### 4. 配置更新

**文件**: `app/services/agent_orchestration/odr_configuration.py`

```python
# 在Configuration类中添加MCP相关配置

@dataclass
class Configuration:
    # ... 现有配置 ...

    # MCP配置
    mcp_server_url: str = "http://localhost:8000"
    enable_mcp_tools: bool = True
    mcp_timeout: int = 30
    mcp_tools_whitelist: List[str] = field(default_factory=list)  # 空列表表示允许所有工具
    mcp_tools_blacklist: List[str] = field(default_factory=list)  # 黑名单
```

### 5. 工具集成层更新

**文件**: `app/services/agent_orchestration/odr_utils.py`

```python
# 更新 get_all_tools 函数
async def get_all_tools(config: RunnableConfig) -> List[BaseTool]:
    """获取所有可用工具（包含MCP工具）"""
    tools = []

    # 添加搜索工具
    configurable = Configuration.from_runnable_config(config)
    if configurable.search_api == SearchAPI.TAVILY:
        tools.append(tavily_search)
    elif configurable.search_api == SearchAPI.SERPER:
        tools.append(serper_search_tool)

    # 添加think_tool
    tools.append(think_tool)

    # 按需加载MCP工具
    if configurable.enable_mcp_tools:
        try:
            from .mcp_service_manager import mcp_service_manager

            # 按需初始化MCP工具
            await mcp_service_manager.initialize_if_needed(configurable.mcp_server_url)

            if mcp_service_manager.initialized:
                mcp_tools = mcp_service_manager.get_tools()

                # 应用白名单和黑名单过滤
                filtered_tools = []
                for tool in mcp_tools:
                    tool_name = tool.name

                    # 检查白名单
                    if configurable.mcp_tools_whitelist and tool_name not in configurable.mcp_tools_whitelist:
                        continue

                    # 检查黑名单
                    if tool_name in configurable.mcp_tools_blacklist:
                        continue

                    filtered_tools.append(tool)

                tools.extend(filtered_tools)
                logger.info(f"已加载 {len(filtered_tools)} 个MCP工具")

        except Exception as e:
            logger.warning(f"加载MCP工具失败，继续使用基础工具: {e}")

    return tools
```

### 6. 编排器初始化更新

**文件**: `app/services/research_service.py`

```python
# 更新 get_orchestrator 函数
async def get_orchestrator(research_depth: str = "comprehensive") -> ODRResearchOrchestrator:
    """获取编排器实例（支持MCP工具）"""
    global orchestrator

    if orchestrator is None:
        # 从环境变量或配置文件读取MCP设置
        mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
        enable_mcp = os.getenv("MCP_ENABLED", "true").lower() == "true"

        config = Configuration(
            max_concurrent_research_units=5,
            max_researcher_iterations=6,
            max_react_tool_calls=10,
            allow_clarification=True,
            search_api="serper",
            enable_mcp_tools=enable_mcp,
            mcp_server_url=mcp_server_url,
            mcp_timeout=30
        )

        orchestrator = ODRResearchOrchestrator(config)

        # 添加超时保护
        try:
            await asyncio.wait_for(orchestrator.initialize(), timeout=30.0)
            logger.info(f"Open Deep Research 编排器已创建并初始化 (MCP: {enable_mcp})")
        except asyncio.TimeoutError:
            logger.error("编排器初始化超时")
            raise Exception("编排器初始化超时")

    return orchestrator
```

## 环境配置

### 1. 环境变量配置

**文件**: `.env`

```env
# MCP配置
MCP_SERVER_URL=http://localhost:8000
MCP_ENABLED=true
MCP_TIMEOUT=30

# 可选：工具过滤配置
MCP_TOOLS_WHITELIST=  # 逗号分隔的工具名列表，为空表示允许所有
MCP_TOOLS_BLACKLIST=  # 逗号分隔的工具黑名单
```

### 2. Docker Compose配置

**文件**: `docker-compose.yml`

```yaml
services:
  # 现有服务...

  mcp-service:
    build:
      context: ./mcp-app
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - MCP_SERVER_PORT=8000
    volumes:
      - ./mcp-app/configs:/app/configs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  app:
    # 现有配置...
    environment:
      # 现有环境变量...
      - MCP_SERVER_URL=http://mcp-service:8000
      - MCP_ENABLED=true
    depends_on:
      - mcp-service
```

## 使用示例

### 1. 研究者调用MCP工具

```python
# 研究者可能会自动调用这些MCP工具：
{
    "tool_name": "database_query",
    "args": {
        "sql": "SELECT * FROM research_papers WHERE topic = 'AI' LIMIT 10",
        "database": "academic_papers"
    }
}

{
    "tool_name": "web_scraping",
    "args": {
        "url": "https://arxiv.org/list/cs.AI/recent",
        "selector": ".list-title",
        "max_items": 20
    }
}

{
    "tool_name": "file_analyzer",
    "args": {
        "file_path": "/data/research_papers.pdf",
        "analysis_type": "extract_key_findings"
    }
}
```

### 2. 配置特定工具

```python
# 只允许特定MCP工具
config = Configuration(
    enable_mcp_tools=True,
    mcp_tools_whitelist=["database_query", "web_scraping"],
    mcp_tools_blacklist=["file_deleter"]  # 禁用危险工具
)
```

## 监控和调试

### 1. 健康检查端点

**文件**: `app/router/enhanced_research_router_simple.py`

```python
@router.get("/mcp-health")
async def mcp_health_check():
    """MCP服务健康检查"""
    try:
        from app.services.agent_orchestration.mcp_service_manager import mcp_service_manager
        health_status = await mcp_service_manager.health_check()
        return health_status
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
```

### 2. 工具列表端点

```python
@router.get("/mcp-tools")
async def list_mcp_tools():
    """列出所有可用的MCP工具"""
    try:
        from app.services.agent_orchestration.mcp_service_manager import mcp_service_manager

        await mcp_service_manager.initialize_if_needed()
        tools = mcp_service_manager.get_tools()

        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "is_mcp_tool": getattr(tool, '_is_mcp_tool', False)
                }
                for tool in tools
            ]
        }
    except Exception as e:
        return {"error": str(e)}
```

## 错误处理

### 1. 连接失败处理

```python
# MCP服务不可用时的降级策略
try:
    await mcp_service_manager.initialize_if_needed()
    mcp_tools = mcp_service_manager.get_tools()
except Exception as e:
    logger.warning(f"MCP服务不可用，使用基础工具: {e}")
    mcp_tools = []  # 空列表，继续使用基础搜索工具
```

### 2. 工具调用失败处理

```python
# 在MCP工具包装器中已经包含错误处理
async def mcp_tool_wrapper(**kwargs):
    try:
        result = await self.mcp_client.call_tool(tool_name, kwargs)
        return result
    except Exception as e:
        logger.error(f"MCP工具调用失败 {tool_name}: {e}")
        return f"工具调用失败: {str(e)}"  # 返回错误信息而不是抛出异常
```

## 测试

### 1. 单元测试

**文件**: `tests/test_mcp_integration.py`

```python
import pytest
from app.services.agent_orchestration.mcp_integration import MCPToolManager
from app.services.agent_orchestration.mcp_service_manager import MCPServiceManager

@pytest.mark.asyncio
async def test_mcp_tool_manager_initialization():
    manager = MCPToolManager("http://localhost:8000")

    # 测试初始化
    await manager.initialize()
    assert manager.initialized == True

    # 测试工具获取
    tools = manager.get_tools()
    assert isinstance(tools, list)

    await manager.cleanup()

@pytest.mark.asyncio
async def test_mcp_service_manager():
    service_manager = MCPServiceManager()

    # 测试按需初始化
    await service_manager.initialize_if_needed()

    # 测试健康检查
    health = await service_manager.health_check()
    assert "status" in health
```

### 2. 集成测试

```python
@pytest.mark.asyncio
async def test_research_with_mcp_tools():
    # 测试研究流程是否能正确使用MCP工具
    from app.services.research_service import execute_research_task_sync

    result = await execute_research_task_sync(
        research_id="test_mcp",
        question="使用数据库查询最新的AI研究论文",
        allow_clarification=False,
        research_depth="basic"
    )

    assert result.status in ["completed", "failed"]
    if result.status == "completed":
        assert result.final_report is not None
```

## 部署注意事项

### 1. 网络配置

- 确保MCP服务端口可访问
- 在Docker网络中，服务间通信使用服务名
- 外部访问需要端口映射

### 2. 安全考虑

- 不要在生产环境中暴露所有MCP工具
- 使用白名单机制限制可用工具
- 定期审计MCP工具的安全性

### 3. 性能优化

- 设置合理的超时时间
- 监控MCP工具调用频率和响应时间
- 考虑MCP服务的负载均衡

## 故障排除

### 1. 常见问题

**Q: MCP工具初始化失败**
A: 检查MCP服务是否运行，网络连接是否正常

**Q: 工具调用超时**
A: 调整`mcp_timeout`配置，检查MCP服务性能

**Q: 某些工具不可用**
A: 检查工具白名单/黑名单配置

### 2. 调试日志

```python
# 启用详细日志
import logging
logging.getLogger("app.services.agent_orchestration.mcp_integration").setLevel(logging.DEBUG)
logging.getLogger("app.services.mcp_client").setLevel(logging.DEBUG)
```

## 扩展功能

### 1. 动态工具发现

```python
# 支持运行时添加新的MCP工具
async def add_mcp_server(server_url: str):
    """添加新的MCP服务器"""
    new_manager = MCPToolManager(server_url)
    await new_manager.initialize()

    # 合并到现有工具池
    mcp_service_manager.tool_manager.available_tools.update(
        new_manager.available_tools
    )
```

### 2. 工具使用统计

```python
# 记录工具使用情况
class MCPToolManager:
    def __init__(self, server_url: str):
        # ... 现有代码 ...
        self.usage_stats = {}

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        # 记录使用次数
        self.usage_stats[tool_name] = self.usage_stats.get(tool_name, 0) + 1

        # ... 调用逻辑 ...
```

## 总结

通过以上完整的MCP工具集成方案，AI研究系统获得了以下能力：

### 核心优势

1. **扩展性**: 可以轻松添加各种外部工具，大大增强研究能力
2. **模块化**: MCP工具独立管理，不影响现有系统稳定性
3. **容错性**: MCP服务不可用时，系统仍能正常运行基础功能
4. **安全性**: 支持工具白名单/黑名单，可以精细控制工具访问权限

### 典型应用场景

1. **数据库查询**: 直接查询学术数据库、统计数据等
2. **文件处理**: 分析PDF文档、提取关键信息、格式转换等
3. **网络爬虫**: 获取最新研究动态、抓取特定网站数据
4. **计算工具**: 数据分析、图表生成、统计计算等
5. **API集成**: 调用外部API获取实时数据、第三方服务等

### 部署建议

1. **开发环境**: 启用所有MCP工具进行测试和开发
2. **测试环境**: 使用白名单限制工具范围，确保系统稳定性
3. **生产环境**: 严格限制工具访问权限，定期审计工具安全性

通过这套完整的MCP集成方案，AI研究系统将成为一个真正可扩展的智能研究平台，能够根据需要动态集成各种外部工具和服务，为研究者提供更强大的研究能力。