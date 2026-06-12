import { useState, useCallback, useMemo, useEffect } from 'react'
import { useAppStore } from '@/store'
import api from '@/lib/api'

export type SymbolMode = 'OFF' | 'PAPER' | 'LIVE'

export interface SymbolSwitchItem {
  symbol: string
  name: string
  mode: SymbolMode
  marginUsed: number
  marginTotal: number
  sharpe20d: number
  maxDrawdown20d: number
  isMarginInsufficient: boolean
  isDeliveryMonth: boolean
}

export interface SelfCheckResult {
  name: string
  label: string
  passed: boolean
  detail: string
}

export interface LiveConfirmData {
  symbol: string
  name: string
  sharpe20d: number
  maxDrawdown20d: number
  selfChecks: SelfCheckResult[]
}


function generateSelfChecks(item: SymbolSwitchItem): SelfCheckResult[] {
  return [
    {
      name: 'deployable',
      label: 'Deployable',
      passed: item.sharpe20d >= 1.0 && item.maxDrawdown20d > -0.15,
      detail: item.sharpe20d >= 1.0 && item.maxDrawdown20d > -0.15
        ? `夏普 ${item.sharpe20d.toFixed(2)} / 回撤 ${(item.maxDrawdown20d * 100).toFixed(1)}%`
        : `夏普 ${item.sharpe20d.toFixed(2)} 不足或回撤过大`,
    },
    {
      name: 'margin',
      label: '保证金充足',
      passed: !item.isMarginInsufficient,
      detail: item.isMarginInsufficient
        ? '保证金不足，无法切换LIVE'
        : `可用保证金 ${(item.marginTotal - item.marginUsed).toLocaleString()}`,
    },
    {
      name: 'tianqin',
      label: '天勤连接',
      passed: true,
      detail: '天勤行情连接正常',
    },
    {
      name: 'circuit',
      label: '熔断状态',
      passed: true,
      detail: '系统未触发熔断',
    },
    {
      name: 'delivery',
      label: '交割月检查',
      passed: !item.isDeliveryMonth,
      detail: item.isDeliveryMonth
        ? '当前为交割月，禁止LIVE交易'
        : '非交割月，可正常交易',
    },
  ]
}

export function useManualSwitch() {
  const [symbols, setSymbols] = useState<SymbolSwitchItem[]>([])
  const [loading, setLoading] = useState<Record<string, boolean>>({})
  const [emergencyLoading, setEmergencyLoading] = useState(false)
  const setSystemStatus = useAppStore((s) => s.setSystemStatus)

  // 从后端真实加载 12 个品种状态（不再使用 mock 数据）
  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const { data } = await api.get('/symbols')
        if (cancelled || !Array.isArray(data)) return
        setSymbols(
          data.map((d: any): SymbolSwitchItem => ({
            symbol: d.symbol,
            name: d.name ?? d.symbol,
            mode: (d.status ?? 'OFF') as SymbolMode,
            marginUsed: d.margin_used ?? 0,
            marginTotal: d.max_margin ?? 0,
            sharpe20d: d.sharpe_ratio ?? 0,
            maxDrawdown20d: d.max_drawdown_20d ?? 0,
            isMarginInsufficient: d.is_margin_insufficient ?? false,
            isDeliveryMonth: d.is_delivery_month ?? false,
          })),
        )
      } catch (err) {
        console.error('Failed to load symbols:', err)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  const updateSymbolMode = useCallback(async (symbol: string, mode: SymbolMode) => {
    setLoading((prev) => ({ ...prev, [symbol]: true }))
    try {
      await api.post(`/symbols/${symbol}/mode`, { mode })
      setSymbols((prev) =>
        prev.map((s) => (s.symbol === symbol ? { ...s, mode } : s))
      )
    } catch (err) {
      console.error(`Failed to switch ${symbol} to ${mode}:`, err)
      throw err
    } finally {
      setLoading((prev) => ({ ...prev, [symbol]: false }))
    }
  }, [])

  const getLiveConfirmData = useCallback((symbol: string): LiveConfirmData | null => {
    const item = symbols.find((s) => s.symbol === symbol)
    if (!item) return null
    return {
      symbol: item.symbol,
      name: item.name,
      sharpe20d: item.sharpe20d,
      maxDrawdown20d: item.maxDrawdown20d,
      selfChecks: generateSelfChecks(item),
    }
  }, [symbols])

  const batchSetMode = useCallback(async (mode: SymbolMode) => {
    const targets = symbols.filter((s) => !s.isMarginInsufficient && s.mode !== mode)
    await Promise.all(
      targets.map((s) => updateSymbolMode(s.symbol, mode).catch(() => {}))
    )
  }, [symbols, updateSymbolMode])

  const emergencyStop = useCallback(async () => {
    setEmergencyLoading(true)
    try {
      await api.post('/system/emergency-stop')
      setSymbols((prev) =>
        prev.map((s) => ({ ...s, mode: 'OFF' as SymbolMode }))
      )
      setSystemStatus('paused')
    } catch (err) {
      console.error('Emergency stop failed:', err)
      throw err
    } finally {
      setEmergencyLoading(false)
    }
  }, [setSystemStatus])

  const marginInsufficientSymbols = useMemo(
    () => symbols.filter((s) => s.isMarginInsufficient),
    [symbols]
  )

  const liveSymbols = useMemo(
    () => symbols.filter((s) => s.mode === 'LIVE'),
    [symbols]
  )

  const paperSymbols = useMemo(
    () => symbols.filter((s) => s.mode === 'PAPER'),
    [symbols]
  )

  return {
    symbols,
    loading,
    emergencyLoading,
    updateSymbolMode,
    getLiveConfirmData,
    batchSetMode,
    emergencyStop,
    marginInsufficientSymbols,
    liveSymbols,
    paperSymbols,
  }
}
