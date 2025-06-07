<!--
  圖片上傳組件
  支持拖拽上傳、多文件選擇、預覽、進度顯示等功能
-->

<template>
  <div class="image-upload">
    <!-- 上傳區域 -->
    <div 
      class="upload-area"
      :class="uploadAreaClass"
      @dragenter="handleDragEnter"
      @dragleave="handleDragLeave"
      @dragover="handleDragOver"
      @drop="handleDrop"
      @click="triggerFileSelect(fileInputRef)"
    >
      <!-- 隱藏的文件輸入 -->
      <input
        ref="fileInputRef"
        type="file"
        multiple
        accept="image/*"
        @change="handleFileSelect"
        class="file-input"
      />
      
      <!-- 上傳提示 -->
      <div class="upload-prompt">
        <div class="upload-icon">
          <span v-if="!isDragging">📁</span>
          <span v-else>📂</span>
        </div>
        
        <div class="upload-text">
          <div class="primary-text">
            {{ isDragging ? '放開以上傳文件' : '點擊或拖拽圖片到此處' }}
          </div>
          <div class="secondary-text">
            支持 JPG、PNG、GIF、WebP 格式，單個文件最大 {{ formatFileSize(config.maxFileSize) }}
          </div>
        </div>
        
        <button 
          type="button"
          class="browse-btn"
          @click.stop="triggerFileSelect(fileInputRef)"
        >
          選擇文件
        </button>
      </div>
      
      <!-- 上傳限制提示 -->
      <div class="upload-limits">
        <span class="limit-item">
          最多 {{ config.maxFiles }} 個文件
        </span>
        <span class="limit-item">
          總大小 {{ totalFileSizeFormatted }}
        </span>
      </div>
    </div>
    
    <!-- 文件列表 -->
    <div v-if="uploadedFiles.length > 0" class="file-list">
      <div class="list-header">
        <h3 class="list-title">
          已選擇的圖片 ({{ uploadedFiles.length }}/{{ config.maxFiles }})
        </h3>
        
        <div class="list-actions">
          <!-- 全部上傳按鈕 -->
          <button 
            v-if="!hasUploadingFiles"
            @click="uploadAllFiles"
            class="action-btn upload-all-btn"
            :disabled="isUploading || uploadedFiles.length === 0"
          >
            <span class="btn-icon">⬆️</span>
            上傳全部
          </button>
          
          <!-- 清空按鈕 -->
          <button 
            @click="clearAllFiles"
            class="action-btn clear-btn"
            :disabled="isUploading"
          >
            <span class="btn-icon">🗑️</span>
            清空
          </button>
        </div>
      </div>
      
      <!-- 上傳進度總覽 -->
      <div v-if="hasUploadingFiles" class="upload-progress-summary">
        <div class="progress-info">
          <span class="progress-text">
            上傳進度: {{ uploadStats.completed }}/{{ uploadStats.total }}
          </span>
          <span class="progress-percentage">
            {{ Math.round(uploadStats.average) }}%
          </span>
        </div>
        <div class="progress-bar">
          <div 
            class="progress-fill"
            :style="{ width: uploadStats.average + '%' }"
          ></div>
        </div>
      </div>
      
      <!-- 文件項目列表 -->
      <div class="file-items">
        <div 
          v-for="file in uploadedFiles"
          :key="file.id"
          class="file-item"
          :class="{ 'uploading': uploadProgress[file.id] < 100 }"
        >
          <!-- 圖片預覽 -->
          <div class="file-preview">
            <img 
              v-if="file.preview"
              :src="file.preview"
              :alt="file.name"
              class="preview-image"
            />
            <div v-else class="preview-placeholder">
              <span class="placeholder-icon">🖼️</span>
            </div>
            
            <!-- 上傳進度覆蓋層 -->
            <div 
              v-if="uploadProgress[file.id] < 100"
              class="upload-overlay"
            >
              <div class="upload-progress">
                <div class="progress-circle">
                  <span class="progress-text">{{ uploadProgress[file.id] || 0 }}%</span>
                </div>
              </div>
            </div>
          </div>
          
          <!-- 文件信息 -->
          <div class="file-info">
            <div class="file-name" :title="file.name">
              {{ file.name }}
            </div>
            <div class="file-meta">
              <span class="file-size">{{ formatFileSize(file.size) }}</span>
              <span class="file-type">{{ file.type }}</span>
            </div>
          </div>
          
          <!-- 操作按鈕 -->
          <div class="file-actions">
            <!-- 預覽按鈕 -->
            <button 
              v-if="file.preview"
              @click="previewImage(file)"
              class="file-action-btn preview-btn"
              title="預覽"
            >
              👁️
            </button>
            
            <!-- 刪除按鈕 -->
            <button 
              @click="removeFile(file.id)"
              class="file-action-btn remove-btn"
              title="刪除"
              :disabled="uploadProgress[file.id] > 0 && uploadProgress[file.id] < 100"
            >
              🗑️
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 圖片預覽模態框 -->
    <div 
      v-if="previewModal.show"
      class="preview-modal"
      @click="closePreview"
    >
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3 class="modal-title">{{ previewModal.file?.name }}</h3>
          <button @click="closePreview" class="modal-close">×</button>
        </div>
        
        <div class="modal-body">
          <img 
            :src="previewModal.file?.preview"
            :alt="previewModal.file?.name"
            class="preview-full-image"
          />
        </div>
        
        <div class="modal-footer">
          <div class="image-info">
            <span>大小: {{ formatFileSize(previewModal.file?.size || 0) }}</span>
            <span>類型: {{ previewModal.file?.type }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, reactive } from 'vue'
import { useFileUpload } from '@/composables/useFileUpload'

// ===== Props =====
const props = defineProps({
  // 是否禁用
  disabled: {
    type: Boolean,
    default: false
  },
  
  // 緊湊模式
  compact: {
    type: Boolean,
    default: false
  }
})

// ===== Emits =====
const emit = defineEmits([
  'files-added',
  'file-removed',
  'files-cleared',
  'upload-complete',
  'upload-error'
])

// ===== Composable =====
const {
  isDragging,
  isUploading,
  uploadProgress,
  config,
  uploadedFiles,
  canAddMoreFiles,
  totalFileSizeFormatted,
  hasUploadingFiles,
  uploadStats,
  addFiles,
  removeFile,
  clearAllFiles,
  handleDragEnter,
  handleDragLeave,
  handleDragOver,
  handleDrop,
  handleFileSelect,
  triggerFileSelect,
  uploadAllFiles,
  formatFileSize
} = useFileUpload()

// ===== 狀態 =====
const fileInputRef = ref(null)
const previewModal = reactive({
  show: false,
  file: null
})

// ===== 計算屬性 =====
const uploadAreaClass = computed(() => {
  return {
    'dragging': isDragging.value,
    'disabled': props.disabled,
    'compact': props.compact,
    'has-files': uploadedFiles.value.length > 0
  }
})

// ===== 方法 =====

/**
 * 預覽圖片
 */
function previewImage(file) {
  previewModal.file = file
  previewModal.show = true
}

/**
 * 關閉預覽
 */
function closePreview() {
  previewModal.show = false
  previewModal.file = null
}

/**
 * 處理文件添加
 */
async function handleFilesAdded(files) {
  const result = await addFiles(files)
  
  if (result.success) {
    emit('files-added', result.files)
  } else {
    emit('upload-error', result.errors || result.error)
  }
}

/**
 * 處理文件移除
 */
function handleFileRemove(fileId) {
  removeFile(fileId)
  emit('file-removed', fileId)
}

/**
 * 處理清空文件
 */
function handleClearFiles() {
  clearAllFiles()
  emit('files-cleared')
}

/**
 * 處理上傳完成
 */
async function handleUploadAll() {
  const result = await uploadAllFiles()
  
  if (result.success) {
    emit('upload-complete', result.files)
  } else {
    emit('upload-error', result.error)
  }
}

// 重寫方法以觸發事件
const originalAddFiles = addFiles
const originalRemoveFile = removeFile
const originalClearAllFiles = clearAllFiles
const originalUploadAllFiles = uploadAllFiles

// 覆蓋方法
Object.assign(window, {
  addFiles: handleFilesAdded,
  removeFile: handleFileRemove,
  clearAllFiles: handleClearFiles,
  uploadAllFiles: handleUploadAll
})
</script>

<style lang="scss" scoped>
.image-upload {
  width: 100%;
}

.upload-area {
  border: 2px dashed #d1d5db;
  border-radius: 12px;
  padding: 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #fafafa;
  
  &:hover:not(.disabled) {
    border-color: #3b82f6;
    background: #f8faff;
  }
  
  &.dragging {
    border-color: #10b981;
    background: #f0fdf4;
    transform: scale(1.02);
  }
  
  &.disabled {
    opacity: 0.5;
    cursor: not-allowed;
    background: #f5f5f5;
  }
  
  &.compact {
    padding: 1rem;
  }
  
  &.has-files {
    margin-bottom: 1.5rem;
  }
}

.file-input {
  display: none;
}

.upload-prompt {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.upload-icon {
  font-size: 3rem;
  transition: transform 0.3s ease;
  
  .upload-area:hover & {
    transform: scale(1.1);
  }
}

.upload-text {
  .primary-text {
    font-size: 1.125rem;
    font-weight: 600;
    color: #374151;
    margin-bottom: 0.5rem;
  }
  
  .secondary-text {
    font-size: 0.875rem;
    color: #6b7280;
    line-height: 1.4;
  }
}

.browse-btn {
  padding: 0.75rem 1.5rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s ease;
  
  &:hover {
    background: #2563eb;
  }
}

.upload-limits {
  margin-top: 1rem;
  display: flex;
  justify-content: center;
  gap: 1rem;
  font-size: 0.75rem;
  color: #9ca3af;
}

.file-list {
  background: white;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  overflow: hidden;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}

.list-title {
  font-size: 1rem;
  font-weight: 600;
  color: #374151;
  margin: 0;
}

.list-actions {
  display: flex;
  gap: 0.5rem;
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
  
  &.upload-all-btn {
    border-color: #10b981;
    color: #059669;
    
    &:hover:not(:disabled) {
      background: rgba(16, 185, 129, 0.05);
    }
  }
  
  &.clear-btn {
    border-color: #ef4444;
    color: #dc2626;
    
    &:hover:not(:disabled) {
      background: rgba(239, 68, 68, 0.05);
    }
  }
}

.upload-progress-summary {
  padding: 1rem 1.5rem;
  background: #f0f9ff;
  border-bottom: 1px solid #e5e7eb;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  color: #374151;
}

.progress-bar {
  height: 6px;
  background: #e5e7eb;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #3b82f6;
  transition: width 0.3s ease;
}

.file-items {
  max-height: 400px;
  overflow-y: auto;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #f3f4f6;
  transition: background-color 0.2s ease;
  
  &:hover {
    background: #f9fafb;
  }
  
  &:last-child {
    border-bottom: none;
  }
  
  &.uploading {
    background: #f0f9ff;
  }
}

.file-preview {
  position: relative;
  width: 60px;
  height: 60px;
  border-radius: 8px;
  overflow: hidden;
  background: #f3f4f6;
  flex-shrink: 0;
}

.preview-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.preview-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  font-size: 1.5rem;
}

.upload-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
}

.progress-circle {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  
  .progress-text {
    color: white;
    font-size: 0.75rem;
    font-weight: 600;
  }
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-weight: 500;
  color: #374151;
  margin-bottom: 0.25rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-meta {
  display: flex;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: #9ca3af;
}

.file-actions {
  display: flex;
  gap: 0.25rem;
}

.file-action-btn {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 6px;
  background: #f3f4f6;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  
  &:hover:not(:disabled) {
    background: #e5e7eb;
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  
  &.preview-btn:hover {
    background: rgba(59, 130, 246, 0.1);
  }
  
  &.remove-btn:hover {
    background: rgba(239, 68, 68, 0.1);
  }
}

.preview-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 2rem;
}

.modal-content {
  background: white;
  border-radius: 12px;
  max-width: 90vw;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.modal-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #374151;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.modal-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #9ca3af;
  padding: 0;
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s ease;
  
  &:hover {
    background: #f3f4f6;
    color: #374151;
  }
}

.modal-body {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  overflow: hidden;
}

.preview-full-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: 8px;
}

.modal-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid #e5e7eb;
  background: #f9fafb;
}

.image-info {
  display: flex;
  gap: 1rem;
  font-size: 0.875rem;
  color: #6b7280;
}

@media (max-width: 768px) {
  .upload-area {
    padding: 1.5rem 1rem;
  }
  
  .upload-icon {
    font-size: 2rem;
  }
  
  .list-header {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }
  
  .list-actions {
    justify-content: center;
  }
  
  .file-item {
    padding: 0.75rem 1rem;
  }
  
  .file-preview {
    width: 50px;
    height: 50px;
  }
  
  .preview-modal {
    padding: 1rem;
  }
  
  .modal-content {
    max-width: 95vw;
    max-height: 95vh;
  }
}
</style>
