# 前端组件实现示例

## 🎯 组件设计

### 1. **研究界面主组件** (`ResearchInterface.vue`)

```vue
<template>
  <div class="research-interface">
    <!-- 问题输入区域 -->
    <div class="question-input">
      <h2>深度研究系统</h2>
      <textarea
        v-model="question"
        placeholder="请输入您想要研究的问题..."
        rows="4"
        :disabled="isResearching"
      ></textarea>
      
      <!-- 研究选项 -->
      <div class="research-options">
        <label>
          <input type="checkbox" v-model="allowClarification">
          允许澄清问题
        </label>
        <select v-model="researchDepth">
          <option value="basic">基础研究</option>
          <option value="standard">标准研究</option>
          <option value="comprehensive">综合研究</option>
        </select>
        <div class="output-formats">
          <label>输出格式:</label>
          <label v-for="format in outputFormats" :key="format">
            <input type="checkbox" :value="format" v-model="selectedFormats">
            {{ format.toUpperCase() }}
          </label>
        </div>
      </div>
      
      <!-- 开始按钮 -->
      <button 
        @click="startResearch" 
        :disabled="!question.trim() || isResearching"
        class="start-btn"
      >
        {{ isResearching ? '研究中...' : '开始研究' }}
      </button>
    </div>

    <!-- 进度显示区域 -->
    <div v-if="isResearching || researchResult" class="progress-area">
      <ProgressStream 
        :progress-data="progressData"
        :research-tasks="researchTasks"
        :current-stage="currentStage"
        :is-completed="isCompleted"
      />
    </div>

    <!-- 结果展示区域 -->
    <div v-if="researchResult && isCompleted" class="result-area">
      <ReportViewer 
        :research-result="researchResult"
        :report-urls="reportUrls"
        @download="downloadReport"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import ProgressStream from './ProgressStream.vue'
import ReportViewer from './ReportViewer.vue'

// 响应式数据
const question = ref('')
const allowClarification = ref(false)
const researchDepth = ref('comprehensive')
const selectedFormats = ref(['json', 'pdf'])
const outputFormats = ['json', 'pdf', 'docx', 'html', 'txt']

const isResearching = ref(false)
const isCompleted = ref(false)
const researchId = ref('')
const progressData = ref({})
const researchTasks = ref([])
const currentStage = ref('')
const researchResult = ref(null)
const reportUrls = ref({})

// EventSource 连接
let eventSource = null

// 开始研究
const startResearch = async () => {
  try {
    isResearching.value = true
    isCompleted.value = false
    progressData.value = {}
    researchTasks.value = []
    researchResult.value = null
    
    const response = await fetch('/api/enhanced-research/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream'
      },
      body: JSON.stringify({
        question: question.value,
        allow_clarification: allowClarification.value,
        research_depth: researchDepth.value,
        output_format: selectedFormats.value,
        save_report: true,
        stream_progress: true
      })
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    // 创建 EventSource 连接
    eventSource = new EventSource('/api/enhanced-research/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        question: question.value,
        allow_clarification: allowClarification.value,
        research_depth: researchDepth.value,
        output_format: selectedFormats.value,
        save_report: true,
        stream_progress: true
      })
    })

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleProgressUpdate(data)
      } catch (error) {
        console.error('解析进度数据失败:', error)
      }
    }

    eventSource.onerror = (error) => {
      console.error('EventSource 连接错误:', error)
      eventSource.close()
      isResearching.value = false
    }

  } catch (error) {
    console.error('启动研究失败:', error)
    isResearching.value = false
  }
}

// 处理进度更新
const handleProgressUpdate = (data) => {
  console.log('收到进度更新:', data)
  
  switch (data.type) {
    case 'progress':
      progressData.value = data
      currentStage.value = data.stage
      if (data.research_tasks) {
        researchTasks.value = data.research_tasks
      }
      break
      
    case 'research_task':
      updateResearchTask(data)
      break
      
    case 'complete':
      isResearching.value = false
      isCompleted.value = true
      researchId.value = data.research_id
      reportUrls.value = data.report_urls || {}
      researchResult.value = data
      eventSource.close()
      break
      
    case 'error':
      console.error('研究错误:', data.message)
      isResearching.value = false
      eventSource.close()
      break
      
    case 'timeout':
      console.warn('研究超时:', data.message)
      isResearching.value = false
      eventSource.close()
      break
  }
}

// 更新研究任务状态
const updateResearchTask = (taskData) => {
  const existingTaskIndex = researchTasks.value.findIndex(task => task.task_id === taskData.task_id)
  
  if (existingTaskIndex >= 0) {
    researchTasks.value[existingTaskIndex] = {
      ...researchTasks.value[existingTaskIndex],
      ...taskData
    }
  } else {
    researchTasks.value.push(taskData)
  }
}

// 下载报告
const downloadReport = async (format) => {
  try {
    const url = reportUrls.value[format]
    if (!url) {
      console.error('报告URL不存在:', format)
      return
    }
    
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`下载失败: ${response.status}`)
    }
    
    const blob = await response.blob()
    const downloadUrl = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = downloadUrl
    link.download = `${researchId.value}.${format}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(downloadUrl)
    
  } catch (error) {
    console.error('下载报告失败:', error)
  }
}

// 清理资源
onUnmounted(() => {
  if (eventSource) {
    eventSource.close()
  }
})
</script>

<style scoped>
.research-interface {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.question-input {
  background: white;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
}

.question-input h2 {
  color: #2563eb;
  margin-bottom: 20px;
  font-size: 28px;
}

.question-input textarea {
  width: 100%;
  padding: 15px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  font-size: 16px;
  resize: vertical;
  margin-bottom: 20px;
}

.question-input textarea:focus {
  outline: none;
  border-color: #2563eb;
}

.research-options {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  align-items: center;
  margin-bottom: 20px;
  padding: 15px;
  background: #f9fafb;
  border-radius: 8px;
}

.research-options label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.research-options select {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
}

.output-formats {
  display: flex;
  align-items: center;
  gap: 10px;
}

.start-btn {
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  color: white;
  border: none;
  padding: 15px 30px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.start-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #1d4ed8, #1e40af);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}

.start-btn:disabled {
  background: #9ca3af;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.progress-area {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
}

.result-area {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
</style>
```

### 2. **进度流组件** (`ProgressStream.vue`)

```vue
<template>
  <div class="progress-stream">
    <!-- 总体进度条 -->
    <div class="overall-progress">
      <div class="progress-header">
        <h3>{{ currentStageMessage }}</h3>
        <span class="progress-percentage">{{ Math.round(progressData.progress || 0) }}%</span>
      </div>
      <div class="progress-bar">
        <div 
          class="progress-fill" 
          :style="{ width: `${progressData.progress || 0}%` }"
        ></div>
      </div>
    </div>

    <!-- 阶段列表 -->
    <div class="stages-list">
      <div 
        v-for="stage in stages" 
        :key="stage.name"
        class="stage-item"
        :class="{ 
          'completed': stage.completed, 
          'current': stage.current,
          'pending': !stage.completed && !stage.current 
        }"
      >
        <div class="stage-icon">
          <i v-if="stage.completed" class="icon-check">✓</i>
          <i v-else-if="stage.current" class="icon-loading">⟳</i>
          <i v-else class="icon-pending">○</i>
        </div>
        <div class="stage-content">
          <div class="stage-name">{{ stage.displayName }}</div>
          <div class="stage-message">{{ stage.message }}</div>
          <div v-if="stage.duration" class="stage-duration">
            耗时: {{ formatDuration(stage.duration) }}
          </div>
        </div>
      </div>
    </div>

    <!-- 研究任务列表 -->
    <div v-if="researchTasks.length > 0" class="research-tasks">
      <h4>研究任务</h4>
      <div class="tasks-list">
        <div 
          v-for="task in researchTasks" 
          :key="task.task_id"
          class="task-item"
          :class="{ 
            'completed': task.status === 'completed',
            'in-progress': task.status === 'started',
            'pending': task.status === 'pending'
          }"
        >
          <div class="task-icon">
            <i v-if="task.status === 'completed'" class="icon-check">✓</i>
            <i v-else-if="task.status === 'started'" class="icon-loading">⟳</i>
            <i v-else class="icon-pending">○</i>
          </div>
          <div class="task-content">
            <div class="task-topic">{{ task.topic }}</div>
            <div v-if="task.findings_count" class="task-findings">
              发现 {{ task.findings_count }} 条信息
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 实时日志 -->
    <div class="realtime-log">
      <h4>实时日志</h4>
      <div class="log-container">
        <div 
          v-for="log in logs" 
          :key="log.id"
          class="log-item"
          :class="log.type"
        >
          <span class="log-time">{{ formatTime(log.timestamp) }}</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  progressData: {
    type: Object,
    default: () => ({})
  },
  researchTasks: {
    type: Array,
    default: () => []
  },
  currentStage: {
    type: String,
    default: ''
  },
  isCompleted: {
    type: Boolean,
    default: false
  }
})

const logs = ref([])

// 阶段配置
const stageConfig = {
  'initializing': { displayName: '初始化', message: '正在初始化研究系统', icon: '⚡' },
  'clarifying': { displayName: '问题澄清', message: '正在分析问题清晰度', icon: '❓' },
  'planning': { displayName: '研究规划', message: '正在制定研究计划', icon: '📋' },
  'researching': { displayName: '数据收集', message: '正在收集和分析数据', icon: '🔍' },
  'writing': { displayName: '报告生成', message: '正在生成研究报告', icon: '📝' },
  'completed': { displayName: '完成', message: '研究报告生成完成', icon: '✅' },
  'failed': { displayName: '失败', message: '研究任务失败', icon: '❌' }
}

// 计算当前阶段消息
const currentStageMessage = computed(() => {
  const config = stageConfig[props.currentStage]
  return config ? config.message : props.currentStage
})

// 计算阶段列表
const stages = computed(() => {
  const stageOrder = ['initializing', 'clarifying', 'planning', 'researching', 'writing', 'completed']
  return stageOrder.map(stageName => {
    const config = stageConfig[stageName]
    const isCompleted = props.progressData.stages_completed?.some(s => s.stage_name === stageName && s.status === 'completed')
    const isCurrent = props.currentStage === stageName && !isCompleted
    
    return {
      name: stageName,
      displayName: config?.displayName || stageName,
      message: config?.message || '',
      icon: config?.icon || '○',
      completed: isCompleted,
      current: isCurrent,
      duration: props.progressData.stages_completed?.find(s => s.stage_name === stageName)?.duration
    }
  })
})

// 监听进度数据变化，添加日志
watch(() => props.progressData, (newData) => {
  if (newData && newData.message) {
    logs.value.unshift({
      id: Date.now(),
      type: 'info',
      message: newData.message,
      timestamp: newData.timestamp || new Date().toISOString()
    })
    
    // 限制日志数量
    if (logs.value.length > 50) {
      logs.value = logs.value.slice(0, 50)
    }
  }
}, { deep: true })

// 格式化持续时间
const formatDuration = (seconds) => {
  if (seconds < 60) {
    return `${seconds.toFixed(1)}秒`
  } else {
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}分${remainingSeconds.toFixed(0)}秒`
  }
}

// 格式化时间
const formatTime = (timestamp) => {
  return new Date(timestamp).toLocaleTimeString()
}
</script>

<style scoped>
.progress-stream {
  padding: 20px;
}

.overall-progress {
  margin-bottom: 30px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.progress-header h3 {
  margin: 0;
  color: #1f2937;
  font-size: 18px;
}

.progress-percentage {
  font-weight: bold;
  color: #2563eb;
  font-size: 16px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #2563eb, #1d4ed8);
  transition: width 0.3s ease;
}

.stages-list {
  margin-bottom: 30px;
}

.stage-item {
  display: flex;
  align-items: center;
  padding: 15px;
  margin-bottom: 10px;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.stage-item.completed {
  background: #f0f9ff;
  border-left: 4px solid #10b981;
}

.stage-item.current {
  background: #fef3c7;
  border-left: 4px solid #f59e0b;
  animation: pulse 2s infinite;
}

.stage-item.pending {
  background: #f9fafb;
  border-left: 4px solid #d1d5db;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.stage-icon {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 15px;
  border-radius: 50%;
  font-weight: bold;
}

.stage-item.completed .stage-icon {
  background: #10b981;
  color: white;
}

.stage-item.current .stage-icon {
  background: #f59e0b;
  color: white;
}

.stage-item.pending .stage-icon {
  background: #d1d5db;
  color: #6b7280;
}

.stage-content {
  flex: 1;
}

.stage-name {
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 4px;
}

.stage-message {
  color: #6b7280;
  font-size: 14px;
}

.stage-duration {
  color: #9ca3af;
  font-size: 12px;
  margin-top: 4px;
}

.research-tasks {
  margin-bottom: 30px;
}

.research-tasks h4 {
  color: #1f2937;
  margin-bottom: 15px;
  font-size: 16px;
}

.tasks-list {
  display: grid;
  gap: 10px;
}

.task-item {
  display: flex;
  align-items: center;
  padding: 12px;
  border-radius: 6px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
}

.task-item.completed {
  background: #f0fdf4;
  border-color: #10b981;
}

.task-item.in-progress {
  background: #fef3c7;
  border-color: #f59e0b;
}

.task-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
  border-radius: 50%;
  font-size: 12px;
  font-weight: bold;
}

.task-item.completed .task-icon {
  background: #10b981;
  color: white;
}

.task-item.in-progress .task-icon {
  background: #f59e0b;
  color: white;
}

.task-item.pending .task-icon {
  background: #d1d5db;
  color: #6b7280;
}

.task-content {
  flex: 1;
}

.task-topic {
  font-weight: 500;
  color: #1f2937;
  margin-bottom: 2px;
}

.task-findings {
  color: #6b7280;
  font-size: 12px;
}

.realtime-log {
  border-top: 1px solid #e5e7eb;
  padding-top: 20px;
}

.realtime-log h4 {
  color: #1f2937;
  margin-bottom: 15px;
  font-size: 16px;
}

.log-container {
  max-height: 200px;
  overflow-y: auto;
  background: #f9fafb;
  border-radius: 6px;
  padding: 10px;
}

.log-item {
  display: flex;
  padding: 6px 0;
  border-bottom: 1px solid #e5e7eb;
  font-size: 13px;
}

.log-item:last-child {
  border-bottom: none;
}

.log-time {
  color: #9ca3af;
  margin-right: 10px;
  min-width: 80px;
}

.log-message {
  color: #1f2937;
  flex: 1;
}

.log-item.error .log-message {
  color: #dc2626;
}

.log-item.warning .log-message {
  color: #d97706;
}
</style>
```

### 3. **报告查看器组件** (`ReportViewer.vue`)

```vue
<template>
  <div class="report-viewer">
    <div class="report-header">
      <h2>{{ researchResult.question }}</h2>
      <div class="report-meta">
        <span class="quality-score">质量评分: {{ qualityScore }}分</span>
        <span class="findings-count">关键发现: {{ researchResult.key_findings?.length || 0 }}条</span>
      </div>
    </div>

    <div class="report-actions">
      <div class="format-selector">
        <label>查看格式:</label>
        <select v-model="currentFormat" @change="loadReport">
          <option value="preview">预览模式</option>
          <option value="json">JSON</option>
          <option value="html">HTML</option>
        </select>
      </div>
      
      <div class="download-buttons">
        <button 
          v-for="format in availableFormats" 
          :key="format"
          @click="downloadReport(format)"
          class="download-btn"
          :class="format"
        >
          <i class="icon">📄</i>
          下载 {{ format.toUpperCase() }}
        </button>
      </div>
    </div>

    <div class="report-content">
      <div v-if="currentFormat === 'preview'" class="preview-mode">
        <div class="key-findings">
          <h3>关键发现</h3>
          <ul>
            <li v-for="finding in researchResult.key_findings" :key="finding">
              {{ finding }}
            </li>
          </ul>
        </div>
        
        <div class="report-text">
          <h3>研究报告</h3>
          <div class="report-body" v-html="formattedReport"></div>
        </div>
      </div>
      
      <div v-else-if="currentFormat === 'json'" class="json-mode">
        <pre>{{ JSON.stringify(researchResult, null, 2) }}</pre>
      </div>
      
      <div v-else-if="currentFormat === 'html'" class="html-mode">
        <div v-html="htmlReport"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const props = defineProps({
  researchResult: {
    type: Object,
    required: true
  },
  reportUrls: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['download'])

const currentFormat = ref('preview')
const htmlReport = ref('')

// 计算质量评分
const qualityScore = computed(() => {
  return props.researchResult.quality_metrics?.overall_score || 0
})

// 计算可用格式
const availableFormats = computed(() => {
  return Object.keys(props.reportUrls)
})

// 格式化报告文本
const formattedReport = computed(() => {
  if (!props.researchResult.final_report) return ''
  
  // 简单的 Markdown 转 HTML
  return props.researchResult.final_report
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
})

// 加载报告
const loadReport = async () => {
  if (currentFormat.value === 'html' && props.reportUrls.html) {
    try {
      const response = await fetch(props.reportUrls.html)
      htmlReport.value = await response.text()
    } catch (error) {
      console.error('加载HTML报告失败:', error)
    }
  }
}

// 下载报告
const downloadReport = (format) => {
  emit('download', format)
}

onMounted(() => {
  loadReport()
})
</script>

<style scoped>
.report-viewer {
  background: white;
  border-radius: 12px;
  overflow: hidden;
}

.report-header {
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  color: white;
  padding: 30px;
}

.report-header h2 {
  margin: 0 0 15px 0;
  font-size: 24px;
  line-height: 1.3;
}

.report-meta {
  display: flex;
  gap: 20px;
  font-size: 14px;
  opacity: 0.9;
}

.quality-score {
  background: rgba(255, 255, 255, 0.2);
  padding: 4px 8px;
  border-radius: 4px;
}

.findings-count {
  background: rgba(255, 255, 255, 0.2);
  padding: 4px 8px;
  border-radius: 4px;
}

.report-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 30px;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}

.format-selector {
  display: flex;
  align-items: center;
  gap: 10px;
}

.format-selector select {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
}

.download-buttons {
  display: flex;
  gap: 10px;
}

.download-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  color: #374151;
  cursor: pointer;
  transition: all 0.2s ease;
}

.download-btn:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
}

.download-btn.pdf {
  border-color: #dc2626;
  color: #dc2626;
}

.download-btn.pdf:hover {
  background: #fef2f2;
}

.download-btn.docx {
  border-color: #2563eb;
  color: #2563eb;
}

.download-btn.docx:hover {
  background: #eff6ff;
}

.report-content {
  padding: 30px;
  max-height: 600px;
  overflow-y: auto;
}

.preview-mode {
  display: grid;
  gap: 30px;
}

.key-findings h3,
.report-text h3 {
  color: #1f2937;
  margin-bottom: 15px;
  font-size: 18px;
  border-bottom: 2px solid #e5e7eb;
  padding-bottom: 8px;
}

.key-findings ul {
  list-style: none;
  padding: 0;
}

.key-findings li {
  padding: 10px 15px;
  margin-bottom: 8px;
  background: #f0f9ff;
  border-left: 4px solid #2563eb;
  border-radius: 4px;
}

.report-body {
  line-height: 1.6;
  color: #1f2937;
}

.json-mode pre {
  background: #1f2937;
  color: #f9fafb;
  padding: 20px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 14px;
}

.html-mode {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}
</style>
```

## 🚀 使用说明

1. **安装依赖**：
   ```bash
   npm install vue@3 @vue/composition-api
   ```

2. **集成到项目**：
   - 将组件文件放到 `components/` 目录
   - 在主页面中引入和使用

3. **API集成**：
   - 确保后端API正常运行
   - 根据实际部署情况调整API地址

4. **样式定制**：
   - 可以根据项目需求调整CSS样式
   - 支持响应式设计

这个设计提供了完整的用户体验，包括实时进度显示、多格式报告下载和友好的界面交互！
