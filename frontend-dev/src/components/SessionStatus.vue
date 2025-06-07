<!--
  會話狀態組件
  顯示當前會話狀態、連接狀態、會話 ID、超時倒計時等信息
-->

<template>
  <div class="session-status" :class="statusClass">
    <!-- 主要狀態區域 -->
    <div class="status-main">
      <!-- 連接狀態指示器 -->
      <div class="connection-indicator">
        <div class="status-dot" :class="connectionStatusClass"></div>
        <div class="status-info">
          <div class="status-title">{{ connectionStatusText }}</div>
          <div v-if="sessionId" class="session-id">
            <span class="label">會話 ID:</span>
            <code class="id-value">{{ sessionId }}</code>
            <button 
              @click="copySessionId" 
              class="copy-btn"
              :title="copyButtonTitle"
            >
              {{ copyButtonText }}
            </button>
          </div>
        </div>
      </div>
      
      <!-- 會話時間信息 -->
      <div v-if="sessionStartTime" class="session-time">
        <div class="time-item">
          <span class="time-label">開始時間:</span>
          <span class="time-value">{{ sessionStartTimeFormatted }}</span>
        </div>
        <div class="time-item">
          <span class="time-label">剩餘時間:</span>
          <span class="time-value" :class="timeWarningClass">
            {{ sessionRemainingTimeFormatted }}
          </span>
        </div>
      </div>
    </div>
    
    <!-- 操作按鈕區域 -->
    <div class="status-actions">
      <!-- 延長會話按鈕 -->
      <button 
        v-if="canExtendSession"
        @click="handleExtendSession"
        class="action-btn extend-btn"
        :disabled="isExtending"
      >
        <span class="btn-icon">⏰</span>
        {{ isExtending ? '延長中...' : '延長會話' }}
      </button>
      
      <!-- 重新連接按鈕 -->
      <button 
        v-if="canReconnect"
        @click="handleReconnect"
        class="action-btn reconnect-btn"
        :disabled="isConnecting"
      >
        <span class="btn-icon">🔄</span>
        {{ isConnecting ? '連接中...' : '重新連接' }}
      </button>
      
      <!-- 重置會話按鈕 -->
      <button 
        v-if="canResetSession"
        @click="handleResetSession"
        class="action-btn reset-btn"
        :disabled="isResetting"
      >
        <span class="btn-icon">🔄</span>
        {{ isResetting ? '重置中...' : '重置會話' }}
      </button>
    </div>
    
    <!-- 超時警告 -->
    <div 
      v-if="shouldShowTimeoutWarning"
      class="timeout-warning"
    >
      <div class="warning-content">
        <span class="warning-icon">⚠️</span>
        <div class="warning-text">
          <div class="warning-title">會話即將過期</div>
          <div class="warning-message">
            您的會話將在 {{ sessionRemainingTimeFormatted }} 後過期，請及時保存您的工作。
          </div>
        </div>
        <button 
          @click="handleExtendSession"
          class="warning-action"
        >
          延長會話
        </button>
        <button 
          @click="dismissTimeoutWarning"
          class="warning-dismiss"
        >
          ×
        </button>
      </div>
    </div>
    
    <!-- 錯誤信息 -->
    <div 
      v-if="lastError && showError"
      class="error-message"
    >
      <div class="error-content">
        <span class="error-icon">❌</span>
        <div class="error-text">
          <div class="error-title">連接錯誤</div>
          <div class="error-detail">{{ lastError.message }}</div>
        </div>
        <button 
          @click="clearError"
          class="error-dismiss"
        >
          ×
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useSessionStore } from '@/stores/session'

// ===== Props =====
const props = defineProps({
  // 是否顯示詳細信息
  showDetails: {
    type: Boolean,
    default: true
  },
  
  // 是否顯示操作按鈕
  showActions: {
    type: Boolean,
    default: true
  },
  
  // 是否顯示錯誤信息
  showError: {
    type: Boolean,
    default: true
  },
  
  // 緊湊模式
  compact: {
    type: Boolean,
    default: false
  }
})

// ===== Emits =====
const emit = defineEmits([
  'extend-session',
  'reconnect',
  'reset-session',
  'copy-session-id',
  'timeout-warning-dismissed'
])

// ===== Store =====
const sessionStore = useSessionStore()

// ===== 狀態 =====
const isExtending = ref(false)
const isResetting = ref(false)
const copyButtonText = ref('📋')
const copyButtonTitle = ref('複製會話 ID')

// ===== 計算屬性 =====
const sessionId = computed(() => sessionStore.sessionId)
const isConnected = computed(() => sessionStore.isConnected)
const isConnecting = computed(() => sessionStore.connectionStatus === 'connecting')
const connectionStatus = computed(() => sessionStore.connectionStatus)
const connectionStatusText = computed(() => sessionStore.connectionStatusText)
const sessionStartTime = computed(() => sessionStore.sessionStartTime)
const sessionRemainingTime = computed(() => sessionStore.sessionRemainingTime)
const sessionRemainingTimeFormatted = computed(() => sessionStore.sessionRemainingTimeFormatted)
const shouldShowTimeoutWarning = computed(() => sessionStore.shouldShowTimeoutWarning)
const lastError = computed(() => sessionStore.lastError)
const canReconnect = computed(() => sessionStore.canReconnect)

// 狀態樣式類
const statusClass = computed(() => {
  return {
    'status-connected': isConnected.value,
    'status-connecting': isConnecting.value,
    'status-disconnected': !isConnected.value && !isConnecting.value,
    'status-error': connectionStatus.value === 'error',
    'status-compact': props.compact
  }
})

const connectionStatusClass = computed(() => {
  return {
    'dot-connected': isConnected.value,
    'dot-connecting': isConnecting.value,
    'dot-disconnected': !isConnected.value && !isConnecting.value,
    'dot-error': connectionStatus.value === 'error'
  }
})

// 時間警告樣式
const timeWarningClass = computed(() => {
  const remaining = sessionRemainingTime.value
  return {
    'time-warning': remaining <= 5 * 60 * 1000 && remaining > 2 * 60 * 1000, // 5-2分鐘
    'time-critical': remaining <= 2 * 60 * 1000 && remaining > 0 // 2分鐘內
  }
})

// 會話開始時間格式化
const sessionStartTimeFormatted = computed(() => {
  if (!sessionStartTime.value) return ''
  return new Date(sessionStartTime.value).toLocaleString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
})

// 操作按鈕顯示條件
const canExtendSession = computed(() => {
  return props.showActions && 
         sessionId.value && 
         sessionRemainingTime.value > 0 &&
         sessionRemainingTime.value < 10 * 60 * 1000 // 剩餘時間少於10分鐘時顯示
})

const canResetSession = computed(() => {
  return props.showActions && 
         (connectionStatus.value === 'error' || !isConnected.value)
})

// ===== 方法 =====

/**
 * 處理延長會話
 */
async function handleExtendSession() {
  if (isExtending.value) return
  
  isExtending.value = true
  
  try {
    sessionStore.extendSession()
    emit('extend-session')
    
    // 模擬延長操作
    await new Promise(resolve => setTimeout(resolve, 500))
    
    console.log('✅ 會話已延長')
  } catch (error) {
    console.error('❌ 延長會話失敗:', error)
    sessionStore.setError(error)
  } finally {
    isExtending.value = false
  }
}

/**
 * 處理重新連接
 */
function handleReconnect() {
  emit('reconnect')
}

/**
 * 處理重置會話
 */
async function handleResetSession() {
  if (isResetting.value) return
  
  if (!confirm('確定要重置會話嗎？這將清除當前的所有數據。')) {
    return
  }
  
  isResetting.value = true
  
  try {
    sessionStore.resetSession()
    emit('reset-session')
    
    // 模擬重置操作
    await new Promise(resolve => setTimeout(resolve, 500))
    
    console.log('✅ 會話已重置')
  } catch (error) {
    console.error('❌ 重置會話失敗:', error)
    sessionStore.setError(error)
  } finally {
    isResetting.value = false
  }
}

/**
 * 複製會話 ID
 */
async function copySessionId() {
  if (!sessionId.value) return
  
  try {
    await navigator.clipboard.writeText(sessionId.value)
    
    copyButtonText.value = '✅'
    copyButtonTitle.value = '已複製'
    
    setTimeout(() => {
      copyButtonText.value = '📋'
      copyButtonTitle.value = '複製會話 ID'
    }, 2000)
    
    emit('copy-session-id', sessionId.value)
    console.log('📋 會話 ID 已複製到剪貼板')
  } catch (error) {
    console.error('❌ 複製失敗:', error)
    
    copyButtonText.value = '❌'
    copyButtonTitle.value = '複製失敗'
    
    setTimeout(() => {
      copyButtonText.value = '📋'
      copyButtonTitle.value = '複製會話 ID'
    }, 2000)
  }
}

/**
 * 關閉超時警告
 */
function dismissTimeoutWarning() {
  sessionStore.markTimeoutWarningShown()
  emit('timeout-warning-dismissed')
}

/**
 * 清除錯誤
 */
function clearError() {
  sessionStore.clearError()
}

// ===== 監聽器 =====

// 監聽會話過期
watch(sessionRemainingTime, (remaining) => {
  if (remaining <= 0 && sessionStartTime.value) {
    console.log('⏰ 會話已過期')
    // 這裡可以添加過期處理邏輯
  }
})

// ===== 生命週期 =====

onMounted(() => {
  console.log('🎯 會話狀態組件已掛載')
})
</script>

<style lang="scss" scoped>
.session-status {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  
  &.status-compact {
    padding: 1rem;
    
    .status-main {
      flex-direction: row;
      align-items: center;
      gap: 1rem;
    }
    
    .session-time {
      flex-direction: row;
      gap: 1rem;
    }
  }
}

.status-main {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1rem;
}

.connection-indicator {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.status-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  transition: all 0.3s ease;
  
  &.dot-connected {
    background: #10b981;
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2);
  }
  
  &.dot-connecting {
    background: #f59e0b;
    animation: pulse 1.5s ease-in-out infinite;
  }
  
  &.dot-disconnected {
    background: #9ca3af;
  }
  
  &.dot-error {
    background: #ef4444;
    box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.2);
  }
}

.status-info {
  flex: 1;
}

.status-title {
  font-weight: 600;
  font-size: 1rem;
  color: #1f2937;
  margin-bottom: 0.25rem;
}

.session-id {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #6b7280;
  
  .label {
    font-weight: 500;
  }
  
  .id-value {
    background: #f3f4f6;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-family: 'Monaco', 'Menlo', monospace;
    font-size: 0.75rem;
    color: #374151;
  }
  
  .copy-btn {
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.25rem;
    border-radius: 4px;
    transition: background-color 0.2s ease;
    
    &:hover {
      background: #f3f4f6;
    }
  }
}

.session-time {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.time-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.875rem;
}

.time-label {
  color: #6b7280;
  font-weight: 500;
}

.time-value {
  font-weight: 600;
  color: #374151;
  font-family: 'Monaco', 'Menlo', monospace;
  
  &.time-warning {
    color: #f59e0b;
  }
  
  &.time-critical {
    color: #ef4444;
    animation: blink 1s ease-in-out infinite;
  }
}

.status-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  color: #374151;
  font-size: 0.875rem;
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
    font-size: 1rem;
  }
  
  &.extend-btn {
    border-color: #10b981;
    color: #059669;
    
    &:hover:not(:disabled) {
      background: rgba(16, 185, 129, 0.05);
    }
  }
  
  &.reconnect-btn {
    border-color: #3b82f6;
    color: #2563eb;
    
    &:hover:not(:disabled) {
      background: rgba(59, 130, 246, 0.05);
    }
  }
  
  &.reset-btn {
    border-color: #ef4444;
    color: #dc2626;
    
    &:hover:not(:disabled) {
      background: rgba(239, 68, 68, 0.05);
    }
  }
}

.timeout-warning {
  margin-top: 1rem;
  padding: 1rem;
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: 8px;
  color: #92400e;
}

.warning-content {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.warning-icon {
  font-size: 1.25rem;
  margin-top: 0.125rem;
}

.warning-text {
  flex: 1;
}

.warning-title {
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.warning-message {
  font-size: 0.875rem;
  line-height: 1.4;
}

.warning-action {
  padding: 0.375rem 0.75rem;
  background: #f59e0b;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s ease;
  
  &:hover {
    background: #d97706;
  }
}

.warning-dismiss {
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
    background: rgba(245, 158, 11, 0.2);
  }
}

.error-message {
  margin-top: 1rem;
  padding: 1rem;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  color: #991b1b;
}

.error-content {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.error-icon {
  font-size: 1.25rem;
  margin-top: 0.125rem;
}

.error-text {
  flex: 1;
}

.error-title {
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.error-detail {
  font-size: 0.875rem;
  line-height: 1.4;
}

.error-dismiss {
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
    background: rgba(239, 68, 68, 0.2);
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.1);
  }
}

@keyframes blink {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

@media (max-width: 768px) {
  .session-status {
    padding: 1rem;
  }
  
  .status-actions {
    flex-direction: column;
  }
  
  .action-btn {
    justify-content: center;
  }
  
  .warning-content,
  .error-content {
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .warning-action {
    align-self: flex-start;
  }
}
</style>
