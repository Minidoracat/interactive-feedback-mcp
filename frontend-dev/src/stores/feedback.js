/**
 * 人類回饋狀態管理 Store
 * 管理簡化的文字回饋、快速回應、圖片上傳等
 * 專為 AI-人類協作工作流程設計
 */

import { defineStore } from 'pinia'
import { ref, computed, reactive } from 'vue'

export const useFeedbackStore = defineStore('feedback', () => {
  // ===== 狀態定義 =====
  
  // 簡化的回饋數據
  const feedbackData = reactive({
    text: '',
    type: 'text', // 'text', 'quick', 'mixed'
    metadata: {}
  })

  // 快速回應狀態
  const quickResponseHistory = ref([])
  const lastQuickResponse = ref(null)
  
  // 文件上傳
  const uploadedFiles = ref([])
  const uploadProgress = ref({})
  const maxFileSize = ref(10 * 1024 * 1024) // 10MB
  const allowedFileTypes = ref(['image/jpeg', 'image/png', 'image/gif', 'image/webp'])
  const maxFiles = ref(5)
  
  // 提交狀態
  const isSubmitting = ref(false)
  const submitProgress = ref(0)
  const lastSubmitTime = ref(null)
  const submitHistory = ref([])
  
  // 驗證狀態
  const validationErrors = ref({})
  const isFormValid = ref(false)
  
  // 錯誤處理
  const lastError = ref(null)
  const errorHistory = ref([])
  
  // UI 狀態
  const isDirty = ref(false) // 表單是否有未保存的更改
  const charCount = ref(0)
  const maxCharCount = ref(2000)

  // ===== 計算屬性 =====
  
  // 回饋是否為空
  const isFeedbackEmpty = computed(() => {
    return !feedbackData.text.trim() && uploadedFiles.value.length === 0
  })

  // 字符計數是否超限
  const isCharCountExceeded = computed(() => {
    return charCount.value > maxCharCount.value
  })
  
  // 文件總大小
  const totalFileSize = computed(() => {
    return uploadedFiles.value.reduce((total, file) => total + file.size, 0)
  })
  
  // 文件總大小（格式化）
  const totalFileSizeFormatted = computed(() => {
    return formatFileSize(totalFileSize.value)
  })
  
  // 是否可以添加更多文件
  const canAddMoreFiles = computed(() => {
    return uploadedFiles.value.length < maxFiles.value
  })
  
  // 回饋摘要
  const feedbackSummary = computed(() => {
    return {
      textLength: feedbackData.text.length,
      type: feedbackData.type,
      fileCount: uploadedFiles.value.length,
      totalSize: totalFileSizeFormatted.value,
      hasContent: !isFeedbackEmpty.value
    }
  })
  
  // 驗證錯誤數量
  const validationErrorCount = computed(() => {
    return Object.keys(validationErrors.value).length
  })
  
  // 是否有正在上傳的文件
  const hasUploadingFiles = computed(() => {
    return Object.values(uploadProgress.value).some(progress => progress < 100)
  })

  // ===== 工具方法 =====
  
  /**
   * 格式化文件大小
   */
  function formatFileSize(bytes) {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }
  
  /**
   * 生成文件 ID
   */
  function generateFileId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2)
  }

  // ===== 回饋操作 =====

  /**
   * 更新回饋文字
   */
  function updateFeedbackText(text) {
    feedbackData.text = text
    charCount.value = text.length

    // 自動判斷類型
    if (text.trim() && uploadedFiles.value.length > 0) {
      feedbackData.type = 'mixed'
    } else if (text.trim()) {
      feedbackData.type = 'text'
    }

    markDirty()
    validateFeedback()
  }

  /**
   * 發送快速回應
   */
  function sendQuickResponse(responseType, responseText) {
    const quickResponse = {
      id: Date.now(),
      type: responseType, // 'confirm', 'reject', 'need-info', 'later'
      text: responseText,
      timestamp: Date.now()
    }

    quickResponseHistory.value.unshift(quickResponse)
    lastQuickResponse.value = quickResponse

    // 保持快速回應歷史不超過 20 條
    if (quickResponseHistory.value.length > 20) {
      quickResponseHistory.value = quickResponseHistory.value.slice(0, 20)
    }

    console.log('⚡ 快速回應已發送:', quickResponse)
    return quickResponse
  }
  
  /**
   * 標記表單為已修改
   */
  function markDirty() {
    isDirty.value = true
  }
  
  /**
   * 標記表單為乾淨（已保存）
   */
  function markClean() {
    isDirty.value = false
  }

  // ===== 文件操作 =====
  
  /**
   * 添加文件
   */
  function addFile(file) {
    if (!canAddMoreFiles.value) {
      setError('文件數量已達上限')
      return false
    }
    
    if (!allowedFileTypes.value.includes(file.type)) {
      setError('不支持的文件類型')
      return false
    }
    
    if (file.size > maxFileSize.value) {
      setError('文件大小超過限制')
      return false
    }
    
    const fileInfo = {
      id: generateFileId(),
      file: file,
      name: file.name,
      size: file.size,
      type: file.type,
      preview: null,
      uploadedAt: Date.now()
    }
    
    // 如果是圖片，生成預覽
    if (file.type.startsWith('image/')) {
      const reader = new FileReader()
      reader.onload = (e) => {
        fileInfo.preview = e.target.result
      }
      reader.readAsDataURL(file)
    }
    
    uploadedFiles.value.push(fileInfo)

    // 自動更新回饋類型
    if (feedbackData.text.trim() && uploadedFiles.value.length > 0) {
      feedbackData.type = 'mixed'
    } else if (uploadedFiles.value.length > 0) {
      feedbackData.type = 'mixed'
    }

    markDirty()

    console.log('📁 文件已添加:', fileInfo.name)
    return true
  }
  
  /**
   * 移除文件
   */
  function removeFile(fileId) {
    const index = uploadedFiles.value.findIndex(f => f.id === fileId)
    if (index > -1) {
      const file = uploadedFiles.value[index]
      uploadedFiles.value.splice(index, 1)
      
      // 清理上傳進度
      if (uploadProgress.value[fileId]) {
        delete uploadProgress.value[fileId]
      }
      
      // 自動更新回饋類型
      if (feedbackData.text.trim() && uploadedFiles.value.length > 0) {
        feedbackData.type = 'mixed'
      } else if (feedbackData.text.trim()) {
        feedbackData.type = 'text'
      } else if (uploadedFiles.value.length > 0) {
        feedbackData.type = 'mixed'
      }

      markDirty()
      console.log('🗑️ 文件已移除:', file.name)
    }
  }
  
  /**
   * 設置文件上傳進度
   */
  function setFileUploadProgress(fileId, progress) {
    uploadProgress.value[fileId] = Math.min(100, Math.max(0, progress))
  }

  // ===== 驗證 =====

  /**
   * 驗證回饋內容
   */
  function validateFeedback() {
    const errors = {}

    // 檢查文字長度
    if (feedbackData.text.length > maxCharCount.value) {
      errors.text = `回饋內容不能超過 ${maxCharCount.value} 字符`
    }

    // 檢查是否有內容
    if (isFeedbackEmpty.value) {
      errors.general = '請至少輸入回饋內容或上傳圖片'
    } else {
      delete errors.general
    }

    // 更新驗證錯誤
    validationErrors.value = errors
    updateFormValidation()

    return Object.keys(errors).length === 0
  }
  
  /**
   * 更新表單驗證狀態
   */
  function updateFormValidation() {
    isFormValid.value = Object.keys(validationErrors.value).length === 0
  }
  
  /**
   * 清除驗證錯誤
   */
  function clearValidationErrors() {
    validationErrors.value = {}
    updateFormValidation()
  }

  // ===== 提交處理 =====
  
  /**
   * 準備提交數據
   */
  function prepareSubmitData() {
    return {
      ...feedbackData,
      files: uploadedFiles.value.map(f => ({
        id: f.id,
        name: f.name,
        size: f.size,
        type: f.type
      })),
      submittedAt: Date.now(),
      charCount: charCount.value
    }
  }
  
  /**
   * 設置提交狀態
   */
  function setSubmitStatus(status, progress = 0) {
    isSubmitting.value = status
    submitProgress.value = progress
  }
  
  /**
   * 記錄提交歷史
   */
  function recordSubmission(success, data = null) {
    const record = {
      timestamp: Date.now(),
      success,
      data: success ? data : null,
      error: success ? null : lastError.value
    }
    
    submitHistory.value.unshift(record)
    lastSubmitTime.value = Date.now()
    
    // 保持歷史記錄不超過 20 條
    if (submitHistory.value.length > 20) {
      submitHistory.value = submitHistory.value.slice(0, 20)
    }
  }

  // ===== 錯誤處理 =====
  
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
    
    console.error('❌ 反饋錯誤:', errorInfo)
  }
  
  /**
   * 清除錯誤
   */
  function clearError() {
    lastError.value = null
  }

  // ===== 重置和清理 =====
  
  /**
   * 重置回饋表單
   */
  function resetFeedback() {
    // 重置回饋數據
    Object.assign(feedbackData, {
      text: '',
      type: 'text',
      metadata: {}
    })

    // 重置字符計數
    charCount.value = 0

    // 清理文件
    uploadedFiles.value = []
    uploadProgress.value = {}

    // 重置狀態
    isSubmitting.value = false
    submitProgress.value = 0
    isDirty.value = false

    // 清理驗證和錯誤
    clearValidationErrors()
    clearError()

    console.log('🔄 回饋表單已重置')
  }
  
  /**
   * 清除快速回應歷史
   */
  function clearQuickResponseHistory() {
    quickResponseHistory.value = []
    lastQuickResponse.value = null
    console.log('🗑️ 快速回應歷史已清除')
  }

  // ===== 返回 Store API =====
  return {
    // 狀態
    feedbackData,
    quickResponseHistory,
    lastQuickResponse,
    uploadedFiles,
    uploadProgress,
    maxFileSize,
    allowedFileTypes,
    maxFiles,
    isSubmitting,
    submitProgress,
    lastSubmitTime,
    submitHistory,
    validationErrors,
    isFormValid,
    lastError,
    errorHistory,
    isDirty,
    charCount,
    maxCharCount,

    // 計算屬性
    isFeedbackEmpty,
    isCharCountExceeded,
    totalFileSize,
    totalFileSizeFormatted,
    canAddMoreFiles,
    feedbackSummary,
    validationErrorCount,
    hasUploadingFiles,

    // 方法
    updateFeedbackText,
    sendQuickResponse,
    clearQuickResponseHistory,
    markDirty,
    markClean,
    addFile,
    removeFile,
    setFileUploadProgress,
    validateFeedback,
    clearValidationErrors,
    prepareSubmitData,
    setSubmitStatus,
    recordSubmission,
    setError,
    clearError,
    resetFeedback
  }
})
