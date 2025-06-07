<!--
  AI 工作摘要組件
  顯示 AI 當前工作狀態、請求和進度
-->

<template>
  <div class="ai-work-summary">
    <!-- 當前工作狀態 -->
    <div class="work-status-section">
      <h3 class="section-title">
        <span class="title-icon">⚡</span>
        Current Status
      </h3>
      <div class="status-card">
        <div class="status-indicator" :class="statusClass">
          <span class="status-dot"></span>
          <span class="status-text">{{ workStatus.status }}</span>
        </div>
        <div class="status-details">
          <div class="detail-item">
            <span class="detail-label">Task:</span>
            <span class="detail-value">{{ workStatus.currentTask }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Progress:</span>
            <div class="progress-container">
              <div class="progress-bar">
                <div 
                  class="progress-fill" 
                  :style="{ width: workStatus.progress + '%' }"
                ></div>
              </div>
              <span class="progress-text">{{ workStatus.progress }}%</span>
            </div>
          </div>
          <div class="detail-item">
            <span class="detail-label">Duration:</span>
            <span class="detail-value">{{ formatDuration(workStatus.duration) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- AI 請求內容 -->
    <div class="ai-request-section">
      <h3 class="section-title">
        <span class="title-icon">🤖</span>
        AI Request
      </h3>
      <div class="request-card">
        <div class="request-type" :class="requestTypeClass">
          {{ aiRequest.type }}
        </div>
        <div class="request-content">
          <div v-if="aiRequest.content" class="request-text">
            {{ aiRequest.content }}
          </div>
          <div v-if="aiRequest.codeSnippet" class="code-snippet">
            <pre><code>{{ aiRequest.codeSnippet }}</code></pre>
          </div>
        </div>
        <div class="request-meta">
          <span class="request-time">{{ formatTime(aiRequest.timestamp) }}</span>
          <span class="request-priority" :class="priorityClass">
            {{ aiRequest.priority }}
          </span>
        </div>
      </div>
    </div>

    <!-- 工作歷史 -->
    <div class="work-history-section">
      <h3 class="section-title">
        <span class="title-icon">📋</span>
        Recent Activity
      </h3>
      <div class="history-timeline">
        <div 
          v-for="item in workHistory" 
          :key="item.id"
          class="timeline-item"
        >
          <div class="timeline-dot" :class="item.type"></div>
          <div class="timeline-content">
            <div class="timeline-title">{{ item.title }}</div>
            <div class="timeline-description">{{ item.description }}</div>
            <div class="timeline-time">{{ formatTime(item.timestamp) }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 快速操作 -->
    <div class="quick-actions-section">
      <h3 class="section-title">
        <span class="title-icon">⚡</span>
        Quick Actions
      </h3>
      <div class="action-buttons">
        <button 
          @click="pauseWork" 
          class="action-btn pause-btn"
          :disabled="workStatus.status === 'paused'"
        >
          <span class="btn-icon">⏸️</span>
          Pause
        </button>
        <button 
          @click="resumeWork" 
          class="action-btn resume-btn"
          :disabled="workStatus.status !== 'paused'"
        >
          <span class="btn-icon">▶️</span>
          Resume
        </button>
        <button 
          @click="requestHelp" 
          class="action-btn help-btn"
        >
          <span class="btn-icon">❓</span>
          Need Help
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useSessionStore } from '@/stores/session'
import { useAIWorkStore } from '@/stores/aiWork'

// ===== Props =====
const props = defineProps({
  // 是否自動更新
  autoUpdate: {
    type: Boolean,
    default: true
  },
  
  // 更新間隔（毫秒）
  updateInterval: {
    type: Number,
    default: 5000
  }
})

// ===== Emits =====
const emit = defineEmits([
  'pause-work',
  'resume-work', 
  'request-help',
  'status-change'
])

// ===== Store =====
const sessionStore = useSessionStore()
const aiWorkStore = useAIWorkStore()

// ===== 狀態 =====
const updateTimer = ref(null)

// 模擬工作狀態數據
const workStatus = ref({
  status: 'working', // 'idle', 'working', 'paused', 'completed', 'error'
  currentTask: 'Frontend Refactoring - AI Work Summary Component',
  progress: 75,
  duration: 1800000, // 30 minutes in milliseconds
  startTime: Date.now() - 1800000
})

// 模擬 AI 請求數據
const aiRequest = ref({
  type: 'Review Request',
  content: 'Please review the new AI Work Summary component implementation. Check if the layout matches the design requirements and if the real-time updates work correctly.',
  codeSnippet: null,
  timestamp: Date.now() - 300000, // 5 minutes ago
  priority: 'medium'
})

// 模擬工作歷史
const workHistory = ref([
  {
    id: 1,
    type: 'completed',
    title: 'App.vue Layout Refactored',
    description: 'Successfully updated main layout to AI-Human collaboration design',
    timestamp: Date.now() - 600000 // 10 minutes ago
  },
  {
    id: 2,
    type: 'started',
    title: 'AI Work Summary Component',
    description: 'Started creating the AI work summary component',
    timestamp: Date.now() - 300000 // 5 minutes ago
  },
  {
    id: 3,
    type: 'progress',
    title: 'Component Structure',
    description: 'Implemented basic component structure and styling',
    timestamp: Date.now() - 120000 // 2 minutes ago
  }
])

// ===== 計算屬性 =====
const statusClass = computed(() => {
  const statusMap = {
    'idle': 'status-idle',
    'working': 'status-working', 
    'paused': 'status-paused',
    'completed': 'status-completed',
    'error': 'status-error'
  }
  return statusMap[workStatus.value.status] || 'status-idle'
})

const requestTypeClass = computed(() => {
  const typeMap = {
    'Review Request': 'type-review',
    'Code Request': 'type-code',
    'Question': 'type-question',
    'Feedback': 'type-feedback'
  }
  return typeMap[aiRequest.value.type] || 'type-general'
})

const priorityClass = computed(() => {
  const priorityMap = {
    'low': 'priority-low',
    'medium': 'priority-medium', 
    'high': 'priority-high',
    'urgent': 'priority-urgent'
  }
  return priorityMap[aiRequest.value.priority] || 'priority-medium'
})

// ===== 方法 =====

/**
 * 格式化持續時間
 */
function formatDuration(milliseconds) {
  const minutes = Math.floor(milliseconds / 60000)
  const seconds = Math.floor((milliseconds % 60000) / 1000)
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

/**
 * 格式化時間
 */
function formatTime(timestamp) {
  const now = Date.now()
  const diff = now - timestamp
  
  if (diff < 60000) {
    return 'Just now'
  } else if (diff < 3600000) {
    const minutes = Math.floor(diff / 60000)
    return `${minutes} min ago`
  } else {
    const hours = Math.floor(diff / 3600000)
    return `${hours} hour${hours > 1 ? 's' : ''} ago`
  }
}

/**
 * 暫停工作
 */
function pauseWork() {
  workStatus.value.status = 'paused'
  emit('pause-work')
  emit('status-change', workStatus.value)
}

/**
 * 恢復工作
 */
function resumeWork() {
  workStatus.value.status = 'working'
  emit('resume-work')
  emit('status-change', workStatus.value)
}

/**
 * 請求幫助
 */
function requestHelp() {
  emit('request-help', {
    currentTask: workStatus.value.currentTask,
    progress: workStatus.value.progress,
    timestamp: Date.now()
  })
}

/**
 * 更新工作狀態
 */
function updateWorkStatus() {
  // 這裡將來會從 WebSocket 或 API 獲取實際數據
  if (workStatus.value.status === 'working') {
    workStatus.value.duration = Date.now() - workStatus.value.startTime
    
    // 模擬進度更新
    if (workStatus.value.progress < 100) {
      workStatus.value.progress = Math.min(100, workStatus.value.progress + Math.random() * 2)
    }
  }
}

/**
 * 開始自動更新
 */
function startAutoUpdate() {
  if (props.autoUpdate && !updateTimer.value) {
    updateTimer.value = setInterval(updateWorkStatus, props.updateInterval)
  }
}

/**
 * 停止自動更新
 */
function stopAutoUpdate() {
  if (updateTimer.value) {
    clearInterval(updateTimer.value)
    updateTimer.value = null
  }
}

// ===== 生命週期 =====
onMounted(() => {
  console.log('🤖 AI Work Summary component mounted')
  startAutoUpdate()
})

onUnmounted(() => {
  stopAutoUpdate()
})
</script>

<style lang="scss" scoped>
.ai-work-summary {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  height: 100%;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 1rem 0;
  font-size: 1rem;
  font-weight: 600;
  color: #1e293b;
}

.title-icon {
  font-size: 1.125rem;
}

// 工作狀態區域
.work-status-section {
  .status-card {
    background: #f8fafc;
    border-radius: 12px;
    padding: 1.5rem;
    border: 1px solid #e2e8f0;
  }
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
  
  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    
    .status-working & {
      background: #10b981;
      animation: pulse 2s infinite;
    }
    
    .status-paused & {
      background: #f59e0b;
    }
    
    .status-completed & {
      background: #3b82f6;
    }
    
    .status-error & {
      background: #ef4444;
    }
    
    .status-idle & {
      background: #6b7280;
    }
  }
  
  .status-text {
    font-weight: 500;
    text-transform: capitalize;
  }
}

.status-details {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  
  .detail-label {
    font-size: 0.875rem;
    color: #64748b;
    font-weight: 500;
  }
  
  .detail-value {
    font-size: 0.875rem;
    color: #1e293b;
    font-weight: 500;
  }
}

.progress-container {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
  margin-left: 1rem;
}

.progress-bar {
  flex: 1;
  height: 6px;
  background: #e2e8f0;
  border-radius: 3px;
  overflow: hidden;
  
  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #4fc08d 0%, #42b883 100%);
    transition: width 0.3s ease;
  }
}

.progress-text {
  font-size: 0.75rem;
  color: #64748b;
  font-weight: 500;
  min-width: 2.5rem;
}

// AI 請求區域
.ai-request-section {
  .request-card {
    background: #f8fafc;
    border-radius: 12px;
    padding: 1.5rem;
    border: 1px solid #e2e8f0;
  }
}

.request-type {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 500;
  margin-bottom: 1rem;
  
  &.type-review {
    background: #dbeafe;
    color: #1e40af;
  }
  
  &.type-code {
    background: #dcfce7;
    color: #166534;
  }
  
  &.type-question {
    background: #fef3c7;
    color: #92400e;
  }
  
  &.type-feedback {
    background: #fce7f3;
    color: #be185d;
  }
}

.request-content {
  margin-bottom: 1rem;
  
  .request-text {
    color: #374151;
    line-height: 1.6;
    font-size: 0.875rem;
  }
  
  .code-snippet {
    margin-top: 0.75rem;
    
    pre {
      background: #1e293b;
      color: #e2e8f0;
      padding: 1rem;
      border-radius: 8px;
      font-size: 0.75rem;
      overflow-x: auto;
      margin: 0;
    }
  }
}

.request-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  
  .request-time {
    font-size: 0.75rem;
    color: #9ca3af;
  }
  
  .request-priority {
    padding: 0.125rem 0.5rem;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 500;
    
    &.priority-low {
      background: #f3f4f6;
      color: #6b7280;
    }
    
    &.priority-medium {
      background: #fef3c7;
      color: #92400e;
    }
    
    &.priority-high {
      background: #fecaca;
      color: #dc2626;
    }
    
    &.priority-urgent {
      background: #fecaca;
      color: #dc2626;
      animation: pulse 2s infinite;
    }
  }
}

// 工作歷史區域
.work-history-section {
  flex: 1;
  min-height: 0;
}

.history-timeline {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-height: 200px;
  overflow-y: auto;
  padding-right: 0.5rem;
}

.timeline-item {
  display: flex;
  gap: 0.75rem;
  
  .timeline-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-top: 0.5rem;
    flex-shrink: 0;
    
    &.completed {
      background: #10b981;
    }
    
    &.started {
      background: #3b82f6;
    }
    
    &.progress {
      background: #f59e0b;
    }
  }
  
  .timeline-content {
    flex: 1;
    
    .timeline-title {
      font-weight: 500;
      color: #1e293b;
      font-size: 0.875rem;
      margin-bottom: 0.25rem;
    }
    
    .timeline-description {
      color: #64748b;
      font-size: 0.75rem;
      line-height: 1.4;
      margin-bottom: 0.25rem;
    }
    
    .timeline-time {
      color: #9ca3af;
      font-size: 0.75rem;
    }
  }
}

// 快速操作區域
.quick-actions-section {
  .action-buttons {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }
  
  .action-btn {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.5rem 0.75rem;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    background: white;
    color: #374151;
    font-size: 0.75rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    
    &:hover:not(:disabled) {
      background: #f9fafb;
      border-color: #9ca3af;
    }
    
    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    
    .btn-icon {
      font-size: 0.875rem;
    }
    
    &.pause-btn {
      border-color: #f59e0b;
      color: #92400e;
      
      &:hover:not(:disabled) {
        background: rgba(245, 158, 11, 0.05);
      }
    }
    
    &.resume-btn {
      border-color: #10b981;
      color: #059669;
      
      &:hover:not(:disabled) {
        background: rgba(16, 185, 129, 0.05);
      }
    }
    
    &.help-btn {
      border-color: #3b82f6;
      color: #2563eb;
      
      &:hover:not(:disabled) {
        background: rgba(59, 130, 246, 0.05);
      }
    }
  }
}

// 動畫
@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

// 響應式設計
@media (max-width: 768px) {
  .ai-work-summary {
    gap: 1rem;
  }
  
  .status-card,
  .request-card {
    padding: 1rem;
  }
  
  .action-buttons {
    .action-btn {
      flex: 1;
      justify-content: center;
    }
  }
}
</style>
