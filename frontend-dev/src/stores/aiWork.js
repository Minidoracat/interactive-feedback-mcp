/**
 * AI 工作狀態管理 Store
 * 管理 AI 當前工作狀態、請求、進度和工作歷史
 * 專為 AI-人類協作工作流程設計
 */

import { defineStore } from 'pinia'
import { ref, computed, reactive } from 'vue'

export const useAIWorkStore = defineStore('aiWork', () => {
  // ===== 狀態定義 =====
  
  // AI 工作狀態
  const workStatus = ref('idle') // 'idle', 'working', 'paused', 'completed', 'error'
  const currentTask = ref('')
  const taskDescription = ref('')
  const progress = ref(0)
  const startTime = ref(null)
  const estimatedDuration = ref(null)
  
  // AI 請求
  const currentRequest = reactive({
    id: null,
    type: '', // 'review', 'code', 'question', 'feedback'
    content: '',
    codeSnippet: null,
    priority: 'medium', // 'low', 'medium', 'high', 'urgent'
    timestamp: null,
    metadata: {}
  })
  
  // 工作歷史
  const workHistory = ref([])
  const maxHistoryItems = ref(50)
  
  // AI 請求歷史
  const requestHistory = ref([])
  const maxRequestHistory = ref(30)
  
  // 錯誤處理
  const lastError = ref(null)
  const errorHistory = ref([])
  
  // 配置
  const config = ref({
    autoUpdateInterval: 5000, // 5秒自動更新
    progressUpdateThreshold: 1, // 進度更新閾值 1%
    maxRetries: 3
  })

  // ===== 計算屬性 =====
  
  // 工作持續時間
  const workDuration = computed(() => {
    if (!startTime.value) return 0
    return Date.now() - startTime.value
  })
  
  // 格式化的工作持續時間
  const workDurationFormatted = computed(() => {
    const duration = workDuration.value
    const minutes = Math.floor(duration / 60000)
    const seconds = Math.floor((duration % 60000) / 1000)
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  })
  
  // 工作狀態描述
  const workStatusText = computed(() => {
    const statusMap = {
      'idle': '空閒',
      'working': '工作中',
      'paused': '已暫停',
      'completed': '已完成',
      'error': '錯誤'
    }
    return statusMap[workStatus.value] || '未知狀態'
  })
  
  // 預計完成時間
  const estimatedCompletionTime = computed(() => {
    if (!startTime.value || !estimatedDuration.value) return null
    return startTime.value + estimatedDuration.value
  })
  
  // 是否超時
  const isOverdue = computed(() => {
    if (!estimatedCompletionTime.value) return false
    return Date.now() > estimatedCompletionTime.value
  })
  
  // 最近的工作歷史
  const recentWorkHistory = computed(() => {
    return workHistory.value.slice(0, 10)
  })
  
  // 當前請求是否有效
  const hasActiveRequest = computed(() => {
    return currentRequest.id && currentRequest.content
  })

  // ===== 工作狀態管理 =====
  
  /**
   * 開始新任務
   */
  function startTask(task, description = '', estimatedDurationMs = null) {
    workStatus.value = 'working'
    currentTask.value = task
    taskDescription.value = description
    progress.value = 0
    startTime.value = Date.now()
    estimatedDuration.value = estimatedDurationMs
    
    // 添加到工作歷史
    addWorkHistoryItem({
      type: 'started',
      title: task,
      description: description,
      timestamp: Date.now()
    })
    
    console.log('🚀 AI 任務已開始:', task)
  }
  
  /**
   * 更新任務進度
   */
  function updateProgress(newProgress) {
    const oldProgress = progress.value
    progress.value = Math.max(0, Math.min(100, newProgress))
    
    // 只有進度變化超過閾值才記錄
    if (Math.abs(progress.value - oldProgress) >= config.value.progressUpdateThreshold) {
      addWorkHistoryItem({
        type: 'progress',
        title: `進度更新: ${progress.value}%`,
        description: currentTask.value,
        timestamp: Date.now()
      })
    }
    
    console.log('📊 任務進度更新:', progress.value + '%')
  }
  
  /**
   * 暫停任務
   */
  function pauseTask() {
    if (workStatus.value === 'working') {
      workStatus.value = 'paused'
      
      addWorkHistoryItem({
        type: 'paused',
        title: '任務已暫停',
        description: currentTask.value,
        timestamp: Date.now()
      })
      
      console.log('⏸️ AI 任務已暫停')
    }
  }
  
  /**
   * 恢復任務
   */
  function resumeTask() {
    if (workStatus.value === 'paused') {
      workStatus.value = 'working'
      
      addWorkHistoryItem({
        type: 'resumed',
        title: '任務已恢復',
        description: currentTask.value,
        timestamp: Date.now()
      })
      
      console.log('▶️ AI 任務已恢復')
    }
  }
  
  /**
   * 完成任務
   */
  function completeTask() {
    workStatus.value = 'completed'
    progress.value = 100
    
    addWorkHistoryItem({
      type: 'completed',
      title: '任務已完成',
      description: currentTask.value,
      timestamp: Date.now()
    })
    
    console.log('✅ AI 任務已完成:', currentTask.value)
    
    // 延遲重置狀態
    setTimeout(() => {
      resetWorkStatus()
    }, 3000)
  }
  
  /**
   * 任務出錯
   */
  function errorTask(error) {
    workStatus.value = 'error'
    setError(error)
    
    addWorkHistoryItem({
      type: 'error',
      title: '任務出錯',
      description: error.message || error,
      timestamp: Date.now()
    })
    
    console.error('❌ AI 任務出錯:', error)
  }
  
  /**
   * 重置工作狀態
   */
  function resetWorkStatus() {
    workStatus.value = 'idle'
    currentTask.value = ''
    taskDescription.value = ''
    progress.value = 0
    startTime.value = null
    estimatedDuration.value = null
    clearError()
    
    console.log('🔄 AI 工作狀態已重置')
  }

  // ===== AI 請求管理 =====
  
  /**
   * 創建新的 AI 請求
   */
  function createRequest(type, content, options = {}) {
    const request = {
      id: Date.now() + Math.random(),
      type,
      content,
      codeSnippet: options.codeSnippet || null,
      priority: options.priority || 'medium',
      timestamp: Date.now(),
      metadata: options.metadata || {}
    }
    
    // 更新當前請求
    Object.assign(currentRequest, request)
    
    // 添加到請求歷史
    requestHistory.value.unshift({ ...request })
    
    // 保持請求歷史不超過最大限制
    if (requestHistory.value.length > maxRequestHistory.value) {
      requestHistory.value = requestHistory.value.slice(0, maxRequestHistory.value)
    }
    
    console.log('📝 AI 請求已創建:', request)
    return request
  }
  
  /**
   * 清除當前請求
   */
  function clearCurrentRequest() {
    Object.assign(currentRequest, {
      id: null,
      type: '',
      content: '',
      codeSnippet: null,
      priority: 'medium',
      timestamp: null,
      metadata: {}
    })
    
    console.log('🗑️ 當前 AI 請求已清除')
  }

  // ===== 工作歷史管理 =====
  
  /**
   * 添加工作歷史項目
   */
  function addWorkHistoryItem(item) {
    const historyItem = {
      id: Date.now() + Math.random(),
      ...item
    }
    
    workHistory.value.unshift(historyItem)
    
    // 保持工作歷史不超過最大限制
    if (workHistory.value.length > maxHistoryItems.value) {
      workHistory.value = workHistory.value.slice(0, maxHistoryItems.value)
    }
  }
  
  /**
   * 清除工作歷史
   */
  function clearWorkHistory() {
    workHistory.value = []
    console.log('🗑️ AI 工作歷史已清除')
  }
  
  /**
   * 獲取特定類型的工作歷史
   */
  function getWorkHistoryByType(type) {
    return workHistory.value.filter(item => item.type === type)
  }

  // ===== 錯誤處理 =====
  
  /**
   * 設置錯誤
   */
  function setError(error) {
    const errorInfo = {
      message: error.message || error,
      timestamp: Date.now(),
      type: error.type || 'unknown',
      task: currentTask.value
    }
    
    lastError.value = errorInfo
    errorHistory.value.unshift(errorInfo)
    
    // 保持錯誤歷史記錄不超過 10 條
    if (errorHistory.value.length > 10) {
      errorHistory.value = errorHistory.value.slice(0, 10)
    }
    
    console.error('❌ AI 工作錯誤:', errorInfo)
  }
  
  /**
   * 清除錯誤
   */
  function clearError() {
    lastError.value = null
  }

  // ===== 返回 Store API =====
  return {
    // 狀態
    workStatus,
    currentTask,
    taskDescription,
    progress,
    startTime,
    estimatedDuration,
    currentRequest,
    workHistory,
    requestHistory,
    lastError,
    errorHistory,
    config,
    
    // 計算屬性
    workDuration,
    workDurationFormatted,
    workStatusText,
    estimatedCompletionTime,
    isOverdue,
    recentWorkHistory,
    hasActiveRequest,
    
    // 工作狀態方法
    startTask,
    updateProgress,
    pauseTask,
    resumeTask,
    completeTask,
    errorTask,
    resetWorkStatus,
    
    // AI 請求方法
    createRequest,
    clearCurrentRequest,
    
    // 工作歷史方法
    addWorkHistoryItem,
    clearWorkHistory,
    getWorkHistoryByType,
    
    // 錯誤處理方法
    setError,
    clearError
  }
})
