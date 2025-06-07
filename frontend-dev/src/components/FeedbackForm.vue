<!--
  反饋表單組件
  提供文本輸入、分類選擇、優先級設置、標籤管理等功能
-->

<template>
  <div class="feedback-form">
    <form @submit.prevent="handleSubmit" class="form-container">
      <!-- 表單標題 -->
      <div class="form-header">
        <h2 class="form-title">提交反饋</h2>
        <p class="form-description">
          請詳細描述您的問題或建議，我們會認真處理每一條反饋。
        </p>
      </div>
      
      <!-- 基本信息區域 -->
      <div class="form-section" :class="{ expanded: expandedSections.basic }">
        <div class="section-header" @click="toggleSection('basic')">
          <h3 class="section-title">基本信息</h3>
          <span class="section-toggle">
            {{ expandedSections.basic ? '▼' : '▶' }}
          </span>
        </div>
        
        <div v-show="expandedSections.basic" class="section-content">
          <!-- 反饋內容 -->
          <div class="form-group">
            <label for="feedback-text" class="form-label required">
              反饋內容
            </label>
            <textarea
              id="feedback-text"
              v-model="formData.text"
              class="form-textarea"
              :class="{ error: validationErrors.text }"
              placeholder="請詳細描述您遇到的問題或建議..."
              rows="6"
              maxlength="5000"
              @input="handleTextInput"
              @blur="validateField('text')"
            ></textarea>
            
            <div class="field-footer">
              <div v-if="validationErrors.text" class="error-message">
                {{ validationErrors.text }}
              </div>
              <div class="char-counter">
                {{ formData.text.length }}/5000
              </div>
            </div>
          </div>
          
          <!-- 分類和優先級 -->
          <div class="form-row">
            <div class="form-group">
              <label for="feedback-category" class="form-label required">
                反饋類別
              </label>
              <select
                id="feedback-category"
                v-model="formData.category"
                class="form-select"
                :class="{ error: validationErrors.category }"
                @change="validateField('category')"
              >
                <option value="">請選擇類別</option>
                <option value="bug">錯誤報告</option>
                <option value="feature">功能建議</option>
                <option value="improvement">改進建議</option>
                <option value="general">一般反饋</option>
              </select>
              
              <div v-if="validationErrors.category" class="error-message">
                {{ validationErrors.category }}
              </div>
            </div>
            
            <div class="form-group">
              <label for="feedback-priority" class="form-label required">
                優先級
              </label>
              <select
                id="feedback-priority"
                v-model="formData.priority"
                class="form-select"
                :class="{ error: validationErrors.priority }"
                @change="validateField('priority')"
              >
                <option value="">請選擇優先級</option>
                <option value="low">低</option>
                <option value="medium">中</option>
                <option value="high">高</option>
                <option value="urgent">緊急</option>
              </select>
              
              <div v-if="validationErrors.priority" class="error-message">
                {{ validationErrors.priority }}
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 標籤管理區域 -->
      <div class="form-section" :class="{ expanded: expandedSections.tags }">
        <div class="section-header" @click="toggleSection('tags')">
          <h3 class="section-title">標籤 (可選)</h3>
          <span class="section-toggle">
            {{ expandedSections.tags ? '▼' : '▶' }}
          </span>
        </div>
        
        <div v-show="expandedSections.tags" class="section-content">
          <!-- 標籤輸入 -->
          <div class="form-group">
            <label for="tag-input" class="form-label">
              添加標籤
            </label>
            <div class="tag-input-container">
              <input
                id="tag-input"
                v-model="newTag"
                type="text"
                class="form-input"
                placeholder="輸入標籤後按 Enter 添加"
                @keydown.enter.prevent="addTag"
                @keydown.comma.prevent="addTag"
              />
              <button
                type="button"
                @click="addTag"
                class="add-tag-btn"
                :disabled="!newTag.trim()"
              >
                添加
              </button>
            </div>
            
            <div class="tag-suggestions">
              <span class="suggestions-label">建議標籤:</span>
              <button
                v-for="suggestion in tagSuggestions"
                :key="suggestion"
                type="button"
                @click="addSuggestedTag(suggestion)"
                class="suggestion-tag"
                :disabled="formData.tags.includes(suggestion)"
              >
                {{ suggestion }}
              </button>
            </div>
          </div>
          
          <!-- 已添加的標籤 -->
          <div v-if="formData.tags.length > 0" class="form-group">
            <label class="form-label">已添加的標籤</label>
            <div class="tag-list">
              <span
                v-for="tag in formData.tags"
                :key="tag"
                class="tag-item"
              >
                {{ tag }}
                <button
                  type="button"
                  @click="removeTag(tag)"
                  class="tag-remove"
                >
                  ×
                </button>
              </span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 表單摘要 -->
      <div v-if="showPreview" class="form-preview">
        <h3 class="preview-title">反饋摘要</h3>
        <div class="preview-content">
          <div class="preview-item">
            <span class="preview-label">內容長度:</span>
            <span class="preview-value">{{ formSummary.textLength }} 字符</span>
          </div>
          <div class="preview-item">
            <span class="preview-label">類別:</span>
            <span class="preview-value">{{ getCategoryText(formSummary.category) }}</span>
          </div>
          <div class="preview-item">
            <span class="preview-label">優先級:</span>
            <span class="preview-value">{{ getPriorityText(formSummary.priority) }}</span>
          </div>
          <div class="preview-item">
            <span class="preview-label">標籤:</span>
            <span class="preview-value">
              {{ formSummary.tags.length > 0 ? formSummary.tags.join(', ') : '無' }}
            </span>
          </div>
        </div>
      </div>
      
      <!-- 表單操作 -->
      <div class="form-actions">
        <div class="action-group">
          <!-- 預覽切換 -->
          <button
            type="button"
            @click="togglePreview"
            class="action-btn preview-btn"
          >
            <span class="btn-icon">👁️</span>
            {{ showPreview ? '隱藏預覽' : '顯示預覽' }}
          </button>
          
          <!-- 重置按鈕 -->
          <button
            type="button"
            @click="handleReset"
            class="action-btn reset-btn"
            :disabled="isSubmitting || isFormEmpty"
          >
            <span class="btn-icon">🔄</span>
            重置
          </button>
        </div>
        
        <div class="action-group">
          <!-- 提交按鈕 -->
          <button
            type="submit"
            class="action-btn submit-btn"
            :disabled="!isFormValid || isSubmitting"
          >
            <span v-if="isSubmitting" class="btn-icon loading">⏳</span>
            <span v-else class="btn-icon">📤</span>
            {{ isSubmitting ? '提交中...' : '提交反饋' }}
          </button>
        </div>
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
          提交進度: {{ submitProgress }}%
        </div>
      </div>
      
      <!-- 錯誤信息 -->
      <div v-if="lastError" class="form-error">
        <div class="error-content">
          <span class="error-icon">❌</span>
          <div class="error-text">
            <div class="error-title">提交失敗</div>
            <div class="error-message">{{ lastError.message }}</div>
          </div>
          <button @click="clearError" class="error-dismiss">×</button>
        </div>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useFeedbackStore } from '@/stores/feedback'

// ===== Props =====
const props = defineProps({
  // 自動保存
  autoSave: {
    type: Boolean,
    default: true
  },
  
  // 顯示預覽
  showPreviewByDefault: {
    type: Boolean,
    default: false
  }
})

// ===== Emits =====
const emit = defineEmits([
  'submit',
  'reset',
  'validation-change',
  'field-change'
])

// ===== Store =====
const feedbackStore = useFeedbackStore()

// ===== 狀態 =====
const newTag = ref('')
const tagSuggestions = ref([
  'UI/UX', '性能', '安全', '兼容性', '文檔', 
  '功能請求', '錯誤修復', '用戶體驗', '移動端', '桌面端'
])

// ===== 計算屬性 =====
const formData = computed(() => feedbackStore.formData)
const validationErrors = computed(() => feedbackStore.validationErrors)
const isFormValid = computed(() => feedbackStore.isFormValid)
const isFormEmpty = computed(() => feedbackStore.isFormEmpty)
const isSubmitting = computed(() => feedbackStore.isSubmitting)
const submitProgress = computed(() => feedbackStore.submitProgress)
const lastError = computed(() => feedbackStore.lastError)
const showPreview = computed(() => feedbackStore.showPreview)
const expandedSections = computed(() => feedbackStore.expandedSections)
const formSummary = computed(() => feedbackStore.formSummary)

// ===== 方法 =====

/**
 * 處理文本輸入
 */
function handleTextInput() {
  feedbackStore.markDirty()
  emit('field-change', 'text', formData.value.text)
}

/**
 * 驗證字段
 */
function validateField(field) {
  feedbackStore.validateField(field)
  emit('validation-change', {
    field,
    isValid: !validationErrors.value[field],
    error: validationErrors.value[field]
  })
}

/**
 * 添加標籤
 */
function addTag() {
  const tag = newTag.value.trim()
  if (tag) {
    feedbackStore.addTag(tag)
    newTag.value = ''
    emit('field-change', 'tags', formData.value.tags)
  }
}

/**
 * 添加建議標籤
 */
function addSuggestedTag(tag) {
  feedbackStore.addTag(tag)
  emit('field-change', 'tags', formData.value.tags)
}

/**
 * 移除標籤
 */
function removeTag(tag) {
  feedbackStore.removeTag(tag)
  emit('field-change', 'tags', formData.value.tags)
}

/**
 * 切換區域展開狀態
 */
function toggleSection(section) {
  feedbackStore.toggleSection(section)
}

/**
 * 切換預覽
 */
function togglePreview() {
  feedbackStore.togglePreview()
}

/**
 * 處理表單提交
 */
async function handleSubmit() {
  // 驗證表單
  if (!feedbackStore.validateForm()) {
    return
  }
  
  try {
    feedbackStore.setSubmitStatus(true, 0)
    
    // 準備提交數據
    const submitData = feedbackStore.prepareSubmitData()
    
    // 模擬提交進度
    for (let i = 0; i <= 100; i += 10) {
      feedbackStore.setSubmitStatus(true, i)
      await new Promise(resolve => setTimeout(resolve, 100))
    }
    
    // 記錄提交成功
    feedbackStore.recordSubmission(true, submitData)
    feedbackStore.setSubmitStatus(false, 100)
    
    emit('submit', submitData)
    console.log('✅ 反饋提交成功:', submitData)
    
    // 可選：提交後重置表單
    // feedbackStore.resetForm()
    
  } catch (error) {
    console.error('❌ 反饋提交失敗:', error)
    feedbackStore.setError(error)
    feedbackStore.recordSubmission(false)
    feedbackStore.setSubmitStatus(false, 0)
  }
}

/**
 * 處理表單重置
 */
function handleReset() {
  if (feedbackStore.isDirty && !confirm('確定要重置表單嗎？所有未保存的內容將丟失。')) {
    return
  }
  
  feedbackStore.resetForm()
  emit('reset')
  console.log('🔄 表單已重置')
}

/**
 * 清除錯誤
 */
function clearError() {
  feedbackStore.clearError()
}

/**
 * 獲取類別文本
 */
function getCategoryText(category) {
  const categoryMap = {
    'bug': '錯誤報告',
    'feature': '功能建議', 
    'improvement': '改進建議',
    'general': '一般反饋'
  }
  return categoryMap[category] || category
}

/**
 * 獲取優先級文本
 */
function getPriorityText(priority) {
  const priorityMap = {
    'low': '低',
    'medium': '中',
    'high': '高', 
    'urgent': '緊急'
  }
  return priorityMap[priority] || priority
}

// ===== 監聽器 =====

// 監聽表單數據變化，自動保存
watch(
  () => formData.value,
  () => {
    if (props.autoSave) {
      // 這裡可以實現自動保存邏輯
      console.log('🔄 自動保存表單數據')
    }
  },
  { deep: true }
)

// 初始化預覽狀態
if (props.showPreviewByDefault) {
  feedbackStore.showPreview = true
}
</script>

<style lang="scss" scoped>
.feedback-form {
  max-width: 800px;
  margin: 0 auto;
}

.form-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.form-header {
  padding: 2rem 2rem 1rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  text-align: center;
}

.form-title {
  font-size: 1.875rem;
  font-weight: 700;
  margin: 0 0 0.5rem 0;
}

.form-description {
  font-size: 1rem;
  margin: 0;
  opacity: 0.9;
  line-height: 1.5;
}

.form-section {
  border-bottom: 1px solid #e5e7eb;
  
  &:last-child {
    border-bottom: none;
  }
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background: #f9fafb;
  cursor: pointer;
  transition: background-color 0.2s ease;
  
  &:hover {
    background: #f3f4f6;
  }
}

.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #374151;
  margin: 0;
}

.section-toggle {
  color: #6b7280;
  font-size: 0.875rem;
  transition: transform 0.2s ease;
}

.section-content {
  padding: 1.5rem 2rem;
}

.form-group {
  margin-bottom: 1.5rem;
  
  &:last-child {
    margin-bottom: 0;
  }
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-label {
  display: block;
  font-weight: 500;
  color: #374151;
  margin-bottom: 0.5rem;
  
  &.required::after {
    content: ' *';
    color: #ef4444;
  }
}

.form-textarea,
.form-input,
.form-select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 1rem;
  transition: all 0.2s ease;
  
  &:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }
  
  &.error {
    border-color: #ef4444;
    box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
  }
}

.form-textarea {
  resize: vertical;
  min-height: 120px;
  font-family: inherit;
}

.field-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.5rem;
}

.error-message {
  color: #ef4444;
  font-size: 0.875rem;
}

.char-counter {
  font-size: 0.75rem;
  color: #9ca3af;
}

.tag-input-container {
  display: flex;
  gap: 0.5rem;
}

.add-tag-btn {
  padding: 0.75rem 1rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: background-color 0.2s ease;
  white-space: nowrap;
  
  &:hover:not(:disabled) {
    background: #2563eb;
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.tag-suggestions {
  margin-top: 0.75rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.suggestions-label {
  font-size: 0.875rem;
  color: #6b7280;
  font-weight: 500;
}

.suggestion-tag {
  padding: 0.25rem 0.5rem;
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover:not(:disabled) {
    background: #e5e7eb;
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.tag-item {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.375rem 0.75rem;
  background: #3b82f6;
  color: white;
  border-radius: 20px;
  font-size: 0.875rem;
}

.tag-remove {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  font-size: 1rem;
  padding: 0;
  width: 1rem;
  height: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background-color 0.2s ease;
  
  &:hover {
    background: rgba(255, 255, 255, 0.2);
  }
}

.form-preview {
  margin: 1.5rem 2rem;
  padding: 1rem;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 8px;
}

.preview-title {
  font-size: 1rem;
  font-weight: 600;
  color: #0c4a6e;
  margin: 0 0 0.75rem 0;
}

.preview-content {
  display: grid;
  gap: 0.5rem;
}

.preview-item {
  display: flex;
  justify-content: space-between;
  font-size: 0.875rem;
}

.preview-label {
  color: #374151;
  font-weight: 500;
}

.preview-value {
  color: #6b7280;
}

.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 2rem;
  background: #f9fafb;
  border-top: 1px solid #e5e7eb;
}

.action-group {
  display: flex;
  gap: 0.75rem;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
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
    
    &.loading {
      animation: spin 1s linear infinite;
    }
  }
  
  &.submit-btn {
    background: #3b82f6;
    color: white;
    border-color: #3b82f6;
    
    &:hover:not(:disabled) {
      background: #2563eb;
      border-color: #2563eb;
    }
  }
  
  &.reset-btn {
    border-color: #ef4444;
    color: #dc2626;
    
    &:hover:not(:disabled) {
      background: rgba(239, 68, 68, 0.05);
    }
  }
  
  &.preview-btn {
    border-color: #10b981;
    color: #059669;
    
    &:hover:not(:disabled) {
      background: rgba(16, 185, 129, 0.05);
    }
  }
}

.submit-progress {
  margin: 0 2rem 1.5rem;
}

.progress-bar {
  height: 6px;
  background: #e5e7eb;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.progress-fill {
  height: 100%;
  background: #3b82f6;
  transition: width 0.3s ease;
}

.progress-text {
  text-align: center;
  font-size: 0.875rem;
  color: #6b7280;
}

.form-error {
  margin: 0 2rem 1.5rem;
  padding: 1rem;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
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
  color: #991b1b;
}

.error-title {
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.error-dismiss {
  background: none;
  border: none;
  color: #991b1b;
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

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 768px) {
  .form-container {
    margin: 0;
    border-radius: 0;
  }
  
  .form-header,
  .section-content,
  .form-actions {
    padding-left: 1rem;
    padding-right: 1rem;
  }
  
  .form-row {
    grid-template-columns: 1fr;
  }
  
  .form-actions {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }
  
  .action-group {
    justify-content: center;
  }
  
  .action-btn {
    flex: 1;
    justify-content: center;
  }
}
</style>
