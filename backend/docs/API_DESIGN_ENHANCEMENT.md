# Open Deep Research API 设计增强

## 🎯 设计理念

基于深度研究的特点，设计一个支持：
- **流式进度输出**：实时显示研究步骤
- **可下载报告**：生成PDF/Word格式的专业报告
- **状态持久化**：支持长时间运行的任务
- **断点续传**：支持任务恢复

## 📋 接口设计方案

### 1. **创建研究任务** - 流式输出

```http
POST /api/enhanced-research/generate
Content-Type: application/json
Accept: text/event-stream

{
  "question": "分析人工智能在教育领域的应用前景",
  "allow_clarification": false,
  "research_depth": "comprehensive",
  "output_format": ["json", "pdf", "docx"],  // 新增：输出格式
  "stream_progress": true,
  "save_report": true,  // 新增：是否保存报告
  "report_settings": {  // 新增：报告设置
    "language": "zh-CN",
    "template": "professional",
    "include_sources": true,
    "max_pages": 50
  }
}
```

**流式响应示例**：
```
data: {"type": "progress", "stage": "initializing", "message": "⚡ 正在初始化研究系统", "progress": 5, "timestamp": "2024-12-01T14:30:22Z"}

data: {"type": "progress", "stage": "clarifying", "message": "❓ 正在分析问题清晰度", "progress": 15, "timestamp": "2024-12-01T14:30:25Z"}

data: {"type": "progress", "stage": "planning", "message": "📋 正在制定研究计划", "progress": 25, "timestamp": "2024-12-01T14:30:28Z"}

data: {"type": "research_start", "stage": "researching", "message": "🔍 开始并行研究任务", "progress": 30, "timestamp": "2024-12-01T14:30:30Z"}

data: {"type": "research_task", "task_id": "task_1", "topic": "AI教育应用现状", "status": "started", "progress": 35, "timestamp": "2024-12-01T14:30:32Z"}

data: {"type": "research_task", "task_id": "task_2", "topic": "AI教育技术趋势", "status": "started", "progress": 40, "timestamp": "2024-12-01T14:30:35Z"}

data: {"type": "research_task", "task_id": "task_1", "status": "completed", "findings_count": 8, "progress": 60, "timestamp": "2024-12-01T14:31:15Z"}

data: {"type": "research_task", "task_id": "task_2", "status": "completed", "findings_count": 12, "progress": 80, "timestamp": "2024-12-01T14:31:45Z"}

data: {"type": "progress", "stage": "writing", "message": "📝 正在生成研究报告", "progress": 90, "timestamp": "2024-12-01T14:32:00Z"}

data: {"type": "report_generation", "format": "pdf", "status": "generating", "progress": 95, "timestamp": "2024-12-01T14:32:15Z"}

data: {"type": "complete", "stage": "completed", "message": "✅ 研究报告生成完成", "progress": 100, "research_id": "enh_research_20241201_143022_1234", "report_urls": {"pdf": "/api/reports/download/1234.pdf", "docx": "/api/reports/download/1234.docx"}, "timestamp": "2024-12-01T14:32:30Z"}
```

### 2. **获取研究状态** - 详细信息

```http
GET /api/enhanced-research/status/{research_id}
```

**响应示例**：
```json
{
  "research_id": "enh_research_20241201_143022_1234",
  "question": "分析人工智能在教育领域的应用前景",
  "status": "completed",
  "progress": 100.0,
  "current_stage": "completed",
  "stages_completed": [
    {
      "stage": "initializing",
      "completed_at": "2024-12-01T14:30:22Z",
      "duration": 3.2
    },
    {
      "stage": "clarifying", 
      "completed_at": "2024-12-01T14:30:25Z",
      "duration": 3.0
    },
    {
      "stage": "planning",
      "completed_at": "2024-12-01T14:30:28Z", 
      "duration": 2.5
    },
    {
      "stage": "researching",
      "completed_at": "2024-12-01T14:31:45Z",
      "duration": 77.0,
      "tasks": [
        {
          "task_id": "task_1",
          "topic": "AI教育应用现状",
          "status": "completed",
          "findings_count": 8,
          "duration": 43.2
        },
        {
          "task_id": "task_2", 
          "topic": "AI教育技术趋势",
          "status": "completed",
          "findings_count": 12,
          "duration": 70.5
        }
      ]
    },
    {
      "stage": "writing",
      "completed_at": "2024-12-01T14:32:30Z",
      "duration": 45.0
    }
  ],
  "total_duration": 128.7,
  "key_findings_count": 20,
  "report_urls": {
    "pdf": "/api/reports/download/1234.pdf",
    "docx": "/api/reports/download/1234.docx",
    "json": "/api/reports/download/1234.json"
  },
  "created_at": "2024-12-01T14:30:22Z",
  "updated_at": "2024-12-01T14:32:30Z"
}
```

### 3. **下载报告** - 多格式支持

```http
GET /api/reports/download/{research_id}.{format}
```

**支持格式**：
- `pdf` - PDF格式报告
- `docx` - Word文档
- `html` - HTML格式
- `json` - 结构化数据
- `txt` - 纯文本

**响应头**：
```
Content-Type: application/pdf
Content-Disposition: attachment; filename="AI教育应用前景分析_20241201.pdf"
Content-Length: 2048576
```

### 4. **获取研究详情** - 包含所有数据

```http
GET /api/enhanced-research/detail/{research_id}
```

**响应示例**：
```json
{
  "research_id": "enh_research_20241201_143022_1234",
  "question": "分析人工智能在教育领域的应用前景",
  "status": "completed",
  "final_report": "# 人工智能在教育领域的应用前景分析\n\n## 执行摘要\n...",
  "research_brief": "深入研究人工智能技术在教育领域的当前应用状况、发展趋势、技术挑战和未来前景...",
  "key_findings": [
    "个性化学习是AI教育的主要优势",
    "智能辅导系统正在快速发展", 
    "数据隐私是重要挑战"
  ],
  "research_tasks": [
    {
      "task_id": "task_1",
      "topic": "AI教育应用现状",
      "status": "completed",
      "findings": ["发现1", "发现2", "发现3"],
      "sources": [
        {
          "title": "AI教育应用报告2024",
          "url": "https://example.com/report",
          "relevance_score": 0.95
        }
      ],
      "duration": 43.2
    }
  ],
  "sources": [
    {
      "title": "AI教育应用报告2024",
      "url": "https://example.com/report", 
      "type": "report",
      "relevance_score": 0.95,
      "used_in_tasks": ["task_1", "task_2"]
    }
  ],
  "metadata": {
    "total_sources": 15,
    "high_quality_sources": 12,
    "research_depth": "comprehensive",
    "language": "zh-CN",
    "estimated_reading_time": "25分钟"
  },
  "quality_metrics": {
    "overall_score": 95.5,
    "completeness_score": 92.0,
    "accuracy_score": 98.0,
    "clarity_score": 96.0,
    "source_quality_score": 94.0
  },
  "report_urls": {
    "pdf": "/api/reports/download/1234.pdf",
    "docx": "/api/reports/download/1234.docx",
    "html": "/api/reports/download/1234.html",
    "json": "/api/reports/download/1234.json"
  },
  "created_at": "2024-12-01T14:30:22Z",
  "completed_at": "2024-12-01T14:32:30Z"
}
```

### 5. **获取研究历史** - 分页支持

```http
GET /api/enhanced-research/history?page=1&limit=10&status=completed
```

**查询参数**：
- `page` - 页码
- `limit` - 每页数量
- `status` - 状态筛选
- `date_from` - 开始日期
- `date_to` - 结束日期
- `search` - 关键词搜索

### 6. **报告模板管理**

```http
GET /api/reports/templates
POST /api/reports/templates
PUT /api/reports/templates/{template_id}
DELETE /api/reports/templates/{template_id}
```

## 🏗️ 实现架构

### 1. **后端架构**

```
enhanced_research_router.py
├── /generate (流式输出)
├── /status/{id} (状态查询)
├── /detail/{id} (详细信息)
├── /history (历史列表)
└── /download/{id}.{format} (报告下载)

report_service.py
├── PDF生成器
├── Word生成器  
├── HTML生成器
└── 模板管理器

file_storage.py
├── 本地存储
├── 云存储集成
└── CDN分发
```

### 2. **前端组件**

```
ResearchInterface.vue
├── 问题输入组件
├── 流式进度显示
├── 实时状态更新
└── 报告下载按钮

ProgressStream.vue
├── 阶段进度条
├── 任务列表
├── 实时日志
└── 错误处理

ReportViewer.vue
├── PDF预览
├── 多格式切换
├── 下载管理
└── 分享功能
```

## 📊 数据库设计

### 研究任务表
```sql
CREATE TABLE research_tasks (
    id VARCHAR(50) PRIMARY KEY,
    question TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    progress FLOAT DEFAULT 0.0,
    current_stage VARCHAR(50),
    research_brief TEXT,
    final_report TEXT,
    key_findings JSON,
    sources JSON,
    metadata JSON,
    report_urls JSON,
    quality_metrics JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

### 研究阶段表
```sql
CREATE TABLE research_stages (
    id SERIAL PRIMARY KEY,
    research_id VARCHAR(50) REFERENCES research_tasks(id),
    stage_name VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration FLOAT,
    details JSON
);
```

### 研究任务子表
```sql
CREATE TABLE research_subtasks (
    id SERIAL PRIMARY KEY,
    research_id VARCHAR(50) REFERENCES research_tasks(id),
    task_id VARCHAR(50) NOT NULL,
    topic VARCHAR(200) NOT NULL,
    status VARCHAR(20) NOT NULL,
    findings JSON,
    sources JSON,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration FLOAT
);
```

## 🚀 部署建议

### 1. **文件存储**
- 本地存储：开发环境
- AWS S3/MinIO：生产环境
- CDN：全球加速

### 2. **缓存策略**
- Redis：任务状态缓存
- 文件缓存：报告文件
- CDN缓存：静态资源

### 3. **监控告警**
- 任务执行时间监控
- 错误率监控
- 存储空间监控
- 用户下载统计

这个设计提供了完整的用户体验，支持实时进度、多格式报告下载和详细的任务管理！
