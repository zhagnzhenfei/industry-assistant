# LLM模型配置说明

## 🔄 支持的模型服务

Text2SQL智能体支持所有**OpenAI兼容**的API服务，只需配置环境变量即可切换。

---

## ⚙️ 快速切换

### 方式1：阿里云通义千问（默认）

```bash
export DASHSCOPE_API_KEY=sk-your-dashscope-key
export DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
export TEXT2SQL_MODEL=qwen-plus
```

**推荐模型**:
- `qwen-plus` - 性价比高
- `qwen-max` - 最强性能
- `qwen-turbo` - 速度快

### 方式2：硅基流动（SiliconFlow）

```bash
export DASHSCOPE_API_KEY=sk-your-siliconflow-key
export DASHSCOPE_BASE_URL=https://api.siliconflow.cn/v1
export TEXT2SQL_MODEL=Qwen/Qwen2.5-7B-Instruct
```

**推荐模型**:
- `Qwen/Qwen2.5-7B-Instruct` - 轻量快速
- `Qwen/Qwen2.5-14B-Instruct` - 平衡性能
- `deepseek-ai/DeepSeek-V2.5` - 代码能力强

### 方式3：其他OpenAI兼容服务

```bash
export DASHSCOPE_API_KEY=your-api-key
export DASHSCOPE_BASE_URL=https://your-service.com/v1
export TEXT2SQL_MODEL=your-model-name
```

---

## 📋 环境变量优先级

### 模型名称

```
TEXT2SQL_MODEL (最高)
  ↓ 如果未设置
LLM_MODEL
  ↓ 如果未设置
"qwen-plus" (默认)
```

### API密钥

```
DASHSCOPE_API_KEY (推荐)
  ↓ 如果未设置
OPENAI_API_KEY
```

### API基础URL

```
DASHSCOPE_BASE_URL (环境变量)
  ↓ 如果未设置
"https://dashscope.aliyuncs.com/compatible-mode/v1" (默认)
```

---

## 🧪 测试不同模型

### 测试阿里云通义千问

```bash
export DASHSCOPE_API_KEY=sk-xxx
export DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
export TEXT2SQL_MODEL=qwen-plus

python scripts/test_text2sql_basic.py
```

### 测试硅基流动

```bash
export DASHSCOPE_API_KEY=sk-xxx  # 硅基流动的key
export DASHSCOPE_BASE_URL=https://api.siliconflow.cn/v1
export TEXT2SQL_MODEL=Qwen/Qwen2.5-7B-Instruct

python scripts/test_text2sql_basic.py
```

---

## ✅ 兼容性说明

Text2SQL使用标准的OpenAI Chat Completions API，支持：

- ✅ `/v1/chat/completions` endpoint
- ✅ `messages` 参数（system/user/assistant）
- ✅ `tools` 参数（工具调用）
- ✅ 标准的响应格式

**理论上支持所有OpenAI兼容的API服务！**

---

## 💡 选择建议

### 按场景选择

| 场景 | 推荐服务 | 推荐模型 | 原因 |
|------|----------|----------|------|
| 生产环境 | 阿里云 | qwen-plus | 稳定、性价比高 |
| 开发测试 | 硅基流动 | Qwen2.5-7B | 便宜、快速 |
| 高准确率 | 阿里云 | qwen-max | 最强性能 |
| 代码理解 | 硅基流动 | DeepSeek-V2.5 | 代码能力强 |

### 按成本选择

| 服务 | 相对成本 | 优势 |
|------|---------|------|
| 硅基流动 | 低 | 开源模型，价格实惠 |
| 阿里云 | 中 | 稳定性好，有SLA |
| OpenAI | 高 | 性能最强 |

---

## 🔧 Docker环境配置

在`docker-compose.yml`中设置：

```yaml
app:
  environment:
    - DASHSCOPE_API_KEY=sk-xxx
    - DASHSCOPE_BASE_URL=https://api.siliconflow.cn/v1
    - TEXT2SQL_MODEL=Qwen/Qwen2.5-7B-Instruct
```

---

## 🎯 验证配置

```python
# 在Python中检查当前配置
import os

print(f"API Key: {os.getenv('DASHSCOPE_API_KEY')[:10]}...")
print(f"Base URL: {os.getenv('DASHSCOPE_BASE_URL')}")
print(f"Model: {os.getenv('TEXT2SQL_MODEL') or os.getenv('LLM_MODEL') or 'qwen-plus'}")
```

---

## 📝 代码示例

不需要修改任何代码！Text2SQL会自动使用配置的模型：

```python
from app.services.agent_orchestration.text2sql_tool import query_database

# 自动使用TEXT2SQL_MODEL环境变量中的模型
result = await query_database("数据库中有多少家公司？")
```

---

**切换模型只需要改环境变量，无需修改代码！** ✅

