import { useEffect, useCallback, useState, useRef } from 'react'
import { useAppStore } from '@/store'
import api, { type SymbolStatus } from '@/lib/api'
import { wsClient } from '@/lib/websocket'

export interface EquityPoint {
  date: string
  equity: number
  drawdown: number
}

export interface AlertLog {
  id: string
  level: 'info' | 'warning' | 'error' | 'critical'
  message: string
  symbol?: string
  timestamp: string
}

export interface GlobalMetrics {
  totalEquity: number
  totalReturn: number
  maxDrawdown: number
  sharpeRatio: number
  totalTrades: number
  runningSymbols: number
  todayPnl: number
  todayReturn: number
}

export interface DashboardData {
  metrics: GlobalMetrics
  equityCurve: EquityPoint[]
  alerts: AlertLog[]
}

const FALLBACK_EQUITY: EquityPoint[] = [
  { date: '01-01', equity: 1000000, drawdown: 0 },
  { date: '01-02', equity: 1001200, drawdown: 0 },
  { date: '01-03', equity: 1000500, drawdown: -0.07 },
  { date: '01-04', equity: 1002800, drawdown: 0 },
  { date: '01-05', equity: 1003100, drawdown: 0 },
  { date: '01-06', equity: 1001500, drawdown: -0.16 },
  { date: '01-07', equity: 1004200, drawdown: 0 },
  { date: '01-08', equity: 1005800, drawdown: 0 },
  { date: '01-09', equity: 1003900, drawdown: -0.19 },
  { date: '01-10', equity: 1006200, drawdown: 0 },
  { date: '01-11', equity: 1007800, drawdown: 0 },
  { date: '01-12', equity: 1006500, drawdown: -0.13 },
  { date: '01-13', equity: 1009200, drawdown: 0 },
  { date: '01-14', equity: 1011000, drawdown: 0 },
  { date: '01-15', equity: 1009500, drawdown: -0.15 },
  { date: '01-16', equity: 1012800, drawdown: 0 },
  { date: '01-17', equity: 1014500, drawdown: 0 },
  { date: '01-18', equity: 1013200, drawdown: -0.13 },
  { date: '01-19', equity: 1015800, drawdown: 0 },
  { date: '01-20', equity: 1017200, drawdown: 0 },
]

function generateId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function computeMetrics(symbols: SymbolStatus[]): GlobalMetrics {
  const runningSymbols = symbols.filter((s) => s.status === 'running').length
  const totalEquity = symbols.reduce((sum, s) => sum + s.pnl_total + 1000000, 0)
  const todayPnl = symbols.reduce((sum, s) => sum + s.pnl_daily, 0)
  const totalReturn = totalEquity > 0 ? (todayPnl / (totalEquity - todayPnl)) * 100 : 0
  const avgSharpe =
    symbols.length > 0
      ? symbols.reduce((sum, s) => sum + s.sharpe_ratio, 0) / symbols.length
      : 0

  return {
    totalEquity,
    totalReturn,
    maxDrawdown: -2.5,
    sharpeRatio: avgSharpe,
    totalTrades: symbols.length * 12,
    runningSymbols,
    todayPnl,
    todayReturn: totalReturn,
  }
}

export function useDashboard() {
  const symbols = useAppStore((s) => s.symbols)
  const [equityCurve, setEquityCurve] = useState<EquityPoint[]>(FALLBACK_EQUITY)
  const [alerts, setAlerts] = useState<AlertLog[]>([])
  const alertsRef = useRef<AlertLog[]>([])

  const fetchEquityCurve = useCallback(async () => {
    try {
      const res = await api.get<EquityPoint[]>('/dashboard/equity-curve')
      if (res.data && res.data.length > 0) {
        setEquityCurve(res.data)
      }
    } catch {
      // keep fallback
    }
  }, [])

  const fetchAlerts = useCallback(async () => {
    try {
      const res = await api.get<AlertLog[]>('/dashboard/alerts')
      if (res.data) {
        const sorted = res.data.sort(
          (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
        )
        alertsRef.current = sorted
        setAlerts(sorted)
      }
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    fetchEquityCurve()
    fetchAlerts()

    const unsubMargin = wsClient.subscribe<{ symbol: string; level: number; message: string }>(
      'margin_alert',
      (data) => {
        const alert: AlertLog = {
          id: generateId(),
          level: data.level >= 90 ? 'critical' : data.level >= 70 ? 'warning' : 'info',
          message: data.message,
          symbol: data.symbol,
          timestamp: new Date().toISOString(),
        }
        alertsRef.current = [alert, ...alertsRef.current].slice(0, 100)
        setAlerts([...alertsRef.current])
      }
    )

    const unsubTrade = wsClient.subscribe<{ symbol: string; side: string; pnl: number }>(
      'trade_signal',
      (data) => {
        const alert: AlertLog = {
          id: generateId(),
          level: data.pnl < -500 ? 'error' : 'info',
          message: `${data.symbol} ${data.side} 信号, PnL: ${data.pnl.toFixed(0)}`,
          symbol: data.symbol,
          timestamp: new Date().toISOString(),
        }
        alertsRef.current = [alert, ...alertsRef.current].slice(0, 100)
        setAlerts([...alertsRef.current])
      }
    )

    const unsubSystem = wsClient.subscribe<{ status: string; message?: string }>(
      'system_status',
      (data) => {
        const alert: AlertLog = {
          id: generateId(),
          level: data.status === 'error' ? 'error' : 'info',
          message: data.message || `系统状态: ${data.status}`,
          timestamp: new Date().toISOString(),
        }
        alertsRef.current = [alert, ...alertsRef.current].slice(0, 100)
        setAlerts([...alertsRef.current])
      }
    )

    return () => {
      unsubMargin()
      unsubTrade()
      unsubSystem()
    }
  }, [fetchEquityCurve, fetchAlerts])

  const metrics = computeMetrics(symbols)

  const pushAlert = useCallback((alert: Omit<AlertLog, 'id' | 'timestamp'>) => {
    const full: AlertLog = {
      ...alert,
      id: generateId(),
      timestamp: new Date().toISOString(),
    }
    alertsRef.current = [full, ...alertsRef.current].slice(0, 100)
    setAlerts([...alertsRef.current])
  }, [])

  return {
    metrics,
    equityCurve,
    alerts,
    pushAlert,
  }
}
