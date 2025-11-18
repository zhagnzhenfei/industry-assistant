"""
具体的Researcher Agent实现
包含数据收集、分析、报告生成等专门化的Agent
"""
import os
import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base_agent import BaseResearcher
from .mcp_client import MCPClient

logger = logging.getLogger(__name__)


class DataRetrievalAgent(BaseResearcher):
    """数据收集Agent - 专注于文件搜索和数据获取"""

    def __init__(self, mcp_client: MCPClient):
        super().__init__(mcp_client, "DataRetrievalAgent")
        self.keywords = ["搜索", "查找", "收集", "文件", "数据", "寻找", "定位"]

    def can_handle(self, query: str) -> bool:
        """判断是否能处理该查询"""
        return any(keyword in query for keyword in self.keywords)

    def get_description(self) -> str:
        return "数据收集专家 - 专注于文件搜索、数据收集和信息检索"

    async def research(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行数据收集任务"""
        workspace = context.get("workspace", ".")
        file_types = context.get("file_types", "all")

        try:
            # 1. 搜索相关文件
            search_results = await self.mcp_client.search_files(
                pattern=query,
                search_path=workspace
            )

            # 2. 获取文件详细信息
            detailed_results = []
            if search_results and isinstance(search_results, dict) and "result" in search_results:
                files = search_results["result"]
                if isinstance(files, list):
                    for file_info in files[:10]:  # 限制最多10个文件
                        if isinstance(file_info, dict) and "path" in file_info:
                            file_path = file_info["path"]
                            try:
                                # 获取文件内容预览
                                content_result = await self.mcp_client.read_file(file_path)
                                if content_result and isinstance(content_result, dict) and "result" in content_result:
                                    content = content_result["result"]
                                    if isinstance(content, str):
                                        preview = content[:200] + "..." if len(content) > 200 else content
                                        detailed_results.append({
                                            "path": file_path,
                                            "size": len(content),
                                            "preview": preview,
                                            "type": os.path.splitext(file_path)[1]
                                        })
                            except Exception as e:
                                logger.warning(f"无法读取文件 {file_path}: {e}")

            # 3. 按文件类型分组
            grouped_results = self._group_by_file_type(detailed_results)

            return {
                "type": "data_collection",
                "query": query,
                "workspace": workspace,
                "total_files": len(detailed_results),
                "files_by_type": grouped_results,
                "search_summary": f"在 {workspace} 中找到 {len(detailed_results)} 个相关文件"
            }

        except Exception as e:
            logger.error(f"数据收集失败: {e}")
            return {
                "type": "data_collection",
                "query": query,
                "error": str(e),
                "total_files": 0
            }

    def _group_by_file_type(self, files: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """按文件类型分组"""
        grouped = {}
        for file_info in files:
            file_type = file_info.get("type", "unknown").lower()
            if file_type not in grouped:
                grouped[file_type] = []
            grouped[file_type].append(file_info)
        return grouped


class AnalysisAgent(BaseResearcher):
    """分析Agent - 专注于代码执行和数据分析"""

    def __init__(self, mcp_client: MCPClient):
        super().__init__(mcp_client, "AnalysisAgent")
        self.keywords = ["分析", "计算", "处理", "执行", "运行", "统计", "验证"]

    def can_handle(self, query: str) -> bool:
        """判断是否能处理该查询"""
        return any(keyword in query for keyword in self.keywords)

    def get_description(self) -> str:
        return "数据分析专家 - 专注于代码执行、数据处理和统计分析"

    async def research(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行分析任务"""
        try:
            # 1. 基于查询生成分析代码
            analysis_code = self._generate_analysis_code(query)

            # 2. 执行分析代码
            execution_result = await self.mcp_client.execute_python(analysis_code)

            # 3. 解析执行结果
            if execution_result and isinstance(execution_result, dict) and "result" in execution_result:
                output = execution_result["result"]
                return {
                    "type": "analysis",
                    "query": query,
                    "analysis_code": analysis_code,
                    "output": output,
                    "analysis_summary": f"完成对'{query}'的分析"
                }
            else:
                return {
                    "type": "analysis",
                    "query": query,
                    "error": "代码执行失败",
                    "execution_result": execution_result
                }

        except Exception as e:
            logger.error(f"分析任务失败: {e}")
            return {
                "type": "analysis",
                "query": query,
                "error": str(e)
            }

    def _generate_analysis_code(self, query: str) -> str:
        """基于查询生成分析代码"""
        # 简单的模板匹配，实际项目中可以使用LLM生成代码
        if "统计" in query or "数量" in query:
            return f"""
# 分析任务: {query}
import os
import json

# 统计当前目录下的文件
files = []
for root, dirs, filenames in os.walk('.'):
    for filename in filenames:
        if filename.endswith(('.py', '.md', '.txt', '.json')):
            files.append({
                'name': filename,
                'path': os.path.join(root, filename),
                'size': os.path.getsize(os.path.join(root, filename))
            })

print(f"总文件数: {{len(files)}}")
print(f"总大小: {{sum(f['size'] for f in files)}} 字节")

# 按类型统计
by_type = {{}}
for f in files:
    ext = os.path.splitext(f['name'])[1].lower()
    if ext not in by_type:
        by_type[ext] = 0
    by_type[ext] += 1

print("按类型统计:")
for ext, count in sorted(by_type.items()):
    print(f"  {{ext}}: {{count}} 个文件")
"""

        else:
            return f"""
# 分析任务: {query}
print("开始分析...")
print(f"查询内容: {query}")
print("分析完成!")

# 这里可以添加更具体的分析逻辑
result = {{
    "query": "{query}",
    "analysis_type": "general",
    "timestamp": "{datetime.now().isoformat()}"
}}
print("分析结果:", result)
"""


class ReportAgent(BaseResearcher):
    """报告Agent - 专注于文档编写和结果整理"""

    def __init__(self, mcp_client: MCPClient):
        super().__init__(mcp_client, "ReportAgent")
        self.keywords = ["报告", "文档", "总结", "整理", "写入", "生成", "记录"]

    def can_handle(self, query: str) -> bool:
        """判断是否能处理该查询"""
        return any(keyword in query for keyword in self.keywords)

    def get_description(self) -> str:
        return "报告生成专家 - 专注于文档编写、结果整理和报告生成"

    async def research(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行报告生成任务"""
        try:
            # 1. 生成报告内容
            report_content = self._generate_report(query, context)

            # 2. 确定报告文件路径
            report_filename = self._generate_filename(query)
            report_path = f"reports/{report_filename}"

            # 3. 写入报告文件
            write_result = await self.mcp_client.write_file(
                file_path=report_path,
                content=report_content
            )

            # 4. 如果配置了Git，提交报告
            git_result = None
            if context.get("auto_commit", False):
                try:
                    git_result = await self.mcp_client.git_commit(
                        message=f"Add report: {report_filename}"
                    )
                except Exception as e:
                    logger.warning(f"Git提交失败: {e}")

            return {
                "type": "report",
                "query": query,
                "report_file": report_path,
                "report_content": report_content,
                "write_result": write_result,
                "git_result": git_result,
                "report_summary": f"已生成报告文件: {report_path}"
            }

        except Exception as e:
            logger.error(f"报告生成失败: {e}")
            return {
                "type": "report",
                "query": query,
                "error": str(e)
            }

    def _generate_report(self, query: str, context: Dict[str, Any]) -> str:
        """生成报告内容"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report = f"""# 分析报告

## 基本信息
- **原始查询**: {query}
- **生成时间**: {timestamp}
- **生成方式**: Agent自动化分析

## 执行摘要
本报告由AI Agent系统自动生成，基于对查询"{query}"的分析。

## 分析过程
1. **任务理解**: 解析用户查询意图
2. **数据收集**: 搜索相关文件和信息
3. **分析处理**: 执行相应的分析逻辑
4. **结果整理**: 生成结构化报告

## 主要发现
- 查询已成功处理
- 生成了结构化的分析报告
- 报告保存在指定位置

## 建议
1. 可以进一步细化查询以获得更精确的结果
2. 可以指定特定的分析维度或指标
3. 可以定期运行此类分析以跟踪变化

---
*此报告由 Agent 系统自动生成于 {timestamp}*
"""
        return report

    def _generate_filename(self, query: str) -> str:
        """生成报告文件名"""
        # 清理查询字符串，移除特殊字符
        safe_query = re.sub(r'[^\w\s-]', '', query).strip()
        safe_query = re.sub(r'[-\s]+', '_', safe_query)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{safe_query}_{timestamp}_report.md"


class ProjectInitAgent(BaseResearcher):
    """项目初始化Agent - 专注于项目创建和配置"""

    def __init__(self, mcp_client: MCPClient):
        super().__init__(mcp_client, "ProjectInitAgent")
        self.keywords = ["项目", "初始化", "创建", "搭建", "配置", "建立"]

    def can_handle(self, query: str) -> bool:
        """判断是否能处理该查询"""
        return any(keyword in query for keyword in self.keywords)

    def get_description(self) -> str:
        return "项目管理专家 - 专注于项目初始化、目录创建和配置管理"

    async def research(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行项目初始化任务"""
        try:
            # 1. 解析项目类型和名称
            project_info = self._parse_project_query(query)

            # 2. 使用project_initializer工具创建项目
            init_result = await self.mcp_client.call_tool(
                "project_initializer",
                project_info
            )

            # 3. 如果需要，创建额外的配置文件
            additional_files = []
            if project_info.get("include_git", True):
                readme_content = self._generate_readme(project_info)
                readme_path = f"{project_info['project_name']}/README.md"

                readme_result = await self.mcp_client.write_file(
                    file_path=readme_path,
                    content=readme_content
                )
                additional_files.append(readme_result)

            return {
                "type": "project_init",
                "query": query,
                "project_info": project_info,
                "init_result": init_result,
                "additional_files": additional_files,
                "project_summary": f"已创建项目: {project_info['project_name']}"
            }

        except Exception as e:
            logger.error(f"项目初始化失败: {e}")
            return {
                "type": "project_init",
                "query": query,
                "error": str(e)
            }

    def _parse_project_query(self, query: str) -> Dict[str, Any]:
        """解析项目查询"""
        # 简单的解析逻辑，实际项目中可以更智能
        project_info = {
            "project_name": "new_project",
            "project_type": "python",
            "base_path": ".",
            "include_git": True,
            "include_readme": True
        }

        # 检测项目类型
        if "node" in query.lower() or "js" in query.lower() or "javascript" in query.lower():
            project_info["project_type"] = "nodejs"
        elif "web" in query.lower() or "html" in query.lower():
            project_info["project_type"] = "web"
        elif "api" in query.lower():
            project_info["project_type"] = "api"

        # 尝试提取项目名称
        words = query.split()
        for i, word in enumerate(words):
            if word in ["项目", "project"] and i + 1 < len(words):
                project_info["project_name"] = words[i + 1]
                break

        return project_info

    def _generate_readme(self, project_info: Dict[str, Any]) -> str:
        """生成README文件"""
        project_name = project_info["project_name"]
        project_type = project_info["project_type"]
        timestamp = datetime.now().strftime("%Y-%m-%d")

        return f"""# {project_name}

## 项目简介
这是一个由Agent系统自动创建的{project_type}项目。

## 创建信息
- **项目名称**: {project_name}
- **项目类型**: {project_type}
- **创建时间**: {timestamp}
- **创建方式**: AI Agent自动化创建

## 项目结构
```
{project_name}/
├── README.md
├── .git/
└── [其他项目文件]
```

## 快速开始
1. 克隆或下载项目
2. 根据项目类型进行相应配置
3. 开始开发

## 说明
此项目由AI Agent系统基于用户需求自动创建。如需修改或扩展，请根据实际需求进行调整。

---
*创建时间: {timestamp}*
"""