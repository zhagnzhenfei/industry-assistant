# 日志配置指南

> 版本：v1.0  
> 日期：2025-10-08

## 📋 概述

系统支持通过环境变量配置日志级别，以控制输出的详细程度。

---

## 🎯 日志级别

### 支持的级别

| 级别 | 用途 | 输出内容 |
|-----|------|---------|
| `DEBUG` | 开发调试 | 所有详细信息，包括事件数据、工具输入输出、状态变化 |
| `INFO` | 正常运行 | 关键进度信息、工具调用、节点执行 |
| `WARNING` | 警告信息 | 异常情况、性能问题 |
| `ERROR` | 错误信息 | 失败和异常 |

### 默认级别

- **默认**: `INFO`
- 生产环境推荐：`INFO` 或 `WARNING`
- 开发调试推荐：`DEBUG`

---

## ⚙️ 配置方式

### 方式 1: 环境变量

```bash
# 临时设置（当前会话）
export LOG_LEVEL=DEBUG

# 永久设置（添加到 ~/.bashrc）
echo 'export LOG_LEVEL=DEBUG' >> ~/.bashrc
source ~/.bashrc
```

### 方式 2: .env 文件

创建 `.env` 文件：

```bash
# .env
LOG_LEVEL=DEBUG
DASHSCOPE_API_KEY=your-key-here
SERPER_API_KEY=your-key-here
```

### 方式 3: Docker Compose

```yaml
# docker-compose.yml
services:
  app:
    environment:
      - LOG_LEVEL=DEBUG
```

---

## 📊 日志输出示例

### INFO 级别（简洁）

```
2025-10-08 18:30:00 [INFO] [enh_research_202510...] 20.0% | 🚀 开始执行研究流程
2025-10-08 18:30:01 [INFO] [enh_research_202510...] 22.0% | 🤔 检查问题是否需要澄清
2025-10-08 18:30:05 [INFO] [enh_research_202510...] 26.0% | 📝 规划研究策略
2025-10-08 18:30:10 [INFO] [TOOL] 🤔 思考工具 | 反思: 需要从多个角度研究
2025-10-08 18:30:15 [INFO] [TOOL] 🚀 委托研究 | 主题: AI技术演进
2025-10-08 18:30:20 [INFO] [TOOL] 🔍 搜索工具: serper_search_tool | 查询: AI技术演进
2025-10-08 18:30:30 [INFO] [TOOL] ✅ 工具完成: serper_search_tool | 输出长度: 2500
```

### DEBUG 级别（详细）

```
2025-10-08 18:30:00 [INFO] [enh_research_202510...] 20.0% | 🚀 开始执行研究流程
2025-10-08 18:30:00 [DEBUG] [PROGRESS_DETAIL] Stage: researching
2025-10-08 18:30:00 [DEBUG] [PROGRESS_DETAIL] Data: {'type': 'progress', 'stage': 'researching', ...}

2025-10-08 18:30:01 [INFO] [enh_research_202510...] 22.0% | 🤔 检查问题是否需要澄清
2025-10-08 18:30:01 [DEBUG] [EVENT] on_chain_start | clarify_with_user
2025-10-08 18:30:01 [DEBUG] [EVENT_DATA] {'event': 'on_chain_start', 'name': 'clarify_with_user', ...}

2025-10-08 18:30:10 [INFO] [TOOL] 🤔 思考工具 | 反思: 需要从多个角度研究
2025-10-08 18:30:10 [DEBUG] [TOOL_START] Tool: think_tool
2025-10-08 18:30:10 [DEBUG] [TOOL_INPUT] {'reflection': '需要从多个角度研究...'}

2025-10-08 18:30:15 [INFO] [TOOL] 🚀 委托研究 | 主题: AI技术演进
2025-10-08 18:30:15 [DEBUG] [TOOL_START] Tool: ConductResearch
2025-10-08 18:30:15 [DEBUG] [TOOL_INPUT] {'research_topic': 'AI技术演进：从规则系统到深度学习'}

2025-10-08 18:30:20 [INFO] [TOOL] 🔍 搜索工具: serper_search_tool | 查询: AI技术演进
2025-10-08 18:30:20 [DEBUG] [TOOL_START] Tool: serper_search_tool
2025-10-08 18:30:20 [DEBUG] [TOOL_INPUT] {'query': 'AI技术演进：从规则系统到深度学习'}

2025-10-08 18:30:30 [INFO] [TOOL] ✅ 工具完成: serper_search_tool | 输出长度: 2500
2025-10-08 18:30:30 [DEBUG] [TOOL_END] Tool: serper_search_tool
2025-10-08 18:30:30 [DEBUG] [TOOL_OUTPUT] 搜索结果1: AI技术演进概述...
```

---

## 🔧 实际使用场景

### 场景 1: 日常开发

```bash
# 使用 INFO 级别，查看关键进度
export LOG_LEVEL=INFO
python test_progress_stream.py
```

### 场景 2: 调试新工具

```bash
# 使用 DEBUG 级别，查看完整的工具调用过程
export LOG_LEVEL=DEBUG
python test_progress_stream.py

# 输出会包含：
# - 完整的事件数据
# - 工具输入参数
# - 工具输出结果
# - 状态变化详情
```

### 场景 3: 生产环境

```bash
# 使用 WARNING 级别，只看异常
export LOG_LEVEL=WARNING
uvicorn app.app_main:app --host 0.0.0.0 --port 8000
```

### 场景 4: 追踪特定问题

```bash
# 临时开启 DEBUG，追踪问题
export LOG_LEVEL=DEBUG
curl -N http://localhost:8000/api/enhanced-research/generate \
  -H "Content-Type: application/json" \
  -d '{"question": "测试问题"}'
```

---

## 📝 日志标签说明

### 标签类型

| 标签 | 含义 | 示例 |
|-----|------|------|
| `[research_id]` | 研究任务ID | `[enh_research_20251008...]` |
| `[EVENT]` | LangGraph 事件 | `[EVENT] on_chain_start` |
| `[EVENT_DATA]` | 事件详细数据 | `[EVENT_DATA] {...}` |
| `[TOOL]` | 工具调用 | `[TOOL] 🔍 搜索工具` |
| `[TOOL_START]` | 工具开始 | `[TOOL_START] Tool: serper_search_tool` |
| `[TOOL_INPUT]` | 工具输入 | `[TOOL_INPUT] {'query': '...'}` |
| `[TOOL_END]` | 工具完成 | `[TOOL_END] Tool: serper_search_tool` |
| `[TOOL_OUTPUT]` | 工具输出 | `[TOOL_OUTPUT] 搜索结果...` |
| `[PROGRESS_DETAIL]` | 进度详情 | `[PROGRESS_DETAIL] Stage: researching` |

### 进度百分比格式

```
[research_id] 进度% | 消息
[enh_research_202510...]  45.2% | 🔬 研究单元1：开始研究
```

---

## 🎯 新增接口返回字段

### 进度数据结构（已优化）

```json
{
  "type": "progress",
  "stage": "searching",
  "progress": 45.2,
  "message": "🔍 调用搜索工具",
  "details": "工具: serper_search_tool\n查询: AI技术演进",
  
  // 👇 新增字段：当前工具信息
  "current_tool": "serper_search_tool",
  "tool_input": "AI技术演进",
  
  "metadata": {
    "tool": "serper_search_tool",
    "event": "tool_start",
    "input": {"query": "AI技术演进"}
  }
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|-----|------|------|
| `current_tool` | string | 当前正在执行的工具名称（如果有） |
| `tool_input` | string | 工具的输入参数（简化版） |
| `metadata.input` | object | 工具的完整输入参数 |

### 前端使用示例

```javascript
// 监听 SSE 流
const eventSource = new EventSource('/api/enhanced-research/generate');

eventSource.addEventListener('message', (event) => {
  const data = JSON.parse(event.data);
  
  // 显示进度
  updateProgress(data.progress);
  
  // 显示消息
  updateMessage(data.message);
  
  // 👇 新增：显示当前工具
  if (data.current_tool) {
    updateToolStatus({
      tool: data.current_tool,
      input: data.tool_input,
      status: 'running'
    });
  }
});
```

---

## 🐛 日志问题排查

### 问题 1: 日志重复

**症状**: 每条日志输出两次

**原因**: logger 设置了 `propagate=True`，日志向上传播

**解决**: 已在代码中添加 `logger.propagate = False`

### 问题 2: 日志太少

**症状**: 看不到详细的调试信息

**解决**: 设置 `LOG_LEVEL=DEBUG`

```bash
export LOG_LEVEL=DEBUG
```

### 问题 3: 日志太多

**症状**: 输出信息过于详细，影响阅读

**解决**: 调整为 `LOG_LEVEL=INFO` 或 `LOG_LEVEL=WARNING`

```bash
export LOG_LEVEL=INFO
```

### 问题 4: 日志级别不生效

**原因**: 环境变量未正确设置或被覆盖

**检查**:

```bash
# 检查当前设置
echo $LOG_LEVEL

# 重新设置
export LOG_LEVEL=DEBUG

# 验证
python -c "import os; print(os.getenv('LOG_LEVEL'))"
```

---

## 📚 相关文件

| 文件 | 修改 |
|-----|------|
| `app/services/agent_orchestration/odr_orchestrator.py` | 添加日志配置和详细日志 |
| `app/services/research_service.py` | 添加日志配置和简化日志 |
| `app/services/agent_orchestration/odr_main.py` | 可能需要检查日志配置 |
| `app/services/agent_orchestration/odr_supervisor.py` | 可能需要检查日志配置 |

---

## ✅ 最佳实践

### 开发环境

```bash
# 开发时使用 DEBUG，查看所有详情
export LOG_LEVEL=DEBUG
export DASHSCOPE_API_KEY=xxx
export SERPER_API_KEY=xxx

# 运行测试
python test_progress_stream.py
```

### 生产环境

```bash
# 生产时使用 INFO，只看关键信息
export LOG_LEVEL=INFO

# 启动服务
uvicorn app.app_main:app --host 0.0.0.0 --port 8000
```

### CI/CD 环境

```bash
# CI/CD 时使用 WARNING，只看错误
export LOG_LEVEL=WARNING

# 运行测试
pytest tests/
```

---

## 🎉 总结

### 改进点

1. ✅ **日志不再重复** - 添加 `logger.propagate = False`
2. ✅ **支持日志级别控制** - 通过 `LOG_LEVEL` 环境变量
3. ✅ **INFO 级别简洁** - 只显示关键进度信息
4. ✅ **DEBUG 级别详细** - 显示完整的事件数据和工具信息
5. ✅ **统一日志格式** - 使用清晰的标签和格式
6. ✅ **新增工具信息** - 接口返回包含 `current_tool` 和 `tool_input`

### 下一步

- [ ] 测试不同日志级别的输出
- [ ] 前端集成新的工具信息字段
- [ ] 根据实际使用调整日志格式

---

*文档版本: v1.0*  
*创建时间: 2025-10-08*

