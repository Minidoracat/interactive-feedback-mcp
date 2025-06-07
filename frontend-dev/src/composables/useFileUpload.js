/**
 * 文件上傳 Composable
 * 提供文件選擇、驗證、預覽、上傳進度等功能
 */

import { ref, computed, reactive } from 'vue'
import { useFeedbackStore } from '@/stores/feedback'

export function useFileUpload() {
  // ===== Store =====
  const feedbackStore = useFeedbackStore()
  
  // ===== 狀態 =====
  const isDragging = ref(false)
  const dragCounter = ref(0)
  const isUploading = ref(false)
  const uploadProgress = reactive({})
  
  // 文件驗證配置
  const config = ref({
    maxFileSize: 10 * 1024 * 1024, // 10MB
    maxFiles: 5,
    allowedTypes: [
      'image/jpeg',
      'image/jpg', 
      'image/png',
      'image/gif',
      'image/webp',
      'image/svg+xml'
    ],
    allowedExtensions: ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
  })

  // ===== 計算屬性 =====
  
  const uploadedFiles = computed(() => feedbackStore.uploadedFiles)
  const canAddMoreFiles = computed(() => feedbackStore.canAddMoreFiles)
  const totalFileSize = computed(() => feedbackStore.totalFileSize)
  const totalFileSizeFormatted = computed(() => feedbackStore.totalFileSizeFormatted)
  
  // 是否有正在上傳的文件
  const hasUploadingFiles = computed(() => {
    return Object.values(uploadProgress).some(progress => progress < 100)
  })
  
  // 上傳進度統計
  const uploadStats = computed(() => {
    const progresses = Object.values(uploadProgress)
    if (progresses.length === 0) return { average: 0, completed: 0, total: 0 }
    
    const total = progresses.length
    const completed = progresses.filter(p => p >= 100).length
    const average = progresses.reduce((sum, p) => sum + p, 0) / total
    
    return { average, completed, total }
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
   * 獲取文件擴展名
   */
  function getFileExtension(filename) {
    return filename.toLowerCase().substring(filename.lastIndexOf('.'))
  }
  
  /**
   * 檢查文件類型
   */
  function isValidFileType(file) {
    const extension = getFileExtension(file.name)
    return config.value.allowedTypes.includes(file.type) || 
           config.value.allowedExtensions.includes(extension)
  }
  
  /**
   * 檢查文件大小
   */
  function isValidFileSize(file) {
    return file.size <= config.value.maxFileSize
  }
  
  /**
   * 生成文件預覽
   */
  function generatePreview(file) {
    return new Promise((resolve, reject) => {
      if (!file.type.startsWith('image/')) {
        resolve(null)
        return
      }
      
      const reader = new FileReader()
      reader.onload = (e) => resolve(e.target.result)
      reader.onerror = reject
      reader.readAsDataURL(file)
    })
  }
  
  /**
   * 創建文件信息對象
   */
  async function createFileInfo(file) {
    const preview = await generatePreview(file).catch(() => null)
    
    return {
      id: Date.now().toString(36) + Math.random().toString(36).substr(2),
      file: file,
      name: file.name,
      size: file.size,
      type: file.type,
      preview: preview,
      uploadedAt: Date.now(),
      progress: 0
    }
  }

  // ===== 文件驗證 =====
  
  /**
   * 驗證單個文件
   */
  function validateFile(file) {
    const errors = []
    
    // 檢查文件數量
    if (!canAddMoreFiles.value) {
      errors.push(`最多只能上傳 ${config.value.maxFiles} 個文件`)
    }
    
    // 檢查文件類型
    if (!isValidFileType(file)) {
      errors.push(`不支持的文件類型: ${file.type || '未知'}`)
    }
    
    // 檢查文件大小
    if (!isValidFileSize(file)) {
      errors.push(`文件大小超過限制 (${formatFileSize(config.value.maxFileSize)})`)
    }
    
    // 檢查文件名
    if (!file.name || file.name.trim() === '') {
      errors.push('文件名不能為空')
    }
    
    // 檢查是否已存在同名文件
    const existingFile = uploadedFiles.value.find(f => f.name === file.name)
    if (existingFile) {
      errors.push(`文件 "${file.name}" 已存在`)
    }
    
    return {
      isValid: errors.length === 0,
      errors
    }
  }
  
  /**
   * 驗證多個文件
   */
  function validateFiles(files) {
    const results = []
    const validFiles = []
    const errors = []
    
    for (const file of files) {
      const validation = validateFile(file)
      results.push({ file, validation })
      
      if (validation.isValid) {
        validFiles.push(file)
      } else {
        errors.push(...validation.errors.map(error => `${file.name}: ${error}`))
      }
    }
    
    return {
      results,
      validFiles,
      errors,
      hasErrors: errors.length > 0
    }
  }

  // ===== 文件操作 =====
  
  /**
   * 添加文件
   */
  async function addFiles(files) {
    const fileArray = Array.from(files)
    const validation = validateFiles(fileArray)
    
    if (validation.hasErrors) {
      feedbackStore.setError(`文件驗證失敗:\n${validation.errors.join('\n')}`)
      return { success: false, errors: validation.errors }
    }
    
    const addedFiles = []
    
    try {
      for (const file of validation.validFiles) {
        const fileInfo = await createFileInfo(file)
        
        if (feedbackStore.addFile(fileInfo)) {
          addedFiles.push(fileInfo)
          console.log('📁 文件已添加:', fileInfo.name)
        }
      }
      
      return { success: true, files: addedFiles }
    } catch (error) {
      console.error('❌ 添加文件失敗:', error)
      feedbackStore.setError(error)
      return { success: false, error }
    }
  }
  
  /**
   * 移除文件
   */
  function removeFile(fileId) {
    feedbackStore.removeFile(fileId)
    
    // 清理上傳進度
    if (uploadProgress[fileId]) {
      delete uploadProgress[fileId]
    }
    
    console.log('🗑️ 文件已移除:', fileId)
  }
  
  /**
   * 清空所有文件
   */
  function clearAllFiles() {
    uploadedFiles.value.forEach(file => {
      removeFile(file.id)
    })
    
    console.log('🗑️ 所有文件已清空')
  }

  // ===== 拖拽處理 =====
  
  /**
   * 處理拖拽進入
   */
  function handleDragEnter(event) {
    event.preventDefault()
    dragCounter.value++
    isDragging.value = true
  }
  
  /**
   * 處理拖拽離開
   */
  function handleDragLeave(event) {
    event.preventDefault()
    dragCounter.value--
    
    if (dragCounter.value === 0) {
      isDragging.value = false
    }
  }
  
  /**
   * 處理拖拽懸停
   */
  function handleDragOver(event) {
    event.preventDefault()
  }
  
  /**
   * 處理文件放置
   */
  async function handleDrop(event) {
    event.preventDefault()
    
    isDragging.value = false
    dragCounter.value = 0
    
    const files = event.dataTransfer.files
    if (files.length > 0) {
      await addFiles(files)
    }
  }

  // ===== 文件選擇 =====
  
  /**
   * 處理文件選擇
   */
  async function handleFileSelect(event) {
    const files = event.target.files
    if (files.length > 0) {
      await addFiles(files)
    }
    
    // 清空 input 值，允許重複選擇同一文件
    event.target.value = ''
  }
  
  /**
   * 觸發文件選擇對話框
   */
  function triggerFileSelect(inputRef) {
    if (inputRef && inputRef.click) {
      inputRef.click()
    }
  }

  // ===== 上傳模擬 =====
  
  /**
   * 模擬文件上傳進度
   */
  function simulateUploadProgress(fileId, duration = 2000) {
    return new Promise((resolve) => {
      uploadProgress[fileId] = 0
      const startTime = Date.now()
      
      const updateProgress = () => {
        const elapsed = Date.now() - startTime
        const progress = Math.min(100, (elapsed / duration) * 100)
        
        uploadProgress[fileId] = Math.round(progress)
        feedbackStore.setFileUploadProgress(fileId, progress)
        
        if (progress < 100) {
          requestAnimationFrame(updateProgress)
        } else {
          resolve()
        }
      }
      
      updateProgress()
    })
  }
  
  /**
   * 上傳所有文件
   */
  async function uploadAllFiles() {
    if (uploadedFiles.value.length === 0) {
      return { success: true, files: [] }
    }
    
    isUploading.value = true
    
    try {
      const uploadPromises = uploadedFiles.value.map(file => 
        simulateUploadProgress(file.id)
      )
      
      await Promise.all(uploadPromises)
      
      console.log('✅ 所有文件上傳完成')
      return { success: true, files: uploadedFiles.value }
    } catch (error) {
      console.error('❌ 文件上傳失敗:', error)
      feedbackStore.setError(error)
      return { success: false, error }
    } finally {
      isUploading.value = false
    }
  }

  // ===== 返回 API =====
  return {
    // 狀態
    isDragging,
    isUploading,
    uploadProgress,
    config,
    
    // 計算屬性
    uploadedFiles,
    canAddMoreFiles,
    totalFileSize,
    totalFileSizeFormatted,
    hasUploadingFiles,
    uploadStats,
    
    // 文件操作
    addFiles,
    removeFile,
    clearAllFiles,
    
    // 拖拽處理
    handleDragEnter,
    handleDragLeave,
    handleDragOver,
    handleDrop,
    
    // 文件選擇
    handleFileSelect,
    triggerFileSelect,
    
    // 上傳
    uploadAllFiles,
    simulateUploadProgress,
    
    // 工具方法
    formatFileSize,
    validateFile,
    validateFiles,
    isValidFileType,
    isValidFileSize
  }
}
