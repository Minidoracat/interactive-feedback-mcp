/**
 * 事件驅動 API 客戶端
 * ==================
 * 
 * 封裝事件驅動 API 調用，提供統一的錯誤處理和重試機制
 */

class EventDrivenAPIClient {
    constructor(baseURL = '') {
        this.baseURL = baseURL;
        this.retryAttempts = 3;
        this.timeout = 5000;
        this.requestId = 0;
        
        console.log('🔗 事件驅動 API 客戶端初始化');
    }

    /**
     * 生成唯一請求 ID
     */
    generateRequestId() {
        return `req_${Date.now()}_${++this.requestId}`;
    }

    /**
     * GET 請求
     */
    async get(endpoint, options = {}) {
        return this.request('GET', `/api/v2${endpoint}`, null, options);
    }

    /**
     * POST 請求
     */
    async post(endpoint, data, options = {}) {
        return this.request('POST', `/api/v2${endpoint}`, data, options);
    }

    /**
     * PUT 請求
     */
    async put(endpoint, data, options = {}) {
        return this.request('PUT', `/api/v2${endpoint}`, data, options);
    }

    /**
     * DELETE 請求
     */
    async delete(endpoint, options = {}) {
        return this.request('DELETE', `/api/v2${endpoint}`, null, options);
    }

    /**
     * 統一請求處理
     */
    async request(method, url, data = null, options = {}) {
        const requestId = this.generateRequestId();
        const startTime = Date.now();
        
        console.log(`🌐 [${requestId}] ${method} ${url}`);

        const requestOptions = {
            method,
            headers: {
                'Content-Type': 'application/json',
                'X-Request-ID': requestId,
                ...options.headers
            }
        };

        // 創建超時控制器（兼容性更好的方式）
        const timeoutMs = options.timeout || this.timeout;
        const controller = new AbortController();
        let timeoutId = setTimeout(() => controller.abort(), timeoutMs);
        requestOptions.signal = controller.signal;

        if (data) {
            requestOptions.body = JSON.stringify(data);
        }

        let lastError = null;
        const maxAttempts = options.retryAttempts || this.retryAttempts;

        for (let attempt = 1; attempt <= maxAttempts; attempt++) {
            try {
                console.log(`🔄 [${requestId}] 嘗試 ${attempt}/${maxAttempts}`);
                
                const response = await fetch(url, requestOptions);
                const duration = Date.now() - startTime;
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const result = await response.json();
                console.log(`✅ [${requestId}] 成功 (${duration}ms)`);

                // 清理超時
                clearTimeout(timeoutId);

                return {
                    success: true,
                    data: result,
                    status: response.status,
                    requestId,
                    duration
                };

            } catch (error) {
                lastError = error;
                const duration = Date.now() - startTime;
                
                console.warn(`⚠️ [${requestId}] 嘗試 ${attempt} 失敗 (${duration}ms):`, error.message);
                
                // 如果不是最後一次嘗試，等待後重試
                if (attempt < maxAttempts) {
                    const delay = Math.min(1000 * Math.pow(2, attempt - 1), 5000); // 指數退避
                    console.log(`⏳ [${requestId}] 等待 ${delay}ms 後重試...`);
                    await new Promise(resolve => setTimeout(resolve, delay));
                }
            }
        }

        // 所有嘗試都失敗
        const duration = Date.now() - startTime;
        console.error(`❌ [${requestId}] 所有嘗試失敗 (${duration}ms):`, lastError);

        // 清理超時
        clearTimeout(timeoutId);

        return {
            success: false,
            error: lastError.message,
            requestId,
            duration
        };
    }
}

/**
 * 請求管理器
 * =========
 * 
 * 管理並發請求和請求隊列
 */
class RequestManager {
    constructor(maxConcurrent = 5) {
        this.maxConcurrent = maxConcurrent;
        this.activeRequests = new Map();
        this.requestQueue = [];
        
        console.log(`📋 請求管理器初始化 (最大並發: ${maxConcurrent})`);
    }

    /**
     * 添加請求到隊列
     */
    async enqueue(requestFn, priority = 0) {
        return new Promise((resolve, reject) => {
            this.requestQueue.push({
                requestFn,
                priority,
                resolve,
                reject,
                timestamp: Date.now()
            });
            
            // 按優先級排序
            this.requestQueue.sort((a, b) => b.priority - a.priority);
            
            this.processQueue();
        });
    }

    /**
     * 處理請求隊列
     */
    async processQueue() {
        while (this.requestQueue.length > 0 && this.activeRequests.size < this.maxConcurrent) {
            const request = this.requestQueue.shift();
            const requestId = `queue_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
            
            this.activeRequests.set(requestId, request);
            
            try {
                const result = await request.requestFn();
                request.resolve(result);
            } catch (error) {
                request.reject(error);
            } finally {
                this.activeRequests.delete(requestId);
                // 繼續處理隊列
                this.processQueue();
            }
        }
    }

    /**
     * 獲取隊列狀態
     */
    getStatus() {
        return {
            activeRequests: this.activeRequests.size,
            queuedRequests: this.requestQueue.length,
            maxConcurrent: this.maxConcurrent
        };
    }
}

/**
 * 健康監控器
 * =========
 * 
 * 監控 API 健康狀態和性能指標
 */
class HealthMonitor {
    constructor(apiClient) {
        this.apiClient = apiClient;
        this.healthStatus = 'unknown';
        this.lastCheck = null;
        this.checkInterval = 30000; // 30秒
        this.metrics = {
            totalRequests: 0,
            successfulRequests: 0,
            failedRequests: 0,
            averageResponseTime: 0,
            lastResponseTime: 0
        };
        
        console.log('💓 健康監控器初始化');
    }

    /**
     * 開始健康檢查
     */
    startMonitoring() {
        console.log('🔍 開始健康監控');
        
        // 立即執行一次檢查
        this.performHealthCheck();
        
        // 設置定期檢查
        this.monitoringInterval = setInterval(() => {
            this.performHealthCheck();
        }, this.checkInterval);
    }

    /**
     * 停止健康檢查
     */
    stopMonitoring() {
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
            this.monitoringInterval = null;
            console.log('🛑 健康監控已停止');
        }
    }

    /**
     * 執行健康檢查
     */
    async performHealthCheck() {
        const startTime = Date.now();
        
        try {
            const result = await this.apiClient.get('/health');
            const responseTime = Date.now() - startTime;
            
            if (result.success) {
                this.healthStatus = 'healthy';
                this.updateMetrics(true, responseTime);
                console.log(`💚 健康檢查通過 (${responseTime}ms)`);
            } else {
                this.healthStatus = 'unhealthy';
                this.updateMetrics(false, responseTime);
                console.warn(`💛 健康檢查失敗:`, result.error);
            }
            
        } catch (error) {
            const responseTime = Date.now() - startTime;
            this.healthStatus = 'error';
            this.updateMetrics(false, responseTime);
            console.error(`❤️ 健康檢查錯誤 (${responseTime}ms):`, error);
        }
        
        this.lastCheck = new Date();
    }

    /**
     * 更新性能指標
     */
    updateMetrics(success, responseTime) {
        this.metrics.totalRequests++;
        this.metrics.lastResponseTime = responseTime;
        
        if (success) {
            this.metrics.successfulRequests++;
        } else {
            this.metrics.failedRequests++;
        }
        
        // 計算平均響應時間
        this.metrics.averageResponseTime = 
            (this.metrics.averageResponseTime * (this.metrics.totalRequests - 1) + responseTime) / 
            this.metrics.totalRequests;
    }

    /**
     * 獲取健康狀態
     */
    getHealthStatus() {
        return {
            status: this.healthStatus,
            lastCheck: this.lastCheck,
            metrics: { ...this.metrics },
            uptime: this.lastCheck ? Date.now() - this.lastCheck.getTime() : 0
        };
    }
}

// 導出類供其他模組使用
window.EventDrivenAPIClient = EventDrivenAPIClient;
window.RequestManager = RequestManager;
window.HealthMonitor = HealthMonitor;

console.log('✅ 事件驅動 API 客戶端模組載入完成');
