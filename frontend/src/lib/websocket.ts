export type WSMessageType =
  | 'symbol_update'
  | 'factor_evolution'
  | 'trade_signal'
  | 'margin_alert'
  | 'system_status'
  | 'evolution_progress'

export interface WSMessage<T = unknown> {
  type: WSMessageType
  timestamp: number
  data: T
}

export interface SymbolUpdateData {
  symbol: string
  status: string
  sharpe_ratio: number
  margin_used: number
  pnl_daily: number
}

class WebSocketClient {
  private ws: WebSocket | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private listeners: Map<WSMessageType, Set<(data: unknown) => void>> = new Map()
  private url: string
  private reconnectAttempts = 0
  private maxReconnectAttempts = 10
  private reconnectDelay = 3000

  constructor(url = '/ws') {
    this.url = url
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return

    // Use relative path to leverage Vite proxy
    const wsUrl = this.url

    this.ws = new WebSocket(wsUrl)

    this.ws.onopen = () => {
      this.reconnectAttempts = 0
      console.log('[WS] Connected')
      window.dispatchEvent(new Event('ws_open'))
    }

    this.ws.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data)
        this.emit(message.type, message.data)
      } catch {
        console.error('[WS] Failed to parse message:', event.data)
      }
    }

    this.ws.onclose = () => {
      console.log('[WS] Disconnected')
      window.dispatchEvent(new Event('ws_close'))
      this.scheduleReconnect()
    }

    this.ws.onerror = (error) => {
      console.error('[WS] Error:', error)
    }
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.ws?.close()
    this.ws = null
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WS] Max reconnect attempts reached')
      return
    }
    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.min(this.reconnectAttempts, 5)
    this.reconnectTimer = setTimeout(() => {
      console.log(`[WS] Reconnecting... (${this.reconnectAttempts})`)
      this.connect()
    }, delay)
  }

  subscribe<T>(type: WSMessageType, callback: (data: T) => void) {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set())
    }
    const set = this.listeners.get(type)!
    set.add(callback as (data: unknown) => void)

    return () => {
      set.delete(callback as (data: unknown) => void)
    }
  }

  private emit(type: WSMessageType, data: unknown) {
    const set = this.listeners.get(type)
    if (!set) return
    set.forEach((cb) => {
      try {
        cb(data)
      } catch (err) {
        console.error('[WS] Listener error:', err)
      }
    })
  }

  send(type: WSMessageType, data: unknown) {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      console.warn('[WS] Not connected')
      return
    }
    this.ws.send(JSON.stringify({ type, data, timestamp: Date.now() }))
  }

  get isConnected() {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

export const wsClient = new WebSocketClient()
export default wsClient
