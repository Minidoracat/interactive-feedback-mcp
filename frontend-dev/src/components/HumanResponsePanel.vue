<!--
  人類回饋面板組件
  簡潔的文字回饋 + 圖片上傳界面，支援快速回應
-->

<template>
  <div class="human-response-panel">
    <!-- 快速回應按鈕 -->
    <div class="quick-response-section">
      <h3 class="section-title">
        <span class="title-icon">⚡</span>
        Quick Response
      </h3>
      <div class="quick-buttons">
        <button 
          @click="sendQuickResponse('confirm')"
          class="quick-btn confirm-btn"
          :disabled="isSubmitting"
        >
          <span class="btn-icon">✅</span>
          Confirm
        </button>
        <button 
          @click="sendQuickResponse('reject')"
          class="quick-btn reject-btn"
          :disabled="isSubmitting"
        >
          <span class="btn-icon">❌</span>
          Reject
        </button>
        <button 
          @click="sendQuickResponse('need-info')"
          class="quick-btn info-btn"
          :disabled="isSubmitting"
        >
          <span class="btn-icon">❓</span>
          Need Info
        </button>
        <button 
          @click="sendQuickResponse('later')"
          class="quick-btn later-btn"
          :disabled="isSubmitting"
        >
          <span class="btn-icon">⏰</span>
          Later
        </button>
      </div>
    </div>

    <!-- 文字回饋區域 -->
    <div class="text-feedback-section">
      <h3 class="section-title">
        <span class="title-icon">💬</span>
        Text Response
      </h3>
      <div class="feedback-input-container">
        <textarea
          v-model="feedbackText"
          class="feedback-textarea"
          placeholder="Type your feedback here... (Ctrl+Enter to submit)"
          rows="6"
          maxlength="2000"
          @keydown.ctrl.enter="submitFeedback"
          @input="updateCharCount"
        ></textarea>
        <div class="input-footer">
          <div class="char-counter">
            {{ charCount }}/2000
          </div>
          <div class="keyboard-hint">
            <kbd>Ctrl</kbd> + <kbd>Enter</kbd> to submit
          </div>
        </div>
      </div>
    </div>

    <!-- 圖片上傳區域 -->
    <div class="image-upload-section">
      <h3 class="section-title">
        <span class="title-icon">📷</span>
        Image Upload
      </h3>
      <div class="upload-container">
        <ImageUpload
          :disabled="isSubmitting"
          :compact="true"
          @files-added="handleFilesAdded"
          @file-removed="handleFileRemoved"
          @files-cleared="handleFilesCleared"
          @upload-complete="handleUploadComplete"
          @upload-error="handleUploadError"
          class="image-upload-component"
        />
      </div>
    </div>

    <!-- 提交區域 -->
    <div class="submit-section">
      <div class="submit-actions">
        <button
          @click="clearAll"
          class="action-btn clear-btn"
          :disabled="isSubmitting || isEmpty"
        >
          <span class="btn-icon">🗑️</span>
          Clear
        </button>
        <button
          @click="submitFeedback"
          class="action-btn submit-btn"
          :disabled="isSubmitting || isEmpty"
        >
          <span v-if="isSubmitting" class="btn-icon loading">⏳</span>
          <span v-else class="btn-icon">📤</span>
          {{ isSubmitting ? 'Submitting...' : 'Submit Feedback' }}
        </button>
      </div>
      
      <!-- 提交進度 -->
      <div v-if="isSubmitting" class="submit-progress">
        <div class="progress-bar">
          <div 
            class="progress-fill"
            :style="{ width: submitProgress + '%' }"
          ></div>
        </div>
        <div class="progress-text">
          Submitting: {{ submitProgress }}%
        </div>
      </div>
    </div>

    <!-- 回饋歷史 -->
    <div class="feedback-history-section">
      <h3 class="section-title">
        <span class="title-icon">📋</span>
        Recent Feedback
      </h3>
      <div class="history-list">
        <div 
          v-for="item in feedbackHistory" 
          :key="item.id"
          class="history-item"
        >
          <div class="history-type" :class="item.type">
            {{ getTypeLabel(item.type) }}
          </div>
          <div class="history-content">
            <div v-if="item.text" class="history-text">{{ item.text }}</div>
            <div v-if="item.images && item.images.length" class="history-images">
              {{ item.images.length }} image(s)
            </div>
          </div>
          <div class="history-time">{{ formatTime(item.timestamp) }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useSessionStore } from '@/stores/session'
import { useFeedbackStore } from '@/stores/feedback'
import ImageUpload from '@/components/ImageUpload.vue'

// ===== Props =====
const props = defineProps({
  // 自動保存
  autoSave: {
    type: Boolean,
    default: true
  }
})

// ===== Emits =====
const emit = defineEmits([
  'submit',
  'quick-response',
  'files-added',
  'file-removed',
  'files-cleared',
  'upload-complete',
  'upload-error'
])

// ===== Store =====
const sessionStore = useSessionStore()
const feedbackStore = useFeedbackStore()

// ===== 狀態 =====
const feedbackText = ref('')
const charCount = ref(0)
const isSubmitting = ref(false)
const submitProgress = ref(0)
const uploadedFiles = ref([])

// 模擬回饋歷史
const feedbackHistory = ref([
  {
    id: 1,
    type: 'text',
    text: 'The new layout looks great! The AI-Human collaboration design is much clearer.',
    images: [],
    timestamp: Date.now() - 600000 // 10 minutes ago
  },
  {
    id: 2,
    type: 'quick',
    text: 'Confirmed',
    images: [],
    timestamp: Date.now() - 300000 // 5 minutes ago
  },
  {
    id: 3,
    type: 'mixed',
    text: 'Please check the responsive design on mobile devices.',
    images: ['screenshot1.png'],
    timestamp: Date.now() - 120000 // 2 minutes ago
  }
])

// ===== 計算屬性 =====
const isEmpty = computed(() => {
  return !feedbackText.value.trim() && uploadedFiles.value.length === 0
})

// ===== 方法 =====

/**
 * 更新字符計數
 */
function updateCharCount() {
  charCount.value = feedbackText.value.length
}

/**
 * 發送快速回應
 */
async function sendQuickResponse(type) {
  const responseMap = {
    'confirm': '✅ Confirmed',
    'reject': '❌ Rejected', 
    'need-info': '❓ Need more information',
    'later': '⏰ Will review later'
  }
  
  const response = {
    type: 'quick',
    text: responseMap[type],
    timestamp: Date.now()
  }
  
  try {
    isSubmitting.value = true
    
    // 模擬提交過程
    for (let i = 0; i <= 100; i += 20) {
      submitProgress.value = i
      await new Promise(resolve => setTimeout(resolve, 100))
    }
    
    // 添加到歷史記錄
    feedbackHistory.value.unshift({
      id: Date.now(),
      ...response
    })
    
    emit('quick-response', response)
    console.log('⚡ 快速回應已發送:', response)
    
  } catch (error) {
    console.error('❌ 快速回應發送失敗:', error)
  } finally {
    isSubmitting.value = false
    submitProgress.value = 0
  }
}

/**
 * 提交完整回饋
 */
async function submitFeedback() {
  if (isEmpty.value) return
  
  const feedback = {
    type: uploadedFiles.value.length > 0 ? 'mixed' : 'text',
    text: feedbackText.value.trim(),
    images: uploadedFiles.value.map(file => file.name),
    timestamp: Date.now()
  }
  
  try {
    isSubmitting.value = true
    
    // 模擬提交過程
    for (let i = 0; i <= 100; i += 10) {
      submitProgress.value = i
      await new Promise(resolve => setTimeout(resolve, 150))
    }
    
    // 添加到歷史記錄
    feedbackHistory.value.unshift({
      id: Date.now(),
      ...feedback
    })
    
    emit('submit', feedback)
    console.log('📤 回饋已提交:', feedback)
    
    // 清空表單
    clearAll()
    
  } catch (error) {
    console.error('❌ 回饋提交失敗:', error)
  } finally {
    isSubmitting.value = false
    submitProgress.value = 0
  }
}

/**
 * 清空所有內容
 */
function clearAll() {
  feedbackText.value = ''
  charCount.value = 0
  uploadedFiles.value = []
  emit('files-cleared')
}

/**
 * 處理文件添加
 */
function handleFilesAdded(files) {
  uploadedFiles.value.push(...files)
  emit('files-added', files)
  console.log('📁 文件已添加:', files)
}

/**
 * 處理文件移除
 */
function handleFileRemoved(fileId) {
  uploadedFiles.value = uploadedFiles.value.filter(file => file.id !== fileId)
  emit('file-removed', fileId)
  console.log('🗑️ 文件已移除:', fileId)
}

/**
 * 處理文件清空
 */
function handleFilesCleared() {
  uploadedFiles.value = []
  emit('files-cleared')
  console.log('🗑️ 文件已清空')
}

/**
 * 處理上傳完成
 */
function handleUploadComplete(files) {
  emit('upload-complete', files)
  console.log('✅ 上傳完成:', files)
}

/**
 * 處理上傳錯誤
 */
function handleUploadError(error) {
  emit('upload-error', error)
  console.error('❌ 上傳錯誤:', error)
}

/**
 * 獲取類型標籤
 */
function getTypeLabel(type) {
  const typeMap = {
    'text': 'Text',
    'quick': 'Quick',
    'mixed': 'Text + Images'
  }
  return typeMap[type] || type
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

// ===== 生命週期 =====
onMounted(() => {
  console.log('👤 Human Response Panel component mounted')
  updateCharCount()
})
</script>

<style lang="scss" scoped>
.human-response-panel {
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

// 快速回應區域
.quick-response-section {
  .quick-buttons {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 0.75rem;
  }
  
  .quick-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    border: 2px solid transparent;
    border-radius: 8px;
    background: #f8fafc;
    color: #475569;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    
    &:hover:not(:disabled) {
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    
    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    
    .btn-icon {
      font-size: 1rem;
    }
    
    &.confirm-btn {
      border-color: #10b981;
      background: #ecfdf5;
      color: #059669;
      
      &:hover:not(:disabled) {
        background: #d1fae5;
      }
    }
    
    &.reject-btn {
      border-color: #ef4444;
      background: #fef2f2;
      color: #dc2626;
      
      &:hover:not(:disabled) {
        background: #fee2e2;
      }
    }
    
    &.info-btn {
      border-color: #3b82f6;
      background: #eff6ff;
      color: #2563eb;
      
      &:hover:not(:disabled) {
        background: #dbeafe;
      }
    }
    
    &.later-btn {
      border-color: #f59e0b;
      background: #fffbeb;
      color: #d97706;
      
      &:hover:not(:disabled) {
        background: #fef3c7;
      }
    }
  }
}

// 文字回饋區域
.text-feedback-section {
  .feedback-input-container {
    position: relative;
  }
  
  .feedback-textarea {
    width: 100%;
    padding: 1rem;
    border: 2px solid #e2e8f0;
    border-radius: 12px;
    font-size: 0.875rem;
    line-height: 1.6;
    resize: vertical;
    min-height: 120px;
    transition: border-color 0.2s ease;
    
    &:focus {
      outline: none;
      border-color: #4fc08d;
      box-shadow: 0 0 0 3px rgba(79, 192, 141, 0.1);
    }
    
    &::placeholder {
      color: #9ca3af;
    }
  }
  
  .input-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 0.5rem;
    
    .char-counter {
      font-size: 0.75rem;
      color: #9ca3af;
    }
    
    .keyboard-hint {
      font-size: 0.75rem;
      color: #6b7280;
      
      kbd {
        background: #f3f4f6;
        border: 1px solid #d1d5db;
        border-radius: 4px;
        padding: 0.125rem 0.25rem;
        font-size: 0.625rem;
        font-family: monospace;
      }
    }
  }
}

// 圖片上傳區域
.image-upload-section {
  .upload-container {
    background: #f8fafc;
    border-radius: 12px;
    padding: 1rem;
    border: 2px dashed #cbd5e1;
    transition: border-color 0.2s ease;
    
    &:hover {
      border-color: #4fc08d;
    }
  }
}

// 提交區域
.submit-section {
  .submit-actions {
    display: flex;
    gap: 0.75rem;
    justify-content: flex-end;
  }
  
  .action-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1.5rem;
    border: 2px solid transparent;
    border-radius: 8px;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    
    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    
    .btn-icon {
      font-size: 1rem;
      
      &.loading {
        animation: spin 1s linear infinite;
      }
    }
    
    &.clear-btn {
      background: #f8fafc;
      color: #64748b;
      border-color: #cbd5e1;
      
      &:hover:not(:disabled) {
        background: #f1f5f9;
        border-color: #94a3b8;
      }
    }
    
    &.submit-btn {
      background: #4fc08d;
      color: white;
      border-color: #4fc08d;
      
      &:hover:not(:disabled) {
        background: #42b883;
        border-color: #42b883;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(79, 192, 141, 0.3);
      }
    }
  }
  
  .submit-progress {
    margin-top: 1rem;
    
    .progress-bar {
      height: 4px;
      background: #e2e8f0;
      border-radius: 2px;
      overflow: hidden;
      margin-bottom: 0.5rem;
      
      .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #4fc08d 0%, #42b883 100%);
        transition: width 0.3s ease;
      }
    }
    
    .progress-text {
      text-align: center;
      font-size: 0.75rem;
      color: #64748b;
    }
  }
}

// 回饋歷史區域
.feedback-history-section {
  flex: 1;
  min-height: 0;
  
  .history-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    max-height: 200px;
    overflow-y: auto;
    padding-right: 0.5rem;
  }
  
  .history-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    background: #f8fafc;
    border-radius: 8px;
    border: 1px solid #e2e8f0;
    
    .history-type {
      padding: 0.25rem 0.5rem;
      border-radius: 12px;
      font-size: 0.625rem;
      font-weight: 500;
      white-space: nowrap;
      
      &.text {
        background: #dbeafe;
        color: #1e40af;
      }
      
      &.quick {
        background: #dcfce7;
        color: #166534;
      }
      
      &.mixed {
        background: #fef3c7;
        color: #92400e;
      }
    }
    
    .history-content {
      flex: 1;
      min-width: 0;
      
      .history-text {
        font-size: 0.75rem;
        color: #374151;
        line-height: 1.4;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      
      .history-images {
        font-size: 0.625rem;
        color: #9ca3af;
        margin-top: 0.125rem;
      }
    }
    
    .history-time {
      font-size: 0.625rem;
      color: #9ca3af;
      white-space: nowrap;
    }
  }
}

// 動畫
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

// 響應式設計
@media (max-width: 768px) {
  .human-response-panel {
    gap: 1rem;
  }
  
  .quick-buttons {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .submit-actions {
    flex-direction: column;
    
    .action-btn {
      justify-content: center;
    }
  }
}
</style>
