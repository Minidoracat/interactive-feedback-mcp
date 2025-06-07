<template>
  <div id="app" class="app">
    <!-- WebSocket 客戶端 -->
    <WebSocketClient
      ref="websocketClient"
      :auto-connect="true"
      @connected="handleWebSocketConnected"
      @disconnected="handleWebSocketDisconnected"
      @error="handleWebSocketError"
      @session-assigned="handleSessionAssigned"
      @feedback-submitted="handleFeedbackSubmitted"
    />

    <!-- Header -->
    <header class="app-header">
      <div class="container">
        <h1 class="app-title">
          🤖 MCP Feedback Enhanced
        </h1>
        <p class="app-subtitle">
          AI-Human Collaborative Development Workflow
        </p>
      </div>
    </header>

    <!-- Main Content -->
    <main class="app-main">
      <div class="container">
        <!-- Session Status -->
        <SessionStatus
          :show-details="true"
          :show-actions="true"
          :compact="false"
          @extend-session="handleExtendSession"
          @reconnect="handleReconnect"
          @reset-session="handleResetSession"
          class="session-status-component"
        />

        <!-- AI-Human Collaborative Interface -->
        <div class="collaboration-layout">
          <!-- Left Panel: AI Work Summary -->
          <div class="ai-work-panel">
            <div class="panel-header">
              <h2 class="panel-title">
                <span class="panel-icon">🤖</span>
                AI Work Summary
              </h2>
            </div>
            <div class="panel-content">
              <AIWorkSummary
                :auto-update="true"
                :update-interval="5000"
                @pause-work="handlePauseWork"
                @resume-work="handleResumeWork"
                @request-help="handleRequestHelp"
                @status-change="handleStatusChange"
              />
            </div>
          </div>

          <!-- Right Panel: Human Response -->
          <div class="human-response-panel">
            <div class="panel-header">
              <h2 class="panel-title">
                <span class="panel-icon">👤</span>
                Human Response
              </h2>
            </div>
            <div class="panel-content">
              <HumanResponsePanel
                :auto-save="true"
                @submit="handleFeedbackSubmit"
                @quick-response="handleQuickResponse"
                @files-added="handleFilesAdded"
                @file-removed="handleFileRemoved"
                @files-cleared="handleFilesCleared"
                @upload-complete="handleUploadComplete"
                @upload-error="handleUploadError"
              />
            </div>
          </div>
        </div>

        <!-- Development Notice -->
        <div class="dev-notice" v-if="isDevelopment">
          <h3>🔧 Development Mode</h3>
          <p>
            You are running the frontend in development mode.
            The backend should be running on <code>http://localhost:8000</code>.
          </p>
          <div class="dev-info">
            <p><strong>Frontend:</strong> http://localhost:5173</p>
            <p><strong>Backend:</strong> http://localhost:8000</p>
            <p><strong>API Docs:</strong> <a href="http://localhost:8000/docs" target="_blank">http://localhost:8000/docs</a></p>
            <p><strong>WebSocket:</strong> ws://localhost:8000/ws/session/{sessionId}</p>
          </div>
        </div>


      </div>
    </main>

    <!-- Footer -->
    <footer class="app-footer">
      <div class="container">
        <p>&copy; 2024 MCP Feedback Enhanced Team. Licensed under MIT.</p>
        <p class="footer-version">Version 0.1.0 | Built with Vue.js 3 + FastAPI</p>
      </div>
    </footer>

    <!-- 全局通知 -->
    <div v-if="notification.show" class="notification" :class="notification.type">
      <div class="notification-content">
        <span class="notification-icon">{{ notification.icon }}</span>
        <div class="notification-text">
          <div class="notification-title">{{ notification.title }}</div>
          <div class="notification-message">{{ notification.message }}</div>
        </div>
        <button @click="hideNotification" class="notification-close">×</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { useSessionStore } from '@/stores/session'
import { useFeedbackStore } from '@/stores/feedback'

// 組件導入
import WebSocketClient from '@/components/WebSocketClient.vue'
import SessionStatus from '@/components/SessionStatus.vue'
import AIWorkSummary from '@/components/AIWorkSummary.vue'
import HumanResponsePanel from '@/components/HumanResponsePanel.vue'

// ===== Stores =====
const sessionStore = useSessionStore()
const feedbackStore = useFeedbackStore()

// ===== 狀態 =====
const websocketClient = ref(null)

// 通知系統
const notification = reactive({
  show: false,
  type: 'info', // 'success', 'error', 'warning', 'info'
  icon: 'ℹ️',
  title: '',
  message: '',
  timeout: null
})

// ===== 計算屬性 =====
const isDevelopment = computed(() => import.meta.env.DEV)
const isConnected = computed(() => sessionStore.isConnected)
const sessionId = computed(() => sessionStore.sessionId)

// ===== 通知方法 =====
function showNotification(type, title, message, duration = 5000) {
  // 清除之前的定時器
  if (notification.timeout) {
    clearTimeout(notification.timeout)
  }

  const iconMap = {
    success: '✅',
    error: '❌',
    warning: '⚠️',
    info: 'ℹ️'
  }

  notification.type = type
  notification.icon = iconMap[type] || 'ℹ️'
  notification.title = title
  notification.message = message
  notification.show = true

  // 自動隱藏
  if (duration > 0) {
    notification.timeout = setTimeout(() => {
      hideNotification()
    }, duration)
  }
}

function hideNotification() {
  notification.show = false
  if (notification.timeout) {
    clearTimeout(notification.timeout)
    notification.timeout = null
  }
}

// ===== WebSocket 事件處理 =====
function handleWebSocketConnected(data) {
  console.log('✅ WebSocket 已連接:', data)
  showNotification('success', '連接成功', 'WebSocket 連接已建立')
}

function handleWebSocketDisconnected(data) {
  console.log('🔌 WebSocket 已斷開:', data)
  showNotification('warning', '連接斷開', 'WebSocket 連接已斷開，正在嘗試重連...')
}

function handleWebSocketError(error) {
  console.error('❌ WebSocket 錯誤:', error)
  showNotification('error', '連接錯誤', 'WebSocket 連接出現錯誤')
}

function handleSessionAssigned(data) {
  console.log('🎯 會話已分配:', data)
  showNotification('info', '會話已分配', `會話 ID: ${data.sessionId}`)
}

function handleFeedbackSubmitted(data) {
  console.log('📝 反饋已提交:', data)
  showNotification('success', '提交成功', '您的反饋已成功提交')
}

// ===== 會話管理事件處理 =====
function handleExtendSession() {
  console.log('⏰ 延長會話')
  showNotification('info', '會話已延長', '會話時間已延長 30 分鐘')
}

function handleReconnect() {
  console.log('🔄 重新連接')
  if (websocketClient.value) {
    websocketClient.value.reconnect()
  }
}

function handleResetSession() {
  console.log('🔄 重置會話')
  showNotification('info', '會話已重置', '會話已重置，請重新開始')
}

// ===== 人類回饋事件處理 =====
function handleFeedbackSubmit(data) {
  console.log('📤 提交回饋:', data)

  // 通過 WebSocket 發送回饋
  if (websocketClient.value && websocketClient.value.isConnected) {
    websocketClient.value.sendFeedback(data)
    showNotification('success', '回饋已提交', '您的回饋已成功發送給 AI')
  } else {
    showNotification('error', '提交失敗', '請先建立 WebSocket 連接')
  }
}

function handleQuickResponse(response) {
  console.log('⚡ 快速回應:', response)

  // 通過 WebSocket 發送快速回應
  if (websocketClient.value && websocketClient.value.isConnected) {
    websocketClient.value.sendFeedback(response)
    showNotification('success', '快速回應已發送', response.text)
  } else {
    showNotification('error', '發送失敗', '請先建立 WebSocket 連接')
  }
}

// ===== 文件上傳事件處理 =====
function handleFilesAdded(files) {
  console.log('📁 文件已添加:', files)
  showNotification('success', '文件已添加', `成功添加 ${files.length} 個文件`)
}

function handleFileRemoved(fileId) {
  console.log('🗑️ 文件已移除:', fileId)
  showNotification('info', '文件已移除', '文件已從列表中移除')
}

function handleFilesCleared() {
  console.log('🗑️ 文件已清空')
  showNotification('info', '文件已清空', '所有文件已清空')
}

function handleUploadComplete(files) {
  console.log('✅ 上傳完成:', files)
  showNotification('success', '上傳完成', `${files.length} 個文件上傳完成`)
}

function handleUploadError(error) {
  console.error('❌ 上傳錯誤:', error)
  showNotification('error', '上傳失敗', '文件上傳過程中出現錯誤')
}

// ===== AI 工作摘要事件處理 =====
function handlePauseWork() {
  console.log('⏸️ AI 工作已暫停')
  showNotification('info', '工作已暫停', 'AI 工作流程已暫停')
}

function handleResumeWork() {
  console.log('▶️ AI 工作已恢復')
  showNotification('info', '工作已恢復', 'AI 工作流程已恢復')
}

function handleRequestHelp(data) {
  console.log('❓ 請求幫助:', data)
  showNotification('info', '需要幫助', '已收到 AI 的幫助請求')
}

function handleStatusChange(status) {
  console.log('📊 工作狀態變化:', status)
  // 這裡可以更新全局狀態或發送到後端
}

// ===== UI 交互 =====
// Features section removed - no longer needed

// ===== 生命週期 =====
onMounted(() => {
  console.log('🎯 MCP Feedback Enhanced App 已掛載')

  // 初始化會話
  if (!sessionStore.sessionId) {
    sessionStore.initializeSession()
  }

  // 開發模式提示
  if (isDevelopment.value) {
    showNotification('info', '開發模式', '應用正在開發模式下運行', 3000)
  }
})
</script>

<style lang="scss" scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #4fc08d 0%, #42b883 100%);
  color: #2c3e50;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 20px;
}

.app-header {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.25);
  padding: 1.5rem 0;
  text-align: center;
  color: white;

  .app-title {
    font-size: 2rem;
    font-weight: 600;
    margin: 0 0 0.5rem 0;
    text-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    letter-spacing: -0.025em;
  }

  .app-subtitle {
    font-size: 1rem;
    margin: 0;
    opacity: 0.9;
    font-weight: 400;
  }
}

.app-main {
  flex: 1;
  padding: 2rem 0;
}

// 會話狀態組件樣式
.session-status-component {
  margin-bottom: 2rem;
}

// AI-Human 協作布局
.collaboration-layout {
  display: grid;
  grid-template-columns: 2fr 3fr;
  gap: 2rem;
  margin-bottom: 2rem;
  min-height: 600px;

  @media (max-width: 1024px) {
    grid-template-columns: 1fr;
    gap: 1.5rem;
    min-height: auto;
  }
}

.ai-work-panel,
.human-response-panel {
  background: rgba(255, 255, 255, 0.98);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.panel-header {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-bottom: 1px solid #e2e8f0;
  padding: 1.5rem 2rem;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #1e293b;
}

.panel-icon {
  font-size: 1.5rem;
}

.panel-content {
  flex: 1;
  padding: 2rem;
  overflow-y: auto;
}

// AI 狀態佔位符樣式已移除 - 使用 AIWorkSummary 組件

// 上傳區域樣式已移至 HumanResponsePanel 組件

// 特性展示區域已移除 - 不再需要

// 開發模式提示
.dev-notice {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  padding: 2rem;
  border-left: 4px solid #f59e0b;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;

  h3 {
    margin: 0 0 1rem 0;
    color: #f59e0b;
    font-size: 1.25rem;
    font-weight: 600;
  }

  p {
    color: #6b7280;
    line-height: 1.6;
    margin-bottom: 1rem;
  }

  .dev-info {
    background: #f8fafc;
    border-radius: 6px;
    padding: 1rem;
    border: 1px solid #e2e8f0;

    p {
      margin: 0.25rem 0;
      font-family: 'Monaco', 'Menlo', monospace;
      font-size: 0.875rem;
    }

    a {
      color: #3b82f6;
      text-decoration: none;

      &:hover {
        text-decoration: underline;
      }
    }
  }
}

// 頁腳
.app-footer {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-top: 1px solid rgba(255, 255, 255, 0.2);
  padding: 1.5rem 0;
  text-align: center;
  color: white;

  p {
    margin: 0.25rem 0;
    opacity: 0.8;

    &.footer-version {
      font-size: 0.875rem;
      opacity: 0.6;
    }
  }
}

// 全局通知
.notification {
  position: fixed;
  top: 2rem;
  right: 2rem;
  z-index: 1000;
  max-width: 400px;
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(10px);
  animation: slideIn 0.3s ease-out;

  &.success {
    background: rgba(16, 185, 129, 0.95);
    color: white;
  }

  &.error {
    background: rgba(239, 68, 68, 0.95);
    color: white;
  }

  &.warning {
    background: rgba(245, 158, 11, 0.95);
    color: white;
  }

  &.info {
    background: rgba(59, 130, 246, 0.95);
    color: white;
  }
}

.notification-content {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
}

.notification-icon {
  font-size: 1.25rem;
  margin-top: 0.125rem;
}

.notification-text {
  flex: 1;
}

.notification-title {
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.notification-message {
  font-size: 0.875rem;
  opacity: 0.9;
  line-height: 1.4;
}

.notification-close {
  background: none;
  border: none;
  color: inherit;
  font-size: 1.25rem;
  cursor: pointer;
  padding: 0;
  width: 1.5rem;
  height: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background-color 0.2s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.2);
  }
}

// 動畫
@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

// 響應式設計
@media (max-width: 1024px) {
  .container {
    padding: 0 1rem;
  }

  .app-main {
    padding: 1.5rem 0;
  }
}

@media (max-width: 768px) {
  .app-header {
    padding: 1rem 0;

    .app-title {
      font-size: 1.75rem;
    }

    .app-subtitle {
      font-size: 0.875rem;
    }
  }

  .collaboration-layout {
    gap: 1rem;
  }

  .panel-header {
    padding: 1rem 1.5rem;
  }

  .panel-content {
    padding: 1.5rem;
  }

  .upload-section,
  .dev-notice {
    padding: 1.5rem;
  }

  .notification {
    top: 1rem;
    right: 1rem;
    left: 1rem;
    max-width: none;
  }
}

@media (max-width: 480px) {
  .container {
    padding: 0 0.75rem;
  }

  .app-header {
    padding: 0.75rem 0;

    .app-title {
      font-size: 1.5rem;
    }
  }

  .panel-header {
    padding: 0.75rem 1rem;
  }

  .panel-content {
    padding: 1rem;
  }

  .upload-section,
  .dev-notice {
    padding: 1rem;
  }
}
</style>
