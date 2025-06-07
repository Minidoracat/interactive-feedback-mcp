/**
 * 會話狀態管理 Store
 * 管理 WebSocket 連接狀態、會話 ID、超時處理等
 */

import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

export const useSessionStore = defineStore('session', () => {
  // ===== 狀態定義 =====
  
  // 會話基本信息
  const sessionId = ref('')
  const isConnected = ref(false)
  const connectionStatus = ref('disconnected') // 'disconnected', 'connecting', 'connected', 'reconnecting', 'error'
  
  // WebSocket 相關
  const websocket = ref(null)
  const reconnectAttempts = ref(0)
  const maxReconnectAttempts = ref(5)
  const reconnectDelay = ref(1000) // 毫秒
  
  // 會話超時管理
  const sessionTimeout = ref(30 * 60 * 1000) // 30分鐘，毫秒
  const sessionStartTime = ref(null)
  const lastActivityTime = ref(null)
  const timeoutWarningShown = ref(false)
  
  // 錯誤處理
  const lastError = ref(null)
  const errorHistory = ref([])

  // AI 工作狀態相關
  const aiWorkStatus = ref('idle') // 'idle', 'working', 'paused', 'completed', 'error'
  const currentTask = ref('')
  const taskProgress = ref(0)
  const taskStartTime = ref(null)

  // 對話歷史管理
  const conversationHistory = ref([])
  const maxConversationHistory = ref(50) // 最多保存 50 條對話記錄

  // 配置
  const config = ref({
    wsUrl: import.meta.env.DEV ? 'ws://localhost:8000' : window.location.origin.replace('http', 'ws'),
    heartbeatInterval: 30000, // 30秒心跳
    timeoutWarning: 5 * 60 * 1000, // 5分鐘前警告
  })

  // ===== 計算屬性 =====
  
  // 會話剩餘時間（毫秒）
  const sessionRemainingTime = computed(() => {
    if (!sessionStartTime.value) return 0
    const elapsed = Date.now() - lastActivityTime.value
    return Math.max(0, sessionTimeout.value - elapsed)
  })
  
  // 會話剩餘時間（格式化字符串）
  const sessionRemainingTimeFormatted = computed(() => {
    const remaining = sessionRemainingTime.value
    const minutes = Math.floor(remaining / 60000)
    const seconds = Math.floor((remaining % 60000) / 1000)
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  })
  
  // 是否需要顯示超時警告
  const shouldShowTimeoutWarning = computed(() => {
    return sessionRemainingTime.value <= config.value.timeoutWarning && 
           sessionRemainingTime.value > 0 && 
           !timeoutWarningShown.value
  })
  
  // 連接狀態描述
  const connectionStatusText = computed(() => {
    const statusMap = {
      'disconnected': '未連接',
      'connecting': '連接中...',
      'connected': '已連接',
      'reconnecting': '重新連接中...',
      'error': '連接錯誤'
    }
    return statusMap[connectionStatus.value] || '未知狀態'
  })
  
  // 是否可以重連
  const canReconnect = computed(() => {
    return reconnectAttempts.value < maxReconnectAttempts.value &&
           connectionStatus.value !== 'connecting'
  })

  // AI 工作持續時間
  const aiWorkDuration = computed(() => {
    if (!taskStartTime.value) return 0
    return Date.now() - taskStartTime.value
  })

  // AI 工作狀態描述
  const aiWorkStatusText = computed(() => {
    const statusMap = {
      'idle': '空閒',
      'working': '工作中',
      'paused': '已暫停',
      'completed': '已完成',
      'error': '錯誤'
    }
    return statusMap[aiWorkStatus.value] || '未知狀態'
  })

  // 最近的對話記錄
  const recentConversations = computed(() => {
    return conversationHistory.value.slice(0, 10)
  })

  // ===== 動作方法 =====
  
  /**
   * 生成新的會話 ID
   */
  function generateSessionId() {
    const timestamp = Date.now()
    const random = Math.random().toString(36).substr(2, 9)
    return `feedback_${timestamp}_${random}`
  }
  
  /**
   * 初始化會話
   */
  function initializeSession() {
    sessionId.value = generateSessionId()
    sessionStartTime.value = Date.now()
    lastActivityTime.value = Date.now()
    timeoutWarningShown.value = false
    
    console.log('🎯 會話已初始化:', sessionId.value)
  }
  
  /**
   * 更新活動時間
   */
  function updateActivity() {
    lastActivityTime.value = Date.now()
    timeoutWarningShown.value = false
  }
  
  /**
   * 設置連接狀態
   */
  function setConnectionStatus(status) {
    connectionStatus.value = status
    isConnected.value = status === 'connected'
    
    if (status === 'connected') {
      reconnectAttempts.value = 0
      clearError()
    }
    
    console.log('🔌 連接狀態更新:', status)
  }
  
  /**
   * 設置錯誤
   */
  function setError(error) {
    const errorInfo = {
      message: error.message || error,
      timestamp: Date.now(),
      type: error.type || 'unknown'
    }
    
    lastError.value = errorInfo
    errorHistory.value.unshift(errorInfo)
    
    // 保持錯誤歷史記錄不超過 10 條
    if (errorHistory.value.length > 10) {
      errorHistory.value = errorHistory.value.slice(0, 10)
    }
    
    console.error('❌ 會話錯誤:', errorInfo)
  }
  
  /**
   * 清除錯誤
   */
  function clearError() {
    lastError.value = null
  }
  
  /**
   * 重置會話
   */
  function resetSession() {
    sessionId.value = ''
    sessionStartTime.value = null
    lastActivityTime.value = null
    timeoutWarningShown.value = false
    setConnectionStatus('disconnected')
    clearError()
    reconnectAttempts.value = 0

    // 重置 AI 工作狀態
    setAIWorkStatus('idle')

    // 可選：是否清除對話歷史（通常保留）
    // clearConversationHistory()

    console.log('🔄 會話已重置')
  }
  
  /**
   * 標記超時警告已顯示
   */
  function markTimeoutWarningShown() {
    timeoutWarningShown.value = true
  }
  
  /**
   * 延長會話
   */
  function extendSession() {
    updateActivity()
    console.log('⏰ 會話已延長')
  }
  
  /**
   * 檢查會話是否過期
   */
  function checkSessionExpiry() {
    if (sessionRemainingTime.value <= 0 && sessionStartTime.value) {
      console.log('⏰ 會話已過期')
      resetSession()
      return true
    }
    return false
  }

  /**
   * 設置 AI 工作狀態
   */
  function setAIWorkStatus(status, task = '') {
    aiWorkStatus.value = status

    if (task) {
      currentTask.value = task
    }

    if (status === 'working' && !taskStartTime.value) {
      taskStartTime.value = Date.now()
      taskProgress.value = 0
    } else if (status === 'completed' || status === 'error') {
      taskProgress.value = status === 'completed' ? 100 : 0
    } else if (status === 'idle') {
      currentTask.value = ''
      taskProgress.value = 0
      taskStartTime.value = null
    }

    console.log('🤖 AI 工作狀態更新:', status, task)
  }

  /**
   * 更新任務進度
   */
  function updateTaskProgress(progress) {
    taskProgress.value = Math.max(0, Math.min(100, progress))
    console.log('📊 任務進度更新:', taskProgress.value + '%')
  }

  /**
   * 添加對話記錄
   */
  function addConversation(conversation) {
    const conversationItem = {
      id: Date.now() + Math.random(),
      timestamp: Date.now(),
      type: conversation.type || 'message', // 'message', 'feedback', 'quick-response', 'ai-request'
      content: conversation.content || '',
      sender: conversation.sender || 'unknown', // 'ai', 'human'
      metadata: conversation.metadata || {}
    }

    conversationHistory.value.unshift(conversationItem)

    // 保持對話歷史記錄不超過最大限制
    if (conversationHistory.value.length > maxConversationHistory.value) {
      conversationHistory.value = conversationHistory.value.slice(0, maxConversationHistory.value)
    }

    console.log('💬 對話記錄已添加:', conversationItem)
    updateActivity()
  }

  /**
   * 清除對話歷史
   */
  function clearConversationHistory() {
    conversationHistory.value = []
    console.log('🗑️ 對話歷史已清除')
  }

  /**
   * 獲取特定類型的對話記錄
   */
  function getConversationsByType(type) {
    return conversationHistory.value.filter(conv => conv.type === type)
  }

  // ===== 監聽器 =====
  
  // 監聽會話超時警告
  watch(shouldShowTimeoutWarning, (shouldShow) => {
    if (shouldShow) {
      console.warn('⚠️ 會話即將超時，剩餘時間:', sessionRemainingTimeFormatted.value)
    }
  })
  
  // 監聽連接狀態變化
  watch(connectionStatus, (newStatus, oldStatus) => {
    console.log(`🔌 連接狀態變化: ${oldStatus} -> ${newStatus}`)
  })

  // ===== 返回 Store API =====
  return {
    // 狀態
    sessionId,
    isConnected,
    connectionStatus,
    websocket,
    reconnectAttempts,
    maxReconnectAttempts,
    reconnectDelay,
    sessionTimeout,
    sessionStartTime,
    lastActivityTime,
    timeoutWarningShown,
    lastError,
    errorHistory,
    config,

    // AI 工作狀態
    aiWorkStatus,
    currentTask,
    taskProgress,
    taskStartTime,

    // 對話歷史
    conversationHistory,
    maxConversationHistory,

    // 計算屬性
    sessionRemainingTime,
    sessionRemainingTimeFormatted,
    shouldShowTimeoutWarning,
    connectionStatusText,
    canReconnect,
    aiWorkDuration,
    aiWorkStatusText,
    recentConversations,

    // 方法
    generateSessionId,
    initializeSession,
    updateActivity,
    setConnectionStatus,
    setError,
    clearError,
    resetSession,
    markTimeoutWarningShown,
    extendSession,
    checkSessionExpiry,

    // AI 工作狀態方法
    setAIWorkStatus,
    updateTaskProgress,

    // 對話歷史方法
    addConversation,
    clearConversationHistory,
    getConversationsByType
  }
})
