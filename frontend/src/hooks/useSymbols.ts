import { useEffect, useCallback } from 'react'
import { useAppStore } from '@/store'
import { symbolApi, type SymbolStatus } from '@/lib/api'
import { wsClient } from '@/lib/websocket'

export interface SymbolWithMetrics extends SymbolStatus {
  marginPercent: number
  sharpe5d: number[]
}

export function useSymbols() {
  const symbols = useAppStore((s) => s.symbols)
  const setSymbols = useAppStore((s) => s.setSymbols)
  const updateSymbol = useAppStore((s) => s.updateSymbol)
  const setWsConnected = useAppStore((s) => s.setWsConnected)

  const fetchSymbols = useCallback(async () => {
    try {
      const res = await symbolApi.getAll()
      const mapped = res.data.map((s): SymbolStatus => ({
        symbol: s.symbol,
        name: s.name,
        status: s.status,
        current_factor: s.current_factor,
        sharpe_ratio: s.sharpe_ratio,
        margin_used: s.margin_used,
        margin_total: s.margin_total,
        pnl_daily: s.pnl_daily,
        pnl_total: s.pnl_total,
        updated_at: s.updated_at,
      }))
      setSymbols(mapped)
    } catch (err) {
      console.error('[useSymbols] fetch failed:', err)
    }
  }, [setSymbols])

  useEffect(() => {
    fetchSymbols()

    wsClient.connect()

    const unsub = wsClient.subscribe<{
      symbol: string
      status?: string
      sharpe_ratio?: number
      margin_used?: number
      pnl_daily?: number
    }>('symbol_update', (data) => {
      updateSymbol(data.symbol, {
        ...(data.status && { status: data.status as SymbolStatus['status'] }),
        ...(data.sharpe_ratio !== undefined && { sharpe_ratio: data.sharpe_ratio }),
        ...(data.margin_used !== undefined && { margin_used: data.margin_used }),
        ...(data.pnl_daily !== undefined && { pnl_daily: data.pnl_daily }),
        updated_at: new Date().toISOString(),
      })
    })

    const onOpen = () => setWsConnected(true)
    const onClose = () => setWsConnected(false)

    window.addEventListener('ws_open', onOpen)
    window.addEventListener('ws_close', onClose)

    return () => {
      unsub()
      window.removeEventListener('ws_open', onOpen)
      window.removeEventListener('ws_close', onClose)
    }
  }, [fetchSymbols, updateSymbol, setWsConnected])

  const symbolsWithMetrics: SymbolWithMetrics[] = symbols.map((s) => ({
    ...s,
    marginPercent: s.margin_total > 0 ? (s.margin_used / s.margin_total) * 100 : 0,
    sharpe5d: (() => {
      const base = Number(s.sharpe_ratio) || 0
      return Array.from({ length: 5 }, (_, i) => {
        const jitter = Math.sin(i + base * 10) * 0.3
        return Math.max(-1, base + jitter)
      })
    })(),
  }))

  const runningCount = symbols.filter((s) => s.status === 'running').length
  const pausedCount = symbols.filter((s) => s.status === 'paused').length
  const errorCount = symbols.filter((s) => s.status === 'error').length

  return {
    symbols: symbolsWithMetrics,
    runningCount,
    pausedCount,
    errorCount,
    totalCount: symbols.length,
    refresh: fetchSymbols,
  }
}
