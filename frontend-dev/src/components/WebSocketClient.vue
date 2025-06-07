<!--
  WebSocket 客戶端組件
  負責管理 WebSocket 連接、處理實時事件、同步狀態
-->

<template>
  <div class="websocket-client">
    <!-- 連接狀態指示器 -->
    <div 
      v-if="showStatusIndicator" 
      class="connection-status"
      :class="connectionStatusClass"
    >
      <div class="status-dot"></div>
      <span class="status-text">{{ connectionStatusText }}</span>
      
      <!-- 重連按鈕 -->
      <button 
        v-if="canShowReconnectButton"
        @click="handleReconnect"
        class="reconnect-btn"
        :disabled="isConnecting"
      >
        {{ isConnecting ? '連接中...' : '重新連接' }}
      </button>
    </div>
    
    <!-- 錯誤提示 -->
    <div 
      v-if="lastError && showErrorAlert"
      class="error-alert"
    >
      <div class="error-content">
        <span class="error-icon">⚠️</span>
        <span class="error-message">{{ lastError.message }}</span>
        <button @click="clearError" class="error-close">×</button>
      </div>
    </div>
    
    <!-- 消息隊列狀態 -->
    <div 
      v-if="messageQueue.length > 0 && showQueueStatus"
      class="queue-status"
    >
      <span class="queue-icon">📦</span>
      <span class="queue-text">
        {{ messageQueue.length }} 條消息等待發送
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'
import { useSessionStore } from '@/stores/session'
import { useFeedbackStore } from '@/stores/feedback'

// ===== Props =====
const props = defineProps({
  // 是否顯示狀態指示器
  showStatusIndicator: {
    type: Boolean,
    default: true
  },
  
  // 是否顯示錯誤警告
  showErrorAlert: {
    type: Boolean,
    default: true
  },
  
  // 是否顯示消息隊列狀態
  showQueueStatus: {
    type: Boolean,
    default: true
  },
  
  // 是否自動連接
  autoConnect: {
    type: Boolean,
    default: true
  },
  
  // 連接配置
  connectionConfig: {
    type: Object,
    default: () => ({})
  }
})

// ===== Emits =====
const emit = defineEmits([
  'connected',
  'disconnected',
  'error',
  'message',
  'session-assigned',
  'feedback-submitted',
  'session-expired'
])

// ===== Stores =====
const sessionStore = useSessionStore()
const feedbackStore = useFeedbackStore()

// ===== Composables =====
const {
  isConnected,
  isConnecting,
  connectionState,
  messageQueue,
  connect,
  disconnect,
  reconnect,
  sendMessage,
  addEventListener,
  removeEventListener
} = useWebSocket()

// ===== 狀態 =====
const eventListeners = ref([])
const lastError = computed(() => sessionStore.lastError)

// ===== 計算屬性 =====
const connectionStatusClass = computed(() => {
  return {
    'status-connected': isConnected.value,
    'status-connecting': isConnecting.value,
    'status-disconnected': !isConnected.value && !isConnecting.value,
    'status-error': sessionStore.connectionStatus === 'error'
  }
})

const connectionStatusText = computed(() => {
  return sessionStore.connectionStatusText
})

const canShowReconnectButton = computed(() => {
  return !isConnected.value && sessionStore.canReconnect
})

// ===== 方法 =====

/**
 * 初始化 WebSocket 連接
 */
async function initializeConnection() {
  if (!sessionStore.sessionId) {
    sessionStore.initializeSession()
  }
  
  try {
    await connect(sessionStore.sessionId, props.connectionConfig)
    console.log('🎯 WebSocket 客戶端已初始化')
  } catch (error) {
    console.error('❌ WebSocket 客戶端初始化失敗:', error)
  }
}

/**
 * 處理重連
 */
async function handleReconnect() {
  try {
    await reconnect(sessionStore.sessionId)
  } catch (error) {
    console.error('❌ 手動重連失敗:', error)
  }
}

/**
 * 清除錯誤
 */
function clearError() {
  sessionStore.clearError()
}

/**
 * 設置事件監聽器
 */
function setupEventListeners() {
  // 連接事件
  const unsubscribeConnected = addEventListener('connected', (data) => {
    console.log('✅ WebSocket 已連接:', data)
    emit('connected', data)
  })
  
  const unsubscribeDisconnected = addEventListener('disconnected', (data) => {
    console.log('🔌 WebSocket 已斷開:', data)
    emit('disconnected', data)
  })
  
  const unsubscribeError = addEventListener('error', (error) => {
    console.error('❌ WebSocket 錯誤:', error)
    emit('error', error)
  })
  
  // 通用消息事件
  const unsubscribeMessage = addEventListener('message', (data) => {
    console.log('📥 收到 WebSocket 消息:', data)
    emit('message', data)
  })
  
  // 會話分配事件
  const unsubscribeSessionAssigned = addEventListener('session_assigned', (data) => {
    console.log('🎯 會話已分配:', data)
    
    if (data.sessionId) {
      sessionStore.sessionId = data.sessionId
    }
    
    emit('session-assigned', data)
  })
  
  // 反饋提交事件
  const unsubscribeFeedbackSubmitted = addEventListener('feedback_submitted', (data) => {
    console.log('📝 反饋已提交:', data)
    
    // 更新反饋狀態
    feedbackStore.recordSubmission(true, data)
    feedbackStore.setSubmitStatus(false, 100)
    
    emit('feedback-submitted', data)
  })
  
  // 會話過期事件
  const unsubscribeSessionExpired = addEventListener('session_expired', (data) => {
    console.log('⏰ 會話已過期:', data)
    
    // 重置會話狀態
    sessionStore.resetSession()
    feedbackStore.resetForm()
    
    emit('session-expired', data)
  })
  
  // Pong 響應（心跳）
  const unsubscribePong = addEventListener('pong', (data) => {
    console.log('💓 收到心跳響應:', data)
    sessionStore.updateActivity()
  })
  
  // 錯誤事件
  const unsubscribeServerError = addEventListener('error', (data) => {
    console.error('🚨 服務器錯誤:', data)
    
    if (data.message) {
      sessionStore.setError(data)
    }
  })
  
  // 保存取消訂閱函數
  eventListeners.value = [
    unsubscribeConnected,
    unsubscribeDisconnected,
    unsubscribeError,
    unsubscribeMessage,
    unsubscribeSessionAssigned,
    unsubscribeFeedbackSubmitted,
    unsubscribeSessionExpired,
    unsubscribePong,
    unsubscribeServerError
  ]
}

/**
 * 清理事件監聽器
 */
function cleanupEventListeners() {
  eventListeners.value.forEach(unsubscribe => {
    if (typeof unsubscribe === 'function') {
      unsubscribe()
    }
  })
  eventListeners.value = []
}

/**
 * 發送會話心跳
 */
function sendHeartbeat() {
  if (isConnected.value) {
    sendMessage({
      type: 'heartbeat',
      sessionId: sessionStore.sessionId,
      timestamp: Date.now()
    })
  }
}

/**
 * 發送反饋數據
 */
function sendFeedback(feedbackData) {
  if (!isConnected.value) {
    feedbackStore.setError('WebSocket 未連接')
    return false
  }
  
  const message = {
    type: 'submit_feedback',
    sessionId: sessionStore.sessionId,
    data: feedbackData,
    timestamp: Date.now()
  }
  
  return sendMessage(message)
}

// ===== 監聽器 =====

// 監聽會話 ID 變化，重新連接
watch(() => sessionStore.sessionId, (newSessionId, oldSessionId) => {
  if (newSessionId && newSessionId !== oldSessionId) {
    if (isConnected.value) {
      disconnect()
    }
    
    if (props.autoConnect) {
      initializeConnection()
    }
  }
})

// 監聽連接狀態變化
watch(connectionState, (newState) => {
  sessionStore.setConnectionStatus(newState)
})

// ===== 生命週期 =====

onMounted(() => {
  console.log('🎯 WebSocket 客戶端組件已掛載')
  
  // 設置事件監聽器
  setupEventListeners()
  
  // 自動連接
  if (props.autoConnect) {
    initializeConnection()
  }
})

onUnmounted(() => {
  console.log('🎯 WebSocket 客戶端組件即將卸載')
  
  // 清理事件監聽器
  cleanupEventListeners()
  
  // 斷開連接
  disconnect()
})

// ===== 暴露方法給父組件 =====
defineExpose({
  connect: initializeConnection,
  disconnect,
  reconnect: handleReconnect,
  sendMessage,
  sendFeedback,
  sendHeartbeat,
  isConnected,
  isConnecting,
  connectionState
})
</script>

<style lang="scss" scoped>
.websocket-client {
  position: relative;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  font-size: 0.875rem;
  transition: all 0.3s ease;
  
  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    transition: background-color 0.3s ease;
  }
  
  .status-text {
    font-weight: 500;
  }
  
  .reconnect-btn {
    margin-left: auto;
    padding: 0.25rem 0.5rem;
    border: 1px solid currentColor;
    border-radius: 4px;
    background: transparent;
    color: inherit;
    font-size: 0.75rem;
    cursor: pointer;
    transition: all 0.2s ease;
    
    &:hover:not(:disabled) {
      background: currentColor;
      color: white;
    }
    
    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  }
  
  &.status-connected {
    background: rgba(16, 185, 129, 0.1);
    color: #059669;
    border: 1px solid rgba(16, 185, 129, 0.2);
    
    .status-dot {
      background: #10b981;
    }
  }
  
  &.status-connecting {
    background: rgba(245, 158, 11, 0.1);
    color: #d97706;
    border: 1px solid rgba(245, 158, 11, 0.2);
    
    .status-dot {
      background: #f59e0b;
      animation: pulse 1.5s ease-in-out infinite;
    }
  }
  
  &.status-disconnected {
    background: rgba(107, 114, 128, 0.1);
    color: #6b7280;
    border: 1px solid rgba(107, 114, 128, 0.2);
    
    .status-dot {
      background: #9ca3af;
    }
  }
  
  &.status-error {
    background: rgba(239, 68, 68, 0.1);
    color: #dc2626;
    border: 1px solid rgba(239, 68, 68, 0.2);
    
    .status-dot {
      background: #ef4444;
    }
  }
}

.error-alert {
  margin-top: 0.5rem;
  padding: 0.75rem;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 6px;
  color: #dc2626;
  
  .error-content {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  
  .error-icon {
    font-size: 1rem;
  }
  
  .error-message {
    flex: 1;
    font-size: 0.875rem;
  }
  
  .error-close {
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
      background: rgba(239, 68, 68, 0.1);
    }
  }
}

.queue-status {
  margin-top: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 6px;
  color: #2563eb;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  
  .queue-icon {
    font-size: 1rem;
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}
</style>
