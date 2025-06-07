/**
 * WebSocket Composable
 * 提供 WebSocket 連接管理、自動重連、事件處理等功能
 */

import { ref, computed, onUnmounted, nextTick } from 'vue'
import { useSessionStore } from '@/stores/session'

export function useWebSocket() {
  // ===== 狀態 =====
  const sessionStore = useSessionStore()
  
  // WebSocket 實例
  const ws = ref(null)
  
  // 連接配置
  const config = ref({
    url: '',
    protocols: [],
    reconnectInterval: 1000,
    maxReconnectAttempts: 5,
    heartbeatInterval: 30000,
    connectionTimeout: 10000
  })
  
  // 重連狀態
  const reconnectTimer = ref(null)
  const heartbeatTimer = ref(null)
  const connectionTimer = ref(null)
  
  // 事件監聽器
  const eventListeners = ref(new Map())
  
  // 消息隊列（連接斷開時暫存）
  const messageQueue = ref([])
  const maxQueueSize = ref(100)

  // ===== 計算屬性 =====
  
  const isConnected = computed(() => {
    return ws.value?.readyState === WebSocket.OPEN
  })
  
  const isConnecting = computed(() => {
    return ws.value?.readyState === WebSocket.CONNECTING
  })
  
  const connectionState = computed(() => {
    if (!ws.value) return 'disconnected'
    
    switch (ws.value.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting'
      case WebSocket.OPEN:
        return 'connected'
      case WebSocket.CLOSING:
        return 'closing'
      case WebSocket.CLOSED:
        return 'disconnected'
      default:
        return 'unknown'
    }
  })

  // ===== 工具方法 =====
  
  /**
   * 清理定時器
   */
  function clearTimers() {
    if (reconnectTimer.value) {
      clearTimeout(reconnectTimer.value)
      reconnectTimer.value = null
    }
    
    if (heartbeatTimer.value) {
      clearInterval(heartbeatTimer.value)
      heartbeatTimer.value = null
    }
    
    if (connectionTimer.value) {
      clearTimeout(connectionTimer.value)
      connectionTimer.value = null
    }
  }
  
  /**
   * 生成 WebSocket URL
   */
  function generateWebSocketUrl(sessionId) {
    const baseUrl = config.value.url || sessionStore.config.wsUrl
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = baseUrl.replace(/^https?:\/\//, '').replace(/^wss?:\/\//, '')
    
    return `${protocol}//${host}/ws/session/${sessionId}`
  }

  // ===== 事件處理 =====
  
  /**
   * 添加事件監聽器
   */
  function addEventListener(event, callback) {
    if (!eventListeners.value.has(event)) {
      eventListeners.value.set(event, new Set())
    }
    eventListeners.value.get(event).add(callback)
    
    return () => removeEventListener(event, callback)
  }
  
  /**
   * 移除事件監聽器
   */
  function removeEventListener(event, callback) {
    const listeners = eventListeners.value.get(event)
    if (listeners) {
      listeners.delete(callback)
      if (listeners.size === 0) {
        eventListeners.value.delete(event)
      }
    }
  }
  
  /**
   * 觸發事件
   */
  function emitEvent(event, data) {
    const listeners = eventListeners.value.get(event)
    if (listeners) {
      listeners.forEach(callback => {
        try {
          callback(data)
        } catch (error) {
          console.error(`事件處理器錯誤 [${event}]:`, error)
        }
      })
    }
  }

  // ===== 消息處理 =====
  
  /**
   * 發送消息
   */
  function sendMessage(data) {
    const message = typeof data === 'string' ? data : JSON.stringify(data)
    
    if (isConnected.value) {
      try {
        ws.value.send(message)
        sessionStore.updateActivity()
        console.log('📤 WebSocket 消息已發送:', data)
        return true
      } catch (error) {
        console.error('❌ 發送消息失敗:', error)
        sessionStore.setError(error)
        return false
      }
    } else {
      // 連接斷開時，將消息加入隊列
      if (messageQueue.value.length < maxQueueSize.value) {
        messageQueue.value.push({
          data: message,
          timestamp: Date.now()
        })
        console.log('📦 消息已加入隊列，等待連接恢復')
      } else {
        console.warn('⚠️ 消息隊列已滿，丟棄消息')
      }
      return false
    }
  }
  
  /**
   * 處理接收到的消息
   */
  function handleMessage(event) {
    try {
      const data = JSON.parse(event.data)
      
      sessionStore.updateActivity()
      console.log('📥 WebSocket 消息已接收:', data)
      
      // 觸發通用消息事件
      emitEvent('message', data)
      
      // 根據消息類型觸發特定事件
      if (data.type) {
        emitEvent(data.type, data)
      }
      
    } catch (error) {
      console.error('❌ 解析消息失敗:', error)
      sessionStore.setError(error)
    }
  }
  
  /**
   * 發送隊列中的消息
   */
  function sendQueuedMessages() {
    if (messageQueue.value.length > 0 && isConnected.value) {
      const messages = [...messageQueue.value]
      messageQueue.value = []
      
      messages.forEach(({ data }) => {
        try {
          ws.value.send(data)
        } catch (error) {
          console.error('❌ 發送隊列消息失敗:', error)
        }
      })
      
      console.log(`📤 已發送 ${messages.length} 條隊列消息`)
    }
  }

  // ===== 心跳機制 =====
  
  /**
   * 開始心跳
   */
  function startHeartbeat() {
    if (heartbeatTimer.value) return
    
    heartbeatTimer.value = setInterval(() => {
      if (isConnected.value) {
        sendMessage({
          type: 'ping',
          timestamp: Date.now()
        })
      }
    }, config.value.heartbeatInterval)
  }
  
  /**
   * 停止心跳
   */
  function stopHeartbeat() {
    if (heartbeatTimer.value) {
      clearInterval(heartbeatTimer.value)
      heartbeatTimer.value = null
    }
  }

  // ===== 連接管理 =====
  
  /**
   * 建立 WebSocket 連接
   */
  function connect(sessionId, options = {}) {
    if (ws.value && (isConnected.value || isConnecting.value)) {
      console.log('⚠️ WebSocket 已連接或正在連接中')
      return Promise.resolve()
    }
    
    // 合併配置
    Object.assign(config.value, options)
    
    return new Promise((resolve, reject) => {
      try {
        const url = generateWebSocketUrl(sessionId)
        console.log('🔌 正在連接 WebSocket:', url)
        
        sessionStore.setConnectionStatus('connecting')
        
        // 創建 WebSocket 連接
        ws.value = new WebSocket(url, config.value.protocols)
        sessionStore.websocket = ws.value
        
        // 設置連接超時
        connectionTimer.value = setTimeout(() => {
          if (!isConnected.value) {
            const error = new Error('連接超時')
            sessionStore.setError(error)
            sessionStore.setConnectionStatus('error')
            reject(error)
          }
        }, config.value.connectionTimeout)
        
        // 連接成功
        ws.value.onopen = () => {
          clearTimers()
          sessionStore.setConnectionStatus('connected')
          sessionStore.reconnectAttempts = 0
          
          console.log('✅ WebSocket 連接成功')
          
          // 開始心跳
          startHeartbeat()
          
          // 發送隊列中的消息
          nextTick(() => {
            sendQueuedMessages()
          })
          
          emitEvent('connected', { sessionId })
          resolve()
        }
        
        // 接收消息
        ws.value.onmessage = handleMessage
        
        // 連接關閉
        ws.value.onclose = (event) => {
          clearTimers()
          stopHeartbeat()
          
          console.log('🔌 WebSocket 連接已關閉:', event.code, event.reason)
          
          sessionStore.setConnectionStatus('disconnected')
          emitEvent('disconnected', { code: event.code, reason: event.reason })
          
          // 如果不是正常關閉，嘗試重連
          if (event.code !== 1000 && sessionStore.canReconnect) {
            scheduleReconnect(sessionId)
          }
        }
        
        // 連接錯誤
        ws.value.onerror = (error) => {
          console.error('❌ WebSocket 連接錯誤:', error)
          
          sessionStore.setError(error)
          sessionStore.setConnectionStatus('error')
          emitEvent('error', error)
          
          reject(error)
        }
        
      } catch (error) {
        console.error('❌ 創建 WebSocket 連接失敗:', error)
        sessionStore.setError(error)
        sessionStore.setConnectionStatus('error')
        reject(error)
      }
    })
  }
  
  /**
   * 安排重連
   */
  function scheduleReconnect(sessionId) {
    if (reconnectTimer.value || !sessionStore.canReconnect) return
    
    sessionStore.reconnectAttempts++
    const delay = Math.min(
      sessionStore.reconnectDelay * Math.pow(2, sessionStore.reconnectAttempts - 1),
      30000 // 最大 30 秒
    )
    
    console.log(`🔄 將在 ${delay}ms 後嘗試重連 (第 ${sessionStore.reconnectAttempts} 次)`)
    sessionStore.setConnectionStatus('reconnecting')
    
    reconnectTimer.value = setTimeout(() => {
      reconnectTimer.value = null
      connect(sessionId).catch(error => {
        console.error('❌ 重連失敗:', error)
      })
    }, delay)
  }
  
  /**
   * 手動重連
   */
  function reconnect(sessionId) {
    clearTimers()
    sessionStore.reconnectAttempts = 0
    return connect(sessionId)
  }
  
  /**
   * 斷開連接
   */
  function disconnect() {
    clearTimers()
    stopHeartbeat()
    
    if (ws.value) {
      ws.value.close(1000, '正常關閉')
      ws.value = null
      sessionStore.websocket = null
    }
    
    sessionStore.setConnectionStatus('disconnected')
    console.log('🔌 WebSocket 連接已斷開')
  }

  // ===== 生命週期 =====
  
  // 組件卸載時清理
  onUnmounted(() => {
    disconnect()
  })

  // ===== 返回 API =====
  return {
    // 狀態
    ws,
    config,
    messageQueue,
    
    // 計算屬性
    isConnected,
    isConnecting,
    connectionState,
    
    // 方法
    connect,
    disconnect,
    reconnect,
    sendMessage,
    addEventListener,
    removeEventListener,
    
    // 工具方法
    clearTimers,
    startHeartbeat,
    stopHeartbeat
  }
}
