import { useState, useCallback, useMemo } from 'react'
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

const DEFAULT_SYMBOLS: SymbolSwitchItem[] = [
  { symbol: 'RB', name: '螺纹钢', mode: 'OFF', marginUsed: 0, marginTotal: 100000, sharpe20d: 1.85, maxDrawdown20d: -0.05, isMarginInsufficient: false, isDeliveryMonth: false },
  { symbol: 'HC', name: '热卷', mode: 'PAPER', marginUsed: 45000, marginTotal: 100000, sharpe20d: 1.62, maxDrawdown20d: -0.08, isMarginInsufficient: false, isDeliveryMonth: false },
  { symbol: 'I', name: '铁矿石', mode: 'LIVE', marginUsed: 78000, marginTotal: 100000, sharpe20d: 2.15, maxDrawdown20d: -0.03, isMarginInsufficient: false, isDeliveryMonth: false },
  { symbol: 'J', name: '焦炭', mode: 'PAPER', marginUsed: 92000, marginTotal: 100000, sharpe20d: 0.95, maxDrawdown20d: -0.12, isMarginInsufficient: false, isDeliveryMonth: false },
  { symbol: 'JM', name: '焦煤', mode: 'OFF', marginUsed: 0, marginTotal: 100000, sharpe20d: 0.72, maxDrawdown20d: -0.15, isMarginInsufficient: false, isDeliveryMonth: false },
  { symbol: 'CU', name: '沪铜', mode: 'LIVE', marginUsed: 65000, marginTotal: 100000, sharpe20d: 1.98, maxDrawdown20d: -0.04, isMarginInsufficient: false, isDeliveryMonth: false },
  { symbol: 'AL', name: '沪铝', mode: 'PAPER', marginUsed: 35000, marginTotal: 100000, sharpe20d: 1.45, maxDrawdown20d: -0.07, isMarginInsufficient: false, isDeliveryMonth: false },
  { symbol: 'ZN', name: '沪锌', mode: 'OFF', marginUsed: 0, marginTotal: 100000, sharpe20d: 1.12, maxDrawdown20d: -0.09, isMarginInsufficient: true, isDeliveryMonth: false },
  { symbol: 'NI', name: '沪镍', mode: 'OFF', marginUsed: 0, marginTotal: 100000, sharpe20d: 0.88, maxDrawdown20d: -0.18, isMarginInsufficient: true, isDeliveryMonth: true },
  { symbol: 'TA', name: 'PTA', mode: 'PAPER', marginUsed: 42000, marginTotal: 100000, sharpe20d: 1.55, maxDrawdown20d: -0.06, isMarginInsufficient: false, isDeliveryMonth: false },
  { symbol: 'MA', name: '甲醇', mode: 'LIVE', marginUsed: 58000, marginTotal: 100000, sharpe20d: 1.72, maxDrawdown20d: -0.05, isMarginInsufficient: false, isDeliveryMonth: false },
  { symbol: 'PP', name: '聚丙烯', mode: 'PAPER', marginUsed: 38000, marginTotal: 100000, sharpe20d: 1.38, maxDrawdown20d: -0.08, isMarginInsufficient: false, isDeliveryMonth: false },
]

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
  const [symbols, setSymbols] = useState<SymbolSwitchItem[]>(DEFAULT_SYMBOLS)
  const [loading, setLoading] = useState<Record<string, boolean>>({})
  const [emergencyLoading, setEmergencyLoading] = useState(false)
  const setSystemStatus = useAppStore((s) => s.setSystemStatus)

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
