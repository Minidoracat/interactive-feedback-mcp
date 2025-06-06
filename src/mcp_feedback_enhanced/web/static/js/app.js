/**
 * MCP Feedback Enhanced - 完整回饋應用程式
 * ==========================================
 *
 * 支援完整的 UI 交互功能，包括頁籤切換、圖片處理、WebSocket 通信等
 */

/**
 * 標籤頁管理器 - 處理多標籤頁狀態同步和智能瀏覽器管理
 */
class TabManager {
    constructor() {
        this.tabId = this.generateTabId();
        this.heartbeatInterval = null;
        this.heartbeatFrequency = 5000; // 5秒心跳
        this.storageKey = 'mcp_feedback_tabs';
        this.lastActivityKey = 'mcp_feedback_last_activity';

        this.init();
    }

    generateTabId() {
        return `tab_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
    }

    init() {
        // 註冊當前標籤頁
        this.registerTab();

        // 向服務器註冊標籤頁
        this.registerTabToServer();

        // 開始心跳
        this.startHeartbeat();

        // 監聽頁面關閉事件
        window.addEventListener('beforeunload', () => {
            this.unregisterTab();
        });

        // 監聽 localStorage 變化（其他標籤頁的狀態變化）
        window.addEventListener('storage', (e) => {
            if (e.key === this.storageKey) {
                this.handleTabsChange();
            }
        });

        console.log(`📋 TabManager 初始化完成，標籤頁 ID: ${this.tabId}`);
    }

    registerTab() {
        const tabs = this.getActiveTabs();
        tabs[this.tabId] = {
            timestamp: Date.now(),
            url: window.location.href,
            active: true
        };
        localStorage.setItem(this.storageKey, JSON.stringify(tabs));
        this.updateLastActivity();
        console.log(`✅ 標籤頁已註冊: ${this.tabId}`);
    }

    unregisterTab() {
        const tabs = this.getActiveTabs();
        delete tabs[this.tabId];
        localStorage.setItem(this.storageKey, JSON.stringify(tabs));
        console.log(`❌ 標籤頁已註銷: ${this.tabId}`);
    }

    startHeartbeat() {
        this.heartbeatInterval = setInterval(() => {
            this.sendHeartbeat();
        }, this.heartbeatFrequency);
    }

    sendHeartbeat() {
        const tabs = this.getActiveTabs();
        if (tabs[this.tabId]) {
            tabs[this.tabId].timestamp = Date.now();
            localStorage.setItem(this.storageKey, JSON.stringify(tabs));
            this.updateLastActivity();
        }
    }

    updateLastActivity() {
        localStorage.setItem(this.lastActivityKey, Date.now().toString());
    }

    getActiveTabs() {
        try {
            const stored = localStorage.getItem(this.storageKey);
            const tabs = stored ? JSON.parse(stored) : {};

            // 清理過期的標籤頁（超過30秒沒有心跳）
            const now = Date.now();
            const expiredThreshold = 30000; // 30秒

            Object.keys(tabs).forEach(tabId => {
                if (now - tabs[tabId].timestamp > expiredThreshold) {
                    delete tabs[tabId];
                }
            });

            return tabs;
        } catch (error) {
            console.error('獲取活躍標籤頁失敗:', error);
            return {};
        }
    }

    hasActiveTabs() {
        const tabs = this.getActiveTabs();
        return Object.keys(tabs).length > 0;
    }

    isOnlyActiveTab() {
        const tabs = this.getActiveTabs();
        return Object.keys(tabs).length === 1 && tabs[this.tabId];
    }

    handleTabsChange() {
        // 處理其他標籤頁狀態變化
        console.log('🔄 檢測到其他標籤頁狀態變化');
    }

    async registerTabToServer() {
        try {
            const response = await fetch('/api/register-tab', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    tabId: this.tabId
                })
            });

            if (response.ok) {
                const data = await response.json();
                console.log(`✅ 標籤頁已向服務器註冊: ${this.tabId}`);
            } else {
                console.warn(`⚠️ 標籤頁服務器註冊失敗: ${response.status}`);
            }
        } catch (error) {
            console.warn(`⚠️ 標籤頁服務器註冊錯誤: ${error}`);
        }
    }

    cleanup() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
        }
        this.unregisterTab();
    }
}

class FeedbackApp {
    constructor(sessionId = null) {
        // 會話信息
        this.sessionId = sessionId;

        // 標籤頁管理
        this.tabManager = new TabManager();

        // WebSocket 相關
        this.websocket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.heartbeatInterval = null;
        this.heartbeatFrequency = 30000; // 30秒 WebSocket 心跳

        // UI 狀態
        this.currentTab = 'feedback';

        // 回饋狀態管理
        this.feedbackState = 'waiting_for_feedback'; // waiting_for_feedback, feedback_submitted, processing
        this.currentSessionId = null;
        this.lastSubmissionTime = null;

        // 圖片處理
        this.images = [];
        this.imageSizeLimit = 0;
        this.enableBase64Detail = false;

        // 設定
        this.autoClose = false;
        this.layoutMode = 'separate';

        // 語言設定
        this.currentLanguage = 'zh-TW';

        this.init();
    }

    async init() {
        console.log('初始化 MCP Feedback Enhanced 應用程式');

        try {
            // 等待國際化系統
            if (window.i18nManager) {
                await window.i18nManager.init();
            }

            // 初始化 UI 組件
            this.initUIComponents();

            // 設置事件監聽器
            this.setupEventListeners();

            // 設置 WebSocket 連接
            this.setupWebSocket();

            // 載入設定（異步等待完成）
            await this.loadSettings();

            // 初始化頁籤（在設定載入完成後）
            this.initTabs();

            // 初始化圖片處理
            this.initImageHandling();

            // 確保狀態指示器使用正確的翻譯（在國際化系統載入後）
            this.updateStatusIndicators();

            // 設置頁面關閉時的清理
            window.addEventListener('beforeunload', () => {
                if (this.tabManager) {
                    this.tabManager.cleanup();
                }
                if (this.heartbeatInterval) {
                    clearInterval(this.heartbeatInterval);
                }
            });

            console.log('MCP Feedback Enhanced 應用程式初始化完成');

        } catch (error) {
            console.error('應用程式初始化失敗:', error);
        }
    }

    initUIComponents() {
        // 基本 UI 元素
        this.connectionIndicator = document.getElementById('connectionIndicator');
        this.connectionText = document.getElementById('connectionText');

        // 頁籤相關元素
        this.tabButtons = document.querySelectorAll('.tab-button');
        this.tabContents = document.querySelectorAll('.tab-content');

        // 回饋相關元素
        this.feedbackText = document.getElementById('feedbackText');
        this.submitBtn = document.getElementById('submitBtn');
        this.cancelBtn = document.getElementById('cancelBtn');

        // 命令相關元素
        this.commandInput = document.getElementById('commandInput');
        this.commandOutput = document.getElementById('commandOutput');
        this.runCommandBtn = document.getElementById('runCommandBtn');

        // 動態初始化圖片相關元素
        this.initImageElements();
    }

    /**
     * 動態初始化圖片相關元素，支援多佈局模式
     */
    initImageElements() {
        // 根據當前佈局模式確定元素前綴
        const prefix = this.layoutMode && this.layoutMode.startsWith('combined') ? 'combined' : 'feedback';

        console.log(`🖼️ 初始化圖片元素，使用前綴: ${prefix}`);

        // 圖片相關元素 - 優先使用當前模式的元素
        this.imageInput = document.getElementById(`${prefix}ImageInput`) || document.getElementById('imageInput');
        this.imageUploadArea = document.getElementById(`${prefix}ImageUploadArea`) || document.getElementById('imageUploadArea');
        this.imagePreviewContainer = document.getElementById(`${prefix}ImagePreviewContainer`) || document.getElementById('imagePreviewContainer');
        this.imageSizeLimitSelect = document.getElementById(`${prefix}ImageSizeLimit`) || document.getElementById('imageSizeLimit');
        this.enableBase64DetailCheckbox = document.getElementById(`${prefix}EnableBase64Detail`) || document.getElementById('enableBase64Detail');

        // 記錄當前使用的前綴，用於後續操作
        this.currentImagePrefix = prefix;

        // 驗證關鍵元素是否存在
        if (!this.imageInput || !this.imageUploadArea) {
            console.warn(`⚠️ 圖片元素初始化失敗 - imageInput: ${!!this.imageInput}, imageUploadArea: ${!!this.imageUploadArea}`);
        } else {
            console.log(`✅ 圖片元素初始化成功 - 前綴: ${prefix}`);
        }
    }

    initTabs() {
        // 設置頁籤點擊事件
        this.tabButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const tabName = button.getAttribute('data-tab');
                this.switchTab(tabName);
            });
        });

        // 根據佈局模式確定初始頁籤
        let initialTab = this.currentTab;
        if (this.layoutMode.startsWith('combined')) {
            // 合併模式時，確保初始頁籤是 combined
            initialTab = 'combined';
        } else {
            // 分離模式時，如果當前頁籤是 combined，則切換到 feedback
            if (this.currentTab === 'combined') {
                initialTab = 'feedback';
            }
        }

        // 設置初始頁籤（不觸發保存，避免循環調用）
        this.setInitialTab(initialTab);
    }

    setInitialTab(tabName) {
        // 更新當前頁籤（不觸發保存）
        this.currentTab = tabName;

        // 更新按鈕狀態
        this.tabButtons.forEach(button => {
            if (button.getAttribute('data-tab') === tabName) {
                button.classList.add('active');
            } else {
                button.classList.remove('active');
            }
        });

        // 更新內容顯示
        this.tabContents.forEach(content => {
            if (content.id === `tab-${tabName}`) {
                content.classList.add('active');
            } else {
                content.classList.remove('active');
            }
        });

        // 特殊處理
        if (tabName === 'combined') {
            this.handleCombinedMode();
        }

        console.log(`初始化頁籤: ${tabName}`);
    }

    switchTab(tabName) {
        // 更新當前頁籤
        this.currentTab = tabName;

        // 更新按鈕狀態
        this.tabButtons.forEach(button => {
            if (button.getAttribute('data-tab') === tabName) {
                button.classList.add('active');
            } else {
                button.classList.remove('active');
            }
        });

        // 更新內容顯示
        this.tabContents.forEach(content => {
            if (content.id === `tab-${tabName}`) {
                content.classList.add('active');
            } else {
                content.classList.remove('active');
            }
        });

        // 特殊處理
        if (tabName === 'combined') {
            this.handleCombinedMode();
        }

        // 重新初始化圖片處理（確保使用正確的佈局模式元素）
        this.reinitializeImageHandling();

        // 保存當前頁籤設定
        this.saveSettings();

        console.log(`切換到頁籤: ${tabName}`);
    }

    /**
     * 重新初始化圖片處理功能
     */
    reinitializeImageHandling() {
        console.log('🔄 重新初始化圖片處理功能...');

        // 移除舊的事件監聽器
        this.removeImageEventListeners();

        // 重新初始化圖片元素
        this.initImageElements();

        // 如果有必要的元素，重新設置事件監聽器
        if (this.imageUploadArea && this.imageInput) {
            this.setupImageEventListeners();
            console.log('✅ 圖片處理功能重新初始化完成');
        } else {
            console.warn('⚠️ 圖片處理重新初始化失敗 - 缺少必要元素');
        }

        // 更新圖片預覽（確保在新的容器中顯示）
        this.updateImagePreview();
    }

    /**
     * 設置圖片事件監聽器
     */
    setupImageEventListeners() {
        // 文件選擇事件
        this.imageChangeHandler = (e) => {
            this.handleFileSelect(e.target.files);
        };
        this.imageInput.addEventListener('change', this.imageChangeHandler);

        // 點擊上傳區域
        this.imageClickHandler = () => {
            this.imageInput.click();
        };
        this.imageUploadArea.addEventListener('click', this.imageClickHandler);

        // 拖放事件
        this.imageDragOverHandler = (e) => {
            e.preventDefault();
            this.imageUploadArea.classList.add('dragover');
        };
        this.imageUploadArea.addEventListener('dragover', this.imageDragOverHandler);

        this.imageDragLeaveHandler = (e) => {
            e.preventDefault();
            this.imageUploadArea.classList.remove('dragover');
        };
        this.imageUploadArea.addEventListener('dragleave', this.imageDragLeaveHandler);

        this.imageDropHandler = (e) => {
            e.preventDefault();
            this.imageUploadArea.classList.remove('dragover');
            this.handleFileSelect(e.dataTransfer.files);
        };
        this.imageUploadArea.addEventListener('drop', this.imageDropHandler);

        // 初始化圖片設定事件
        this.initImageSettings();
    }

    initImageHandling() {
        console.log('🖼️ 開始初始化圖片處理功能...');

        // 重新初始化圖片元素（確保使用最新的佈局模式）
        this.initImageElements();

        if (!this.imageUploadArea || !this.imageInput) {
            console.warn('⚠️ 圖片處理初始化失敗 - 缺少必要元素');
            return;
        }

        // 清除舊的事件監聽器（如果存在）
        this.removeImageEventListeners();

        // 設置圖片事件監聽器
        this.setupImageEventListeners();

        // 設置全域剪貼板貼上事件（只設置一次）
        if (!this.pasteHandler) {
            this.pasteHandler = (e) => {
                const items = e.clipboardData.items;
                for (let item of items) {
                    if (item.type.indexOf('image') !== -1) {
                        e.preventDefault();
                        const file = item.getAsFile();
                        this.handleFileSelect([file]);
                        break;
                    }
                }
            };
            document.addEventListener('paste', this.pasteHandler);
            console.log('✅ 全域剪貼板貼上事件已設置');
        }

        console.log('✅ 圖片處理功能初始化完成');
    }

    /**
     * 移除舊的圖片事件監聽器
     */
    removeImageEventListeners() {
        if (this.imageInput && this.imageChangeHandler) {
            this.imageInput.removeEventListener('change', this.imageChangeHandler);
        }
        if (this.imageUploadArea) {
            if (this.imageClickHandler) {
                this.imageUploadArea.removeEventListener('click', this.imageClickHandler);
            }
            if (this.imageDragOverHandler) {
                this.imageUploadArea.removeEventListener('dragover', this.imageDragOverHandler);
            }
            if (this.imageDragLeaveHandler) {
                this.imageUploadArea.removeEventListener('dragleave', this.imageDragLeaveHandler);
            }
            if (this.imageDropHandler) {
                this.imageUploadArea.removeEventListener('drop', this.imageDropHandler);
            }
        }
    }

    /**
     * 初始化圖片設定事件
     */
    initImageSettings() {
        // 圖片大小限制設定
        if (this.imageSizeLimitSelect) {
            this.imageSizeLimitSelect.addEventListener('change', (e) => {
                this.imageSizeLimit = parseInt(e.target.value);
                this.saveSettings();
            });
        }

        // Base64 詳細模式設定
        if (this.enableBase64DetailCheckbox) {
            this.enableBase64DetailCheckbox.addEventListener('change', (e) => {
                this.enableBase64Detail = e.target.checked;
                this.saveSettings();
            });
        }

        // 同步設定到其他佈局模式
        this.syncImageSettingsAcrossLayouts();
    }

    /**
     * 同步圖片設定到所有佈局模式
     */
    syncImageSettingsAcrossLayouts() {
        const prefixes = ['feedback', 'combined'];

        prefixes.forEach(prefix => {
            const sizeSelect = document.getElementById(`${prefix}ImageSizeLimit`);
            const base64Checkbox = document.getElementById(`${prefix}EnableBase64Detail`);

            if (sizeSelect && sizeSelect !== this.imageSizeLimitSelect) {
                sizeSelect.value = this.imageSizeLimit.toString();
                sizeSelect.addEventListener('change', (e) => {
                    this.imageSizeLimit = parseInt(e.target.value);
                    // 同步到其他元素
                    prefixes.forEach(otherPrefix => {
                        const otherSelect = document.getElementById(`${otherPrefix}ImageSizeLimit`);
                        if (otherSelect && otherSelect !== e.target) {
                            otherSelect.value = e.target.value;
                        }
                    });
                    this.saveSettings();
                });
            }

            if (base64Checkbox && base64Checkbox !== this.enableBase64DetailCheckbox) {
                base64Checkbox.checked = this.enableBase64Detail;
                base64Checkbox.addEventListener('change', (e) => {
                    this.enableBase64Detail = e.target.checked;
                    // 同步到其他元素
                    prefixes.forEach(otherPrefix => {
                        const otherCheckbox = document.getElementById(`${otherPrefix}EnableBase64Detail`);
                        if (otherCheckbox && otherCheckbox !== e.target) {
                            otherCheckbox.checked = e.target.checked;
                        }
                    });
                    this.saveSettings();
                });
            }
        });
    }

    handleFileSelect(files) {
        for (let file of files) {
            if (file.type.startsWith('image/')) {
                this.addImage(file);
            }
        }
    }

    async addImage(file) {
        // 檢查文件大小
        if (this.imageSizeLimit > 0 && file.size > this.imageSizeLimit) {
            alert(`圖片大小超過限制 (${this.formatFileSize(this.imageSizeLimit)})`);
            return;
        }

        try {
            const base64 = await this.fileToBase64(file);
            const imageData = {
                name: file.name,
                size: file.size,
                type: file.type,
                data: base64
            };

            this.images.push(imageData);
            this.updateImagePreview();

        } catch (error) {
            console.error('圖片處理失敗:', error);
            alert('圖片處理失敗，請重試');
        }
    }

    fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result.split(',')[1]);
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }

    updateImagePreview() {
        // 更新所有佈局模式的圖片預覽容器
        const previewContainers = [
            document.getElementById('feedbackImagePreviewContainer'),
            document.getElementById('combinedImagePreviewContainer'),
            this.imagePreviewContainer // 當前主要容器
        ].filter(container => container); // 過濾掉不存在的容器

        if (previewContainers.length === 0) {
            console.warn('⚠️ 沒有找到圖片預覽容器');
            return;
        }

        console.log(`🖼️ 更新 ${previewContainers.length} 個圖片預覽容器`);

        previewContainers.forEach(container => {
            container.innerHTML = '';

            this.images.forEach((image, index) => {
                // 創建圖片預覽項目容器
                const preview = document.createElement('div');
                preview.className = 'image-preview-item';
                preview.style.position = 'relative';
                preview.style.display = 'inline-block';

                // 創建圖片元素
                const img = document.createElement('img');
                img.src = `data:${image.type};base64,${image.data}`;
                img.alt = image.name;
                img.style.width = '80px';
                img.style.height = '80px';
                img.style.objectFit = 'cover';
                img.style.display = 'block';
                img.style.borderRadius = '6px';

                // 創建圖片信息容器
                const imageInfo = document.createElement('div');
                imageInfo.className = 'image-info';
                imageInfo.style.position = 'absolute';
                imageInfo.style.bottom = '0';
                imageInfo.style.left = '0';
                imageInfo.style.right = '0';
                imageInfo.style.background = 'rgba(0, 0, 0, 0.7)';
                imageInfo.style.color = 'white';
                imageInfo.style.padding = '4px';
                imageInfo.style.fontSize = '10px';
                imageInfo.style.lineHeight = '1.2';

                // 創建文件名元素
                const imageName = document.createElement('div');
                imageName.className = 'image-name';
                imageName.textContent = image.name;
                imageName.style.fontWeight = 'bold';
                imageName.style.overflow = 'hidden';
                imageName.style.textOverflow = 'ellipsis';
                imageName.style.whiteSpace = 'nowrap';

                // 創建文件大小元素
                const imageSize = document.createElement('div');
                imageSize.className = 'image-size';
                imageSize.textContent = this.formatFileSize(image.size);
                imageSize.style.fontSize = '9px';
                imageSize.style.opacity = '0.8';

                // 創建刪除按鈕
                const removeBtn = document.createElement('button');
                removeBtn.className = 'image-remove-btn';
                removeBtn.textContent = '×';
                removeBtn.title = '移除圖片';
                removeBtn.style.position = 'absolute';
                removeBtn.style.top = '-8px';
                removeBtn.style.right = '-8px';
                removeBtn.style.width = '20px';
                removeBtn.style.height = '20px';
                removeBtn.style.borderRadius = '50%';
                removeBtn.style.background = '#f44336';
                removeBtn.style.color = 'white';
                removeBtn.style.border = 'none';
                removeBtn.style.cursor = 'pointer';
                removeBtn.style.fontSize = '12px';
                removeBtn.style.fontWeight = 'bold';
                removeBtn.style.display = 'flex';
                removeBtn.style.alignItems = 'center';
                removeBtn.style.justifyContent = 'center';
                removeBtn.style.boxShadow = '0 2px 4px rgba(0, 0, 0, 0.3)';
                removeBtn.style.transition = 'all 0.3s ease';
                removeBtn.style.zIndex = '10';

                // 添加刪除按鈕懸停效果
                removeBtn.addEventListener('mouseenter', () => {
                    removeBtn.style.background = '#d32f2f';
                    removeBtn.style.transform = 'scale(1.1)';
                });
                removeBtn.addEventListener('mouseleave', () => {
                    removeBtn.style.background = '#f44336';
                    removeBtn.style.transform = 'scale(1)';
                });

                // 添加刪除功能
                removeBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    this.removeImage(index);
                });

                // 組裝元素
                imageInfo.appendChild(imageName);
                imageInfo.appendChild(imageSize);

                preview.appendChild(img);
                preview.appendChild(imageInfo);
                preview.appendChild(removeBtn);

                container.appendChild(preview);
            });
        });

        // 更新圖片計數顯示
        this.updateImageCount();
    }

    /**
     * 更新圖片計數顯示
     */
    updateImageCount() {
        const count = this.images.length;
        const countElements = document.querySelectorAll('.image-count');

        countElements.forEach(element => {
            element.textContent = count > 0 ? `(${count})` : '';
        });

        // 更新上傳區域的顯示狀態
        const uploadAreas = [
            document.getElementById('feedbackImageUploadArea'),
            document.getElementById('combinedImageUploadArea')
        ].filter(area => area);

        uploadAreas.forEach(area => {
            if (count > 0) {
                area.classList.add('has-images');
            } else {
                area.classList.remove('has-images');
            }
        });
    }

    removeImage(index) {
        this.images.splice(index, 1);
        this.updateImagePreview();
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // ==================== 狀態管理系統 ====================

    /**
     * 設置回饋狀態
     * @param {string} state - waiting_for_feedback, feedback_submitted, processing
     * @param {string} sessionId - 當前會話 ID
     */
    setFeedbackState(state, sessionId = null) {
        const previousState = this.feedbackState;
        this.feedbackState = state;

        if (sessionId && sessionId !== this.currentSessionId) {
            // 新會話開始，重置狀態
            this.currentSessionId = sessionId;
            this.lastSubmissionTime = null;
            console.log(`🔄 新會話開始: ${sessionId.substring(0, 8)}...`);
        }

        console.log(`📊 狀態變更: ${previousState} → ${state}`);
        this.updateUIState();
        this.updateStatusIndicator();
    }

    /**
     * 檢查是否可以提交回饋
     */
    canSubmitFeedback() {
        // 臨時修復：允許在等待回饋狀態下輸入，即使 WebSocket 未連接
        // 這樣用戶可以先輸入內容，等連接建立後再提交
        const canInput = this.feedbackState === 'waiting_for_feedback';
        const canSubmit = canInput && this.isConnected;
        console.log(`🔍 檢查提交權限: feedbackState=${this.feedbackState}, isConnected=${this.isConnected}, canInput=${canInput}, canSubmit=${canSubmit}`);
        return canSubmit;
    }

    /**
     * 檢查是否可以輸入回饋（允許離線輸入）
     */
    canInputFeedback() {
        return this.feedbackState === 'waiting_for_feedback';
    }

    /**
     * 檢查是否有待處理的會話更新
     */
    checkForPendingUpdates() {
        console.log('🔍 檢查是否有待處理的會話更新...');
        // 這個方法會在 WebSocket 連接建立後被調用
        // 服務器會自動發送 session_updated 或 status_update 消息
        // 所以這裡只需要記錄日誌，實際處理在消息處理器中完成
    }

    /**
     * 更新 UI 狀態
     */
    updateUIState() {
        // 更新提交按鈕狀態
        if (this.submitBtn) {
            const canSubmit = this.canSubmitFeedback();
            this.submitBtn.disabled = !canSubmit;

            switch (this.feedbackState) {
                case 'waiting_for_feedback':
                    this.submitBtn.textContent = window.i18nManager ? window.i18nManager.t('buttons.submit') : '提交回饋';
                    this.submitBtn.className = 'btn btn-primary';
                    break;
                case 'processing':
                    this.submitBtn.textContent = window.i18nManager ? window.i18nManager.t('buttons.processing') : '處理中...';
                    this.submitBtn.className = 'btn btn-secondary';
                    break;
                case 'feedback_submitted':
                    this.submitBtn.textContent = window.i18nManager ? window.i18nManager.t('buttons.submitted') : '已提交';
                    this.submitBtn.className = 'btn btn-success';
                    break;
            }
        }

        // 更新回饋文字框狀態（允許離線輸入）
        if (this.feedbackText) {
            this.feedbackText.disabled = !this.canInputFeedback();
        }

        // 更新合併模式的回饋文字框狀態（允許離線輸入）
        const combinedFeedbackText = document.getElementById('combinedFeedbackText');
        if (combinedFeedbackText) {
            combinedFeedbackText.disabled = !this.canInputFeedback();
        }

        // 更新圖片上傳狀態（允許離線上傳）
        if (this.imageUploadArea) {
            if (this.canInputFeedback()) {
                this.imageUploadArea.classList.remove('disabled');
            } else {
                this.imageUploadArea.classList.add('disabled');
            }
        }

        // 更新合併模式的圖片上傳狀態（允許離線上傳）
        const combinedImageUploadArea = document.getElementById('combinedImageUploadArea');
        if (combinedImageUploadArea) {
            if (this.canInputFeedback()) {
                combinedImageUploadArea.classList.remove('disabled');
            } else {
                combinedImageUploadArea.classList.add('disabled');
            }
        }
    }

    /**
     * 更新狀態指示器（新版本：只更新現有元素的狀態）
     */
    updateStatusIndicator() {
        // 獲取狀態指示器元素
        const feedbackStatusIndicator = document.getElementById('feedbackStatusIndicator');
        const combinedStatusIndicator = document.getElementById('combinedFeedbackStatusIndicator');

        // 根據當前狀態確定圖示、標題和訊息
        let icon, title, message, status;

        switch (this.feedbackState) {
            case 'waiting_for_feedback':
                icon = '⏳';
                title = window.i18nManager ? window.i18nManager.t('status.waiting.title') : '等待回饋';
                message = window.i18nManager ? window.i18nManager.t('status.waiting.message') : '請提供您的回饋意見';
                status = 'waiting';
                break;

            case 'processing':
                icon = '⚙️';
                title = window.i18nManager ? window.i18nManager.t('status.processing.title') : '處理中';
                message = window.i18nManager ? window.i18nManager.t('status.processing.message') : '正在提交您的回饋...';
                status = 'processing';
                break;

            case 'feedback_submitted':
                const timeStr = this.lastSubmissionTime ?
                    new Date(this.lastSubmissionTime).toLocaleTimeString() : '';
                icon = '✅';
                title = window.i18nManager ? window.i18nManager.t('status.submitted.title') : '回饋已提交';
                message = window.i18nManager ? window.i18nManager.t('status.submitted.message') : '等待下次 MCP 調用';
                if (timeStr) {
                    message += ` (${timeStr})`;
                }
                status = 'submitted';
                break;

            default:
                // 預設狀態
                icon = '⏳';
                title = '等待回饋';
                message = '請提供您的回饋意見';
                status = 'waiting';
        }

        // 更新分頁模式的狀態指示器
        if (feedbackStatusIndicator) {
            this.updateStatusIndicatorElement(feedbackStatusIndicator, status, icon, title, message);
        }

        // 更新合併模式的狀態指示器
        if (combinedStatusIndicator) {
            this.updateStatusIndicatorElement(combinedStatusIndicator, status, icon, title, message);
        }

        console.log(`✅ 狀態指示器已更新: ${status} - ${title}`);
    }

    /**
     * 更新單個狀態指示器元素
     */
    updateStatusIndicatorElement(element, status, icon, title, message) {
        if (!element) return;

        // 更新狀態類別
        element.className = `feedback-status-indicator status-${status}`;
        element.style.display = 'block';

        // 更新標題（包含圖示）
        const titleElement = element.querySelector('.status-title');
        if (titleElement) {
            titleElement.textContent = `${icon} ${title}`;
        }

        // 更新訊息
        const messageElement = element.querySelector('.status-message');
        if (messageElement) {
            messageElement.textContent = message;
        }

        console.log(`🔧 已更新狀態指示器: ${element.id} -> ${status}`);
    }

    setupWebSocket() {
        // 確保 WebSocket URL 格式正確
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const wsUrl = `${protocol}//${host}/ws/v2`; // 🔄 遷移到事件驅動端點

        console.log('🔗 嘗試連接事件驅動 WebSocket:', wsUrl);
        this.updateConnectionStatus('connecting', '連接中...');

        try {
            // 如果已有連接，先關閉
            if (this.websocket) {
                this.websocket.close();
                this.websocket = null;
            }

            // 初始化 API 客戶端（如果尚未初始化）
            if (!this.apiClient) {
                // 檢查 EventDrivenAPIClient 是否可用
                if (typeof EventDrivenAPIClient === 'undefined') {
                    console.error('❌ EventDrivenAPIClient 未定義，請檢查 api-client.js 是否正確載入');
                    this.updateConnectionStatus('error', 'API 客戶端載入失敗');
                    return;
                }

                this.apiClient = new EventDrivenAPIClient();
                this.healthMonitor = new HealthMonitor(this.apiClient);
                console.log('✅ 事件驅動 API 客戶端已初始化');
            }

            this.websocket = new WebSocket(wsUrl);

            this.websocket.onopen = () => {
                this.isConnected = true;
                this.updateConnectionStatus('connected', '已連接');
                console.log('✅ 事件驅動 WebSocket 連接已建立');

                // 重置重連計數器
                this.reconnectAttempts = 0;

                // 開始 WebSocket 心跳
                this.startWebSocketHeartbeat();

                // 開始健康監控
                if (this.healthMonitor) {
                    this.healthMonitor.startMonitoring();
                }

                // 連接成功後，請求會話狀態
                this.requestSessionStatus();

                // 如果之前處於處理狀態但連接斷開，重置為等待狀態
                if (this.feedbackState === 'processing') {
                    console.log('🔄 WebSocket 重連後重置處理狀態');
                    this.setFeedbackState('waiting_for_feedback');
                }
            };

            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('解析 WebSocket 消息失敗:', error);
                }
            };

            this.websocket.onclose = (event) => {
                this.isConnected = false;
                console.log('🔌 事件驅動 WebSocket 連接已關閉, code:', event.code, 'reason:', event.reason);

                // 停止心跳
                this.stopWebSocketHeartbeat();

                // 停止健康監控
                if (this.healthMonitor) {
                    this.healthMonitor.stopMonitoring();
                }

                // 重置回饋狀態，避免卡在處理狀態
                if (this.feedbackState === 'processing') {
                    console.log('🔄 WebSocket 斷開，重置處理狀態');
                    this.setFeedbackState('waiting_for_feedback');
                }

                if (event.code === 4004) {
                    // 沒有活躍會話
                    this.updateConnectionStatus('disconnected', '沒有活躍會話');
                } else if (event.code === 4005) {
                    // 架構初始化失敗
                    this.updateConnectionStatus('error', '架構初始化失敗');
                    this.showMessage('事件驅動架構初始化失敗，請刷新頁面重試', 'error');
                } else {
                    this.updateConnectionStatus('disconnected', '已斷開');

                    // 只有在非正常關閉時才重連
                    if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
                        this.reconnectAttempts++;
                        const delay = Math.min(3000 * this.reconnectAttempts, 15000); // 最大延遲15秒
                        console.log(`⏳ ${delay/1000}秒後嘗試重連... (第${this.reconnectAttempts}次)`);
                        setTimeout(() => {
                            console.log(`🔄 開始重連事件驅動 WebSocket... (第${this.reconnectAttempts}次)`);
                            this.setupWebSocket();
                        }, delay);
                    } else if (this.reconnectAttempts >= this.maxReconnectAttempts) {
                        console.log('❌ 達到最大重連次數，停止重連');
                        this.showMessage('事件驅動 WebSocket 連接失敗，請刷新頁面重試', 'error');
                    }
                }
            };

            this.websocket.onerror = (error) => {
                console.error('❌ 事件驅動 WebSocket 錯誤:', error);
                this.updateConnectionStatus('error', '連接錯誤');
            };

        } catch (error) {
            console.error('❌ 事件驅動 WebSocket 連接失敗:', error);
            this.updateConnectionStatus('error', '連接失敗');
        }
    }

    requestSessionStatus() {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({
                type: 'get_status'
            }));
        }
    }

    startWebSocketHeartbeat() {
        // 清理現有心跳
        this.stopWebSocketHeartbeat();

        this.heartbeatInterval = setInterval(() => {
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send(JSON.stringify({
                    type: 'heartbeat',
                    tabId: this.tabManager.tabId,
                    timestamp: Date.now()
                }));
            }
        }, this.heartbeatFrequency);

        console.log(`💓 WebSocket 心跳已啟動，頻率: ${this.heartbeatFrequency}ms`);
    }

    stopWebSocketHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
            console.log('💔 WebSocket 心跳已停止');
        }
    }

    handleWebSocketMessage(data) {
        console.log('📨 收到事件驅動 WebSocket 消息:', data);

        // 事件驅動消息處理
        switch (data.type) {
            case 'connection_established':
                console.log('✅ 事件驅動連接確認');
                this.handleConnectionEstablished(data);
                break;
            case 'heartbeat_response':
                // 心跳回應，更新標籤頁活躍狀態
                this.tabManager.updateLastActivity();
                break;
            case 'command_output':
                this.appendCommandOutput(data.output);
                break;
            case 'command_complete':
                this.appendCommandOutput(`\n[命令完成，退出碼: ${data.exit_code}]\n`);
                this.enableCommandInput();
                break;
            case 'command_error':
                this.appendCommandOutput(`\n[錯誤: ${data.error}]\n`);
                this.enableCommandInput();
                break;
            case 'feedback_received':
                console.log('✅ 回饋已收到');
                this.handleFeedbackReceived(data);
                break;
            case 'status_update':
                console.log('📊 狀態更新:', data.status_info);
                this.handleStatusUpdate(data.status_info);
                break;
            case 'session_updated':
                console.log('🔄 收到會話更新消息:', data.session_info);
                this.handleEventDrivenSessionUpdate(data);
                break;
            case 'state_changed':
                console.log('🔄 狀態變更:', data);
                this.handleStateChange(data);
                break;
            default:
                console.log('⚠️ 未處理的事件驅動消息類型:', data.type);
        }
    }

    /**
     * 處理事件驅動連接建立
     */
    handleConnectionEstablished(data) {
        console.log('🔗 事件驅動連接已建立:', data);

        // 儲存連接 ID
        if (data.connection_id) {
            this.connectionId = data.connection_id;
            console.log(`📋 連接 ID: ${this.connectionId}`);
        }

        // 檢查是否有待處理的會話更新
        this.checkForPendingUpdates();

        // 同步狀態
        this.syncStateWithServer();
    }

    /**
     * 處理狀態變更事件
     */
    handleStateChange(data) {
        console.log('🔄 處理狀態變更:', data);

        const { state_type, new_state, session_id } = data;

        switch (state_type) {
            case 'session_state':
                this.handleSessionStateChange(new_state, session_id);
                break;
            case 'connection_state':
                this.handleConnectionStateChange(new_state);
                break;
            default:
                console.log(`⚠️ 未知狀態類型: ${state_type}`);
        }
    }

    /**
     * 處理會話狀態變更
     */
    handleSessionStateChange(newState, sessionId) {
        console.log(`📋 會話狀態變更: ${newState} (會話: ${sessionId})`);

        switch (newState) {
            case 'active':
                this.setFeedbackState('waiting_for_feedback', sessionId);
                break;
            case 'feedback_submitted':
                this.setFeedbackState('feedback_submitted', sessionId);
                break;
            case 'completed':
                this.setFeedbackState('waiting_for_feedback', sessionId);
                break;
        }
    }

    /**
     * 處理連接狀態變更
     */
    handleConnectionStateChange(newState) {
        console.log(`🔌 連接狀態變更: ${newState}`);

        switch (newState) {
            case 'connected':
                this.updateConnectionStatus('connected', '已連接');
                break;
            case 'disconnected':
                this.updateConnectionStatus('disconnected', '已斷開');
                break;
            case 'error':
                this.updateConnectionStatus('error', '連接錯誤');
                break;
        }
    }

    handleFeedbackReceived(data) {
        // 使用新的狀態管理系統
        this.setFeedbackState('feedback_submitted');
        this.lastSubmissionTime = Date.now();

        // 顯示成功訊息
        this.showSuccessMessage(data.message || '回饋提交成功！');

        // 更新 AI 摘要區域顯示「已送出反饋」狀態
        this.updateSummaryStatus('已送出反饋，等待下次 MCP 調用...');

        // 重構：不再自動關閉頁面，保持持久性
        console.log('反饋已提交，頁面保持開啟狀態');
    }

    /**
     * 事件驅動的會話更新處理器
     */
    handleEventDrivenSessionUpdate(data) {
        console.log('🔄 處理事件驅動會話更新:', data.session_info);

        // 顯示更新通知
        this.showUpdateNotification(data.message || '會話已更新，正在智能更新內容...');

        // 智能局部更新
        this.performSmartUpdate(data.session_info);
    }

    /**
     * 執行智能局部更新
     */
    async performSmartUpdate(sessionInfo) {
        console.log('🧠 開始智能局部更新...');

        try {
            // 1. 更新會話信息
            if (sessionInfo) {
                const newSessionId = sessionInfo.session_id;
                console.log(`📋 會話 ID 更新: ${this.currentSessionId} -> ${newSessionId}`);

                // 重置回饋狀態為等待新回饋
                this.setFeedbackState('waiting_for_feedback', newSessionId);
                this.currentSessionId = newSessionId;

                // 更新頁面標題
                if (sessionInfo.project_directory) {
                    const projectName = sessionInfo.project_directory.split(/[/\\]/).pop();
                    document.title = `MCP Feedback - ${projectName}`;
                }
            }

            // 2. 同步狀態
            await this.syncStateWithServer();

            // 3. 智能更新 UI 組件
            await this.updateUIComponentsSmart(sessionInfo);

            // 4. 重置表單狀態
            this.resetFeedbackForm();

            // 5. 更新狀態指示器
            this.updateStatusIndicators();

            console.log('✅ 智能局部更新完成');

        } catch (error) {
            console.error('❌ 智能局部更新失敗:', error);
            // 備用方案：使用傳統局部更新
            this.refreshPageContent();
        }
    }

    /**
     * 智能更新 UI 組件
     */
    async updateUIComponentsSmart(sessionInfo) {
        console.log('🎨 智能更新 UI 組件...');

        // 使用事件驅動 API 獲取最新數據
        const result = await this.apiClient.get('/session/current');

        if (result.success && result.data) {
            const latestData = result.data;

            // 更新 AI 摘要內容
            if (latestData.summary) {
                this.updateAISummaryContent(latestData.summary);
            }

            // 更新項目信息
            if (latestData.project_directory) {
                this.updateProjectInfo(latestData.project_directory);
            }

            console.log('✅ UI 組件智能更新完成');
        } else {
            console.warn('⚠️ 無法獲取最新會話數據，使用傳統更新方式');
            throw new Error('API 請求失敗');
        }
    }

    /**
     * 同步狀態與服務器
     */
    async syncStateWithServer() {
        console.log('🔄 同步狀態與服務器...');

        try {
            // 使用現有的 /session/current 端點而不是不存在的 /session/status
            const result = await this.apiClient.get('/session/current');

            if (result.success && result.data) {
                const sessionData = result.data.session; // /session/current 返回的是 {status, session}
                console.log('📊 服務器會話數據:', sessionData);

                if (sessionData) {
                    // 同步會話狀態
                    if (sessionData.session_id && sessionData.session_id !== this.currentSessionId) {
                        this.currentSessionId = sessionData.session_id;
                        console.log(`📋 同步會話 ID: ${this.currentSessionId}`);
                    }

                    // 根據會話狀態推斷回饋狀態
                    if (sessionData.status) {
                        let newFeedbackState = 'waiting_for_feedback';
                        switch (sessionData.status) {
                            case 'feedback_submitted':
                                newFeedbackState = 'feedback_submitted';
                                break;
                            case 'active':
                            case 'waiting':
                                newFeedbackState = 'waiting_for_feedback';
                                break;
                        }

                        if (newFeedbackState !== this.feedbackState) {
                            this.setFeedbackState(newFeedbackState);
                            console.log(`🔄 同步回饋狀態: ${this.feedbackState}`);
                        }
                    }
                }

                console.log('✅ 狀態同步完成');
            }
        } catch (error) {
            console.warn('⚠️ 狀態同步失敗:', error);
        }
    }

    handleSessionUpdated(data) {
        console.log('🔄 處理會話更新:', data.session_info);

        // 顯示更新通知
        this.showSuccessMessage(data.message || '會話已更新，正在局部更新內容...');

        // 更新會話信息
        if (data.session_info) {
            const newSessionId = data.session_info.session_id;
            console.log(`📋 會話 ID 更新: ${this.currentSessionId} -> ${newSessionId}`);

            // 重置回饋狀態為等待新回饋（使用新的會話 ID）
            this.setFeedbackState('waiting_for_feedback', newSessionId);

            // 更新當前會話 ID
            this.currentSessionId = newSessionId;

            // 更新頁面標題
            if (data.session_info.project_directory) {
                const projectName = data.session_info.project_directory.split(/[/\\]/).pop();
                document.title = `MCP Feedback - ${projectName}`;
            }

            // 使用局部更新替代整頁刷新
            this.refreshPageContent();
        } else {
            // 如果沒有會話信息，仍然重置狀態
            console.log('⚠️ 會話更新沒有包含會話信息，僅重置狀態');
            this.setFeedbackState('waiting_for_feedback');
        }

        console.log('✅ 會話更新處理完成');
    }

    /**
     * 顯示更新通知
     */
    showUpdateNotification(message = '內容已更新') {
        console.log('📢 顯示更新通知:', message);

        // 創建更新通知元素
        const notification = document.createElement('div');
        notification.className = 'update-notification';
        notification.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            z-index: 1002;
            padding: 12px 20px;
            background: linear-gradient(135deg, #4CAF50, #45a049);
            color: white;
            border-radius: 8px;
            box-shadow: 0 4px 16px rgba(76, 175, 80, 0.3);
            max-width: 320px;
            word-wrap: break-word;
            animation: slideInRight 0.3s ease-out;
            border-left: 4px solid #2E7D32;
        `;

        notification.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 16px;">🔄</span>
                <span>${message}</span>
            </div>
        `;

        document.body.appendChild(notification);

        // 3秒後自動移除
        setTimeout(() => {
            if (notification.parentNode) {
                notification.style.animation = 'slideOutRight 0.3s ease-in';
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, 300);
            }
        }, 3000);
    }

    /**
     * 更新項目信息
     */
    updateProjectInfo(projectDirectory) {
        console.log('📁 更新項目信息:', projectDirectory);

        // 更新頁面標題
        const projectName = projectDirectory.split(/[/\\]/).pop();
        document.title = `MCP Feedback - ${projectName}`;

        // 更新項目目錄顯示
        const projectInfoElements = document.querySelectorAll('.project-info, [data-project-directory]');
        projectInfoElements.forEach(element => {
            if (element.hasAttribute('data-project-directory')) {
                element.textContent = projectDirectory;
            } else {
                element.innerHTML = `<span data-i18n="app.projectDirectory">專案目錄</span>: ${projectDirectory}`;
            }
        });

        console.log('✅ 項目信息更新完成');
    }

    async refreshPageContent() {
        console.log('🔄 局部更新頁面內容...');

        try {
            // 保存當前標籤頁狀態到 localStorage
            if (this.tabManager) {
                this.tabManager.updateLastActivity();
            }

            // 使用局部更新替代整頁刷新
            await this.updatePageContentPartially();

            // 確保 UI 狀態正確更新
            this.updateUIState();

            console.log('✅ 頁面內容局部更新完成');

        } catch (error) {
            console.error('❌ 局部更新頁面內容失敗:', error);
            // 備用方案：顯示提示讓用戶手動刷新
            this.showMessage('更新內容失敗，請手動刷新頁面以查看新的 AI 工作摘要', 'warning');
        }
    }

    /**
     * 局部更新頁面內容，避免整頁刷新（事件驅動版本）
     */
    async updatePageContentPartially() {
        console.log('🔄 開始事件驅動局部更新頁面內容...');

        try {
            // 1. 使用事件驅動 API 獲取最新的會話資料
            const result = await this.apiClient.get('/session/current');

            if (!result.success) {
                // 備用方案：使用傳統 API
                console.warn('⚠️ 事件驅動 API 失敗，使用傳統 API');
                const response = await fetch('/api/current-session');
                if (!response.ok) {
                    throw new Error(`API 請求失敗: ${response.status}`);
                }
                const sessionData = await response.json();
                this.processSessionData(sessionData);
                return;
            }

            const sessionData = result.data;
            console.log('📥 獲取到最新會話資料 (事件驅動):', sessionData);

            // 2. 處理會話數據
            this.processSessionData(sessionData);

            console.log('✅ 事件驅動局部更新完成');

        } catch (error) {
            console.error('❌ 事件驅動局部更新失敗:', error);
            throw error; // 重新拋出錯誤，讓調用者處理
        }
    }

    /**
     * 處理會話數據
     */
    processSessionData(sessionData) {
        console.log('📊 處理會話數據...');

        // 1. 更新 AI 摘要內容
        if (sessionData.summary) {
            this.updateAISummaryContent(sessionData.summary);
        }

        // 2. 重置回饋表單
        this.resetFeedbackForm();

        // 3. 更新狀態指示器
        this.updateStatusIndicators();

        // 4. 更新項目信息
        if (sessionData.project_directory) {
            this.updateProjectInfo(sessionData.project_directory);
        }

        // 5. 更新會話 ID
        if (sessionData.session_id && sessionData.session_id !== this.currentSessionId) {
            this.currentSessionId = sessionData.session_id;
            console.log(`📋 更新會話 ID: ${this.currentSessionId}`);
        }

        console.log('✅ 會話數據處理完成');
    }

    /**
     * 更新 AI 摘要內容
     */
    updateAISummaryContent(summary) {
        console.log('📝 更新 AI 摘要內容...');

        // 更新分頁模式的摘要內容
        const summaryContent = document.getElementById('summaryContent');
        if (summaryContent) {
            summaryContent.textContent = summary;
            console.log('✅ 已更新分頁模式摘要內容');
        }

        // 更新合併模式的摘要內容
        const combinedSummaryContent = document.getElementById('combinedSummaryContent');
        if (combinedSummaryContent) {
            combinedSummaryContent.textContent = summary;
            console.log('✅ 已更新合併模式摘要內容');
        }
    }

    /**
     * 重置回饋表單
     */
    resetFeedbackForm() {
        console.log('🔄 重置回饋表單...');

        // 清空分頁模式的回饋輸入
        const feedbackText = document.getElementById('feedbackText');
        if (feedbackText) {
            feedbackText.value = '';
            feedbackText.disabled = false;
            console.log('✅ 已重置分頁模式回饋輸入');
        }

        // 清空合併模式的回饋輸入
        const combinedFeedbackText = document.getElementById('combinedFeedbackText');
        if (combinedFeedbackText) {
            combinedFeedbackText.value = '';
            combinedFeedbackText.disabled = false;
            console.log('✅ 已重置合併模式回饋輸入');
        }

        // 重置圖片上傳組件
        this.images = [];
        this.updateImagePreview();

        // 重新啟用提交按鈕
        const submitButtons = document.querySelectorAll('.submit-button, #submitButton, #combinedSubmitButton');
        submitButtons.forEach(button => {
            if (button) {
                button.disabled = false;
                button.textContent = button.getAttribute('data-original-text') || '提交回饋';
            }
        });

        console.log('✅ 回饋表單重置完成');
    }

    /**
     * 更新狀態指示器
     */
    updateStatusIndicators() {
        console.log('🔄 更新狀態指示器...');

        // 使用國際化系統獲取翻譯文字
        const waitingTitle = window.i18nManager ? window.i18nManager.t('status.waiting.title') : 'Waiting for Feedback';
        const waitingMessage = window.i18nManager ? window.i18nManager.t('status.waiting.message') : 'Please provide your feedback on the AI work results';

        // 更新分頁模式的狀態指示器
        const feedbackStatusIndicator = document.getElementById('feedbackStatusIndicator');
        if (feedbackStatusIndicator) {
            this.setStatusIndicator(feedbackStatusIndicator, 'waiting', '⏳', waitingTitle, waitingMessage);
        }

        // 更新合併模式的狀態指示器
        const combinedFeedbackStatusIndicator = document.getElementById('combinedFeedbackStatusIndicator');
        if (combinedFeedbackStatusIndicator) {
            this.setStatusIndicator(combinedFeedbackStatusIndicator, 'waiting', '⏳', waitingTitle, waitingMessage);
        }

        console.log('✅ 狀態指示器更新完成');
    }

    /**
     * 設置狀態指示器的內容（兼容舊版本調用）
     */
    setStatusIndicator(element, status, icon, title, message) {
        // 直接調用新的更新方法
        this.updateStatusIndicatorElement(element, status, icon, title, message);
    }

    handleStatusUpdate(statusInfo) {
        console.log('處理狀態更新:', statusInfo);

        // 更新頁面標題顯示會話信息
        if (statusInfo.project_directory) {
            const projectName = statusInfo.project_directory.split(/[/\\]/).pop();
            document.title = `MCP Feedback - ${projectName}`;
        }

        // 提取會話 ID（如果有的話）
        const sessionId = statusInfo.session_id || this.currentSessionId;

        // 根據狀態更新 UI 和狀態管理
        switch (statusInfo.status) {
            case 'feedback_submitted':
                this.setFeedbackState('feedback_submitted', sessionId);
                this.updateSummaryStatus('已送出反饋，等待下次 MCP 調用...');
                const submittedConnectionText = window.i18nManager ? window.i18nManager.t('connection.submitted') : '已連接 - 反饋已提交';
                this.updateConnectionStatus('connected', submittedConnectionText);
                break;

            case 'active':
            case 'waiting':
                // 檢查是否是新會話
                if (sessionId && sessionId !== this.currentSessionId) {
                    // 新會話開始，重置狀態
                    this.setFeedbackState('waiting_for_feedback', sessionId);
                } else if (this.feedbackState !== 'feedback_submitted') {
                    // 如果不是已提交狀態，設置為等待狀態
                    this.setFeedbackState('waiting_for_feedback', sessionId);
                }

                if (statusInfo.status === 'waiting') {
                    this.updateSummaryStatus('等待用戶回饋...');
                }
                const waitingConnectionText = window.i18nManager ? window.i18nManager.t('connection.waiting') : '已連接 - 等待回饋';
                this.updateConnectionStatus('connected', waitingConnectionText);
                break;

            default:
                this.updateConnectionStatus('connected', `已連接 - ${statusInfo.status || '未知狀態'}`);
        }
    }

    disableSubmitButton() {
        const submitBtn = document.getElementById('submitBtn');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = window.i18nManager ? window.i18nManager.t('buttons.submitted') : '✅ 已提交';
            submitBtn.style.background = 'var(--success-color)';
        }
    }

    enableSubmitButton() {
        const submitBtn = document.getElementById('submitBtn');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = window.i18nManager ? window.i18nManager.t('buttons.submit') : '📤 提交回饋';
            submitBtn.style.background = 'var(--accent-color)';
        }
    }

    updateSummaryStatus(message) {
        const summaryElements = document.querySelectorAll('.ai-summary-content');
        summaryElements.forEach(element => {
            element.innerHTML = `
                <div style="padding: 16px; background: var(--success-color); color: white; border-radius: 6px; text-align: center;">
                    ✅ ${message}
                </div>
            `;
        });
    }

    showSuccessMessage(message = '✅ 回饋提交成功！頁面將保持開啟等待下次調用。') {
        this.showMessage(message, 'success');
    }

    showMessage(message, type = 'info') {
        // 創建消息元素
        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${type}`;
        messageDiv.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            z-index: 1001;
            padding: 12px 20px;
            background: var(--success-color);
            color: white;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            max-width: 300px;
            word-wrap: break-word;
        `;
        messageDiv.textContent = message;
        
        document.body.appendChild(messageDiv);
        
        // 3秒後自動移除
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.parentNode.removeChild(messageDiv);
            }
        }, 3000);
    }

    updateConnectionStatus(status, text) {
        if (this.connectionIndicator) {
            this.connectionIndicator.className = `connection-indicator ${status}`;
        }
        if (this.connectionText) {
            this.connectionText.textContent = text;
        }
    }

    showWaitingInterface() {
        if (this.waitingContainer) {
            this.waitingContainer.style.display = 'flex';
        }
        if (this.mainContainer) {
            this.mainContainer.classList.remove('active');
        }
    }

    showMainInterface() {
        if (this.waitingContainer) {
            this.waitingContainer.style.display = 'none';
        }
        if (this.mainContainer) {
            this.mainContainer.classList.add('active');
        }
    }

    async loadFeedbackInterface(sessionInfo) {
        if (!this.mainContainer) return;
        
        this.sessionInfo = sessionInfo;
        
        // 載入完整的回饋界面
        this.mainContainer.innerHTML = await this.generateFeedbackHTML(sessionInfo);
        
        // 重新設置事件監聽器
        this.setupFeedbackEventListeners();
    }

    async generateFeedbackHTML(sessionInfo) {
        return `
            <div class="feedback-container">
                <!-- 頭部 -->
                <header class="header">
                    <div class="header-content">
                        <div class="header-left">
                            <h1 class="title">MCP Feedback Enhanced</h1>
                        </div>
                        <div class="project-info">
                            專案目錄: ${sessionInfo.project_directory}
                        </div>
                    </div>
                </header>

                <!-- AI 摘要區域 -->
                <div class="ai-summary-section">
                    <h2>AI 工作摘要</h2>
                    <div class="ai-summary-content">
                        <p>${sessionInfo.summary}</p>
                    </div>
                </div>

                <!-- 回饋輸入區域 -->
                <div class="feedback-section">
                    <h3>提供回饋</h3>
                    <div class="input-group">
                        <label class="input-label">文字回饋</label>
                        <textarea 
                            id="feedbackText" 
                            class="text-input" 
                            placeholder="請在這裡輸入您的回饋..."
                            style="min-height: 150px;"
                        ></textarea>
                    </div>
                    
                    <div class="button-group">
                        <button id="submitBtn" class="btn btn-primary">
                            📤 提交回饋
                        </button>
                        <button id="clearBtn" class="btn btn-secondary">
                            🗑️ 清空
                        </button>
                    </div>
                </div>

                <!-- 命令執行區域 -->
                <div class="command-section">
                    <h3>命令執行</h3>
                    <div class="input-group">
                        <input 
                            type="text" 
                            id="commandInput" 
                            class="command-input-line" 
                            placeholder="輸入命令..."
                            style="width: 100%; padding: 8px; margin-bottom: 8px;"
                        >
                        <button id="runCommandBtn" class="btn btn-secondary">
                            ▶️ 執行
                        </button>
                    </div>
                    <div id="commandOutput" class="command-output" style="height: 200px; overflow-y: auto;"></div>
                </div>
            </div>
        `;
    }

    setupEventListeners() {
        // 提交和取消按鈕
        if (this.submitBtn) {
            this.submitBtn.addEventListener('click', () => this.submitFeedback());
        }

        if (this.cancelBtn) {
            this.cancelBtn.addEventListener('click', () => this.cancelFeedback());
        }

        // 命令執行
        if (this.runCommandBtn) {
            this.runCommandBtn.addEventListener('click', () => this.runCommand());
        }

        if (this.commandInput) {
            this.commandInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.runCommand();
                }
            });
        }

        // 快捷鍵
        document.addEventListener('keydown', (e) => {
            // Ctrl+Enter 提交回饋
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                this.submitFeedback();
            }

            // Esc 取消
            if (e.key === 'Escape') {
                this.cancelFeedback();
            }
        });

        // 設定相關事件
        this.setupSettingsEvents();
    }

    setupSettingsEvents() {
        // 佈局模式切換
        const layoutModeInputs = document.querySelectorAll('input[name="layoutMode"]');
        layoutModeInputs.forEach(input => {
            input.addEventListener('change', (e) => {
                this.layoutMode = e.target.value;
                this.applyLayoutMode();
                this.saveSettings();
            });
        });

        // 自動關閉切換
        const autoCloseToggle = document.getElementById('autoCloseToggle');
        if (autoCloseToggle) {
            autoCloseToggle.addEventListener('click', () => {
                this.autoClose = !this.autoClose;
                autoCloseToggle.classList.toggle('active', this.autoClose);
                this.saveSettings();
            });
        }

        // 語言切換
        const languageOptions = document.querySelectorAll('.language-option');
        languageOptions.forEach(option => {
            option.addEventListener('click', () => {
                const lang = option.getAttribute('data-lang');
                this.switchLanguage(lang);
            });
        });

        // 重置設定
        const resetBtn = document.getElementById('resetSettingsBtn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                if (confirm('確定要重置所有設定嗎？')) {
                    this.resetSettings();
                }
            });
        }
    }

    // 移除重複的事件監聽器設置方法
    // 所有事件監聽器已在 setupEventListeners() 中統一設置

    submitFeedback() {
        console.log('📤 嘗試提交回饋...');

        // 檢查是否可以提交回饋
        if (!this.canSubmitFeedback()) {
            console.log('⚠️ 無法提交回饋 - 當前狀態:', this.feedbackState, '連接狀態:', this.isConnected);

            if (this.feedbackState === 'feedback_submitted') {
                this.showMessage('回饋已提交，請等待下次 MCP 調用', 'warning');
            } else if (this.feedbackState === 'processing') {
                this.showMessage('正在處理中，請稍候', 'warning');
            } else if (!this.isConnected) {
                this.showMessage('WebSocket 未連接，正在嘗試重連...', 'error');
                // 嘗試重新建立連接
                this.setupWebSocket();
            } else {
                this.showMessage(`當前狀態不允許提交: ${this.feedbackState}`, 'warning');
            }
            return;
        }

        // 根據當前佈局模式獲取回饋內容
        let feedback = '';
        if (this.layoutMode.startsWith('combined')) {
            const combinedFeedbackInput = document.getElementById('combinedFeedbackText');
            feedback = combinedFeedbackInput?.value.trim() || '';
        } else {
            const feedbackInput = document.getElementById('feedbackText');
            feedback = feedbackInput?.value.trim() || '';
        }

        if (!feedback && this.images.length === 0) {
            this.showMessage('請提供回饋文字或上傳圖片', 'warning');
            return;
        }

        // 設置處理狀態
        this.setFeedbackState('processing');

        try {
            // 發送回饋
            this.websocket.send(JSON.stringify({
                type: 'submit_feedback',
                feedback: feedback,
                images: this.images,
                settings: {
                    image_size_limit: this.imageSizeLimit,
                    enable_base64_detail: this.enableBase64Detail
                }
            }));

            // 清空表單
            this.clearFeedback();

            console.log('📤 回饋已發送，等待服務器確認...');

        } catch (error) {
            console.error('❌ 發送回饋失敗:', error);
            this.showMessage('發送失敗，請重試', 'error');
            // 恢復到等待狀態
            this.setFeedbackState('waiting_for_feedback');
        }
    }

    clearFeedback() {
        console.log('🧹 清空回饋內容...');

        // 清空所有模式的回饋文字
        const feedbackInputs = [
            document.getElementById('feedbackText'),
            document.getElementById('combinedFeedbackText')
        ].filter(input => input);

        feedbackInputs.forEach(input => {
            input.value = '';
        });

        // 清空圖片數據
        this.images = [];

        // 更新所有圖片預覽容器（updateImagePreview 現在會處理所有容器）
        this.updateImagePreview();

        // 重新啟用提交按鈕
        const submitButtons = [
            document.getElementById('submitBtn'),
            document.getElementById('combinedSubmitBtn')
        ].filter(btn => btn);

        submitButtons.forEach(button => {
            button.disabled = false;
            button.textContent = window.i18nManager ? window.i18nManager.t('buttons.submit') : '提交回饋';
        });

        console.log('✅ 回饋內容清空完成');
    }

    runCommand() {
        const commandInput = document.getElementById('commandInput');
        const command = commandInput?.value.trim();

        if (!command) {
            this.appendCommandOutput('⚠️ 請輸入命令\n');
            return;
        }

        if (!this.isConnected) {
            this.appendCommandOutput('❌ WebSocket 未連接，無法執行命令\n');
            return;
        }

        // 顯示執行的命令
        this.appendCommandOutput(`$ ${command}\n`);

        // 發送命令
        try {
            this.websocket.send(JSON.stringify({
                type: 'run_command',
                command: command
            }));

            // 清空輸入框
            commandInput.value = '';
            this.appendCommandOutput('[正在執行...]\n');

        } catch (error) {
            this.appendCommandOutput(`❌ 發送命令失敗: ${error.message}\n`);
        }
    }

    appendCommandOutput(output) {
        const commandOutput = document.getElementById('commandOutput');
        if (commandOutput) {
            commandOutput.textContent += output;
            commandOutput.scrollTop = commandOutput.scrollHeight;
        }
    }

    enableCommandInput() {
        const commandInput = document.getElementById('commandInput');
        const runCommandBtn = document.getElementById('runCommandBtn');

        if (commandInput) commandInput.disabled = false;
        if (runCommandBtn) {
            runCommandBtn.disabled = false;
            runCommandBtn.textContent = '▶️ 執行';
        }
    }

    // 設定相關方法
    async loadSettings() {
        try {
            console.log('開始載入設定...');

            // 優先從伺服器端載入設定
            let settings = null;
            try {
                const response = await fetch('/api/load-settings');
                if (response.ok) {
                    const serverSettings = await response.json();
                    if (Object.keys(serverSettings).length > 0) {
                        settings = serverSettings;
                        console.log('從伺服器端載入設定成功:', settings);

                        // 同步到 localStorage
                        localStorage.setItem('mcp-feedback-settings', JSON.stringify(settings));
                    }
                }
            } catch (serverError) {
                console.warn('從伺服器端載入設定失敗，嘗試從 localStorage 載入:', serverError);
            }

            // 如果伺服器端載入失敗，回退到 localStorage
            if (!settings) {
                const localSettings = localStorage.getItem('mcp-feedback-settings');
                if (localSettings) {
                    settings = JSON.parse(localSettings);
                    console.log('從 localStorage 載入設定:', settings);
                }
            }

            // 應用設定
            if (settings) {
                this.layoutMode = settings.layoutMode || 'separate';
                this.autoClose = settings.autoClose || false;
                this.currentLanguage = settings.language || 'zh-TW';
                this.imageSizeLimit = settings.imageSizeLimit || 0;
                this.enableBase64Detail = settings.enableBase64Detail || false;

                // 處理 activeTab 設定
                if (settings.activeTab) {
                    this.currentTab = settings.activeTab;
                }

                console.log('設定載入完成，應用設定...');

                // 同步語言設定到 i18nManager（確保 ui_settings.json 優先於 localStorage）
                if (settings.language && window.i18nManager) {
                    const currentI18nLanguage = window.i18nManager.getCurrentLanguage();
                    console.log(`檢查語言設定: ui_settings.json=${settings.language}, i18nManager=${currentI18nLanguage}`);
                    if (settings.language !== currentI18nLanguage) {
                        console.log(`🔄 同步語言設定: ${currentI18nLanguage} -> ${settings.language}`);
                        window.i18nManager.setLanguage(settings.language);
                        // 同步到 localStorage，確保一致性
                        localStorage.setItem('language', settings.language);
                        console.log(`✅ 語言同步完成: ${settings.language}`);
                    } else {
                        console.log(`✅ 語言設定已同步: ${settings.language}`);
                    }
                } else {
                    console.log(`⚠️ 語言同步跳過: settings.language=${settings.language}, i18nManager=${!!window.i18nManager}`);
                }

                this.applySettings();
            } else {
                console.log('沒有找到設定，使用預設值');
                this.applySettings();
            }
        } catch (error) {
            console.error('載入設定失敗:', error);
            // 使用預設設定
            this.applySettings();
        }
    }

    async saveSettings() {
        try {
            const settings = {
                layoutMode: this.layoutMode,
                autoClose: this.autoClose,
                language: this.currentLanguage,
                imageSizeLimit: this.imageSizeLimit,
                enableBase64Detail: this.enableBase64Detail,
                activeTab: this.currentTab
            };

            console.log('保存設定:', settings);

            // 保存到 localStorage
            localStorage.setItem('mcp-feedback-settings', JSON.stringify(settings));

            // 同步保存到伺服器端
            try {
                const response = await fetch('/api/save-settings', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(settings)
                });

                if (response.ok) {
                    console.log('設定已同步到伺服器端');
                } else {
                    console.warn('同步設定到伺服器端失敗:', response.status);
                }
            } catch (serverError) {
                console.warn('同步設定到伺服器端時發生錯誤:', serverError);
            }
        } catch (error) {
            console.error('保存設定失敗:', error);
        }
    }

    applySettings() {
        // 應用佈局模式
        this.applyLayoutMode();

        // 應用自動關閉設定
        const autoCloseToggle = document.getElementById('autoCloseToggle');
        if (autoCloseToggle) {
            autoCloseToggle.classList.toggle('active', this.autoClose);
        }

        // 應用語言設定
        if (this.currentLanguage && window.i18nManager) {
            const currentI18nLanguage = window.i18nManager.getCurrentLanguage();
            if (this.currentLanguage !== currentI18nLanguage) {
                console.log(`應用語言設定: ${currentI18nLanguage} -> ${this.currentLanguage}`);
                window.i18nManager.setLanguage(this.currentLanguage);
            }
        }

        // 應用圖片設定
        if (this.imageSizeLimitSelect) {
            this.imageSizeLimitSelect.value = this.imageSizeLimit.toString();
        }

        if (this.enableBase64DetailCheckbox) {
            this.enableBase64DetailCheckbox.checked = this.enableBase64Detail;
        }
    }

    applyLayoutMode() {
        const layoutModeInputs = document.querySelectorAll('input[name="layoutMode"]');
        layoutModeInputs.forEach(input => {
            input.checked = input.value === this.layoutMode;
        });

        // 檢查當前 body class 是否已經正確，避免不必要的 DOM 操作
        const expectedClassName = `layout-${this.layoutMode}`;
        if (document.body.className !== expectedClassName) {
            console.log(`應用佈局模式: ${this.layoutMode}`);
            document.body.className = expectedClassName;
        } else {
            console.log(`佈局模式已正確: ${this.layoutMode}，跳過 DOM 更新`);
        }

        // 控制頁籤顯示/隱藏
        this.updateTabVisibility();

        // 同步合併佈局和分頁中的內容
        this.syncCombinedLayoutContent();

        // 如果是合併模式，確保內容同步
        if (this.layoutMode.startsWith('combined')) {
            this.setupCombinedModeSync();
            // 如果當前頁籤不是合併模式，則切換到合併模式頁籤
            if (this.currentTab !== 'combined') {
                this.currentTab = 'combined';
            }
        } else {
            // 分離模式時，如果當前頁籤是合併模式，則切換到回饋頁籤
            if (this.currentTab === 'combined') {
                this.currentTab = 'feedback';
            }
        }
    }

    updateTabVisibility() {
        const combinedTab = document.querySelector('.tab-button[data-tab="combined"]');
        const feedbackTab = document.querySelector('.tab-button[data-tab="feedback"]');
        const summaryTab = document.querySelector('.tab-button[data-tab="summary"]');

        if (this.layoutMode.startsWith('combined')) {
            // 合併模式：顯示合併模式頁籤，隱藏回饋和AI摘要頁籤
            if (combinedTab) combinedTab.style.display = 'inline-block';
            if (feedbackTab) feedbackTab.style.display = 'none';
            if (summaryTab) summaryTab.style.display = 'none';
        } else {
            // 分離模式：隱藏合併模式頁籤，顯示回饋和AI摘要頁籤
            if (combinedTab) combinedTab.style.display = 'none';
            if (feedbackTab) feedbackTab.style.display = 'inline-block';
            if (summaryTab) summaryTab.style.display = 'inline-block';
        }
    }

    syncCombinedLayoutContent() {
        // 同步文字內容
        const feedbackText = document.getElementById('feedbackText');
        const combinedFeedbackText = document.getElementById('combinedFeedbackText');

        if (feedbackText && combinedFeedbackText) {
            // 雙向同步文字內容
            if (feedbackText.value && !combinedFeedbackText.value) {
                combinedFeedbackText.value = feedbackText.value;
            } else if (combinedFeedbackText.value && !feedbackText.value) {
                feedbackText.value = combinedFeedbackText.value;
            }
        }

        // 同步圖片設定
        this.syncImageSettings();

        // 同步圖片內容
        this.syncImageContent();
    }

    syncImageSettings() {
        // 同步圖片大小限制設定
        const imageSizeLimit = document.getElementById('imageSizeLimit');
        const combinedImageSizeLimit = document.getElementById('combinedImageSizeLimit');

        if (imageSizeLimit && combinedImageSizeLimit) {
            if (imageSizeLimit.value !== combinedImageSizeLimit.value) {
                combinedImageSizeLimit.value = imageSizeLimit.value;
            }
        }

        // 同步 Base64 設定
        const enableBase64Detail = document.getElementById('enableBase64Detail');
        const combinedEnableBase64Detail = document.getElementById('combinedEnableBase64Detail');

        if (enableBase64Detail && combinedEnableBase64Detail) {
            combinedEnableBase64Detail.checked = enableBase64Detail.checked;
        }
    }

    syncImageContent() {
        // 同步圖片預覽內容
        const imagePreviewContainer = document.getElementById('imagePreviewContainer');
        const combinedImagePreviewContainer = document.getElementById('combinedImagePreviewContainer');

        if (imagePreviewContainer && combinedImagePreviewContainer) {
            combinedImagePreviewContainer.innerHTML = imagePreviewContainer.innerHTML;
        }
    }

    setupCombinedModeSync() {
        // 設置文字輸入的雙向同步
        const feedbackText = document.getElementById('feedbackText');
        const combinedFeedbackText = document.getElementById('combinedFeedbackText');

        if (feedbackText && combinedFeedbackText) {
            // 移除舊的事件監聽器（如果存在）
            feedbackText.removeEventListener('input', this.syncToCombinetText);
            combinedFeedbackText.removeEventListener('input', this.syncToSeparateText);

            // 添加新的事件監聽器
            this.syncToCombinetText = (e) => {
                combinedFeedbackText.value = e.target.value;
            };
            this.syncToSeparateText = (e) => {
                feedbackText.value = e.target.value;
            };

            feedbackText.addEventListener('input', this.syncToCombinetText);
            combinedFeedbackText.addEventListener('input', this.syncToSeparateText);
        }

        // 設置圖片設定的同步
        this.setupImageSettingsSync();

        // 設置圖片上傳的同步
        this.setupImageUploadSync();
    }

    setupImageSettingsSync() {
        const imageSizeLimit = document.getElementById('imageSizeLimit');
        const combinedImageSizeLimit = document.getElementById('combinedImageSizeLimit');
        const enableBase64Detail = document.getElementById('enableBase64Detail');
        const combinedEnableBase64Detail = document.getElementById('combinedEnableBase64Detail');

        if (imageSizeLimit && combinedImageSizeLimit) {
            imageSizeLimit.addEventListener('change', (e) => {
                combinedImageSizeLimit.value = e.target.value;
                this.imageSizeLimit = parseInt(e.target.value);
                this.saveSettings();
            });

            combinedImageSizeLimit.addEventListener('change', (e) => {
                imageSizeLimit.value = e.target.value;
                this.imageSizeLimit = parseInt(e.target.value);
                this.saveSettings();
            });
        }

        if (enableBase64Detail && combinedEnableBase64Detail) {
            enableBase64Detail.addEventListener('change', (e) => {
                combinedEnableBase64Detail.checked = e.target.checked;
                this.enableBase64Detail = e.target.checked;
                this.saveSettings();
            });

            combinedEnableBase64Detail.addEventListener('change', (e) => {
                enableBase64Detail.checked = e.target.checked;
                this.enableBase64Detail = e.target.checked;
                this.saveSettings();
            });
        }
    }

    setupImageUploadSync() {
        // 設置合併模式的圖片上傳功能
        const combinedImageInput = document.getElementById('combinedImageInput');
        const combinedImageUploadArea = document.getElementById('combinedImageUploadArea');

        if (combinedImageInput && combinedImageUploadArea) {
            // 簡化的圖片上傳同步 - 只需要基本的事件監聽器
            combinedImageInput.addEventListener('change', (e) => {
                this.handleFileSelect(e.target.files);
            });

            combinedImageUploadArea.addEventListener('click', () => {
                combinedImageInput.click();
            });

            // 拖放事件
            combinedImageUploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                combinedImageUploadArea.classList.add('dragover');
            });

            combinedImageUploadArea.addEventListener('dragleave', (e) => {
                e.preventDefault();
                combinedImageUploadArea.classList.remove('dragover');
            });

            combinedImageUploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                combinedImageUploadArea.classList.remove('dragover');
                this.handleFileSelect(e.dataTransfer.files);
            });
        }
    }

    resetSettings() {
        localStorage.removeItem('mcp-feedback-settings');
        this.layoutMode = 'separate';
        this.autoClose = false;
        this.currentLanguage = 'zh-TW';
        this.imageSizeLimit = 0;
        this.enableBase64Detail = false;
        this.applySettings();
        this.saveSettings();
    }

    switchLanguage(lang) {
        this.currentLanguage = lang;

        // 更新語言選項顯示
        const languageOptions = document.querySelectorAll('.language-option');
        languageOptions.forEach(option => {
            option.classList.toggle('active', option.getAttribute('data-lang') === lang);
        });

        // 通知國際化系統
        if (window.i18nManager) {
            window.i18nManager.setLanguage(lang);
        }

        // 同步到 localStorage，確保一致性
        localStorage.setItem('language', lang);

        // 保存到 ui_settings.json
        this.saveSettings();

        console.log(`語言已切換到: ${lang}`);
    }

    handleCombinedMode() {
        // 處理組合模式的特殊邏輯
        console.log('切換到組合模式');

        // 同步等待回饋狀態到合併模式
        this.syncFeedbackStatusToCombined();

        // 確保合併模式的佈局樣式正確應用
        const combinedTab = document.getElementById('tab-combined');
        if (combinedTab) {
            combinedTab.classList.remove('combined-vertical', 'combined-horizontal');
            if (this.layoutMode === 'combined-vertical') {
                combinedTab.classList.add('combined-vertical');
            } else if (this.layoutMode === 'combined-horizontal') {
                combinedTab.classList.add('combined-horizontal');
            }
        }
    }

    syncFeedbackStatusToCombined() {
        // 新版本：直接調用 updateStatusIndicator() 來同步狀態
        // 因為 updateStatusIndicator() 現在會同時更新兩個狀態指示器
        console.log('🔄 同步狀態指示器到合併模式...');
        // 不需要手動複製，updateStatusIndicator() 會處理所有狀態指示器
    }

}

// 注意：應用程式由模板中的 initializeApp() 函數初始化
// 不在此處自動初始化，避免重複實例
