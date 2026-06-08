import { useEffect, useState, useCallback, useMemo } from 'react'
import api, { type FactorInfo } from '@/lib/api'
import { wsClient } from '@/lib/websocket'

export type StrategyStatus = 'RUNNING' | 'PAPER' | 'SEED'

export interface TradeRecord {
  id: string
  timestamp: string
  direction: 'LONG' | 'SHORT' | 'CLOSE'
  price: number
  volume: number
  pnl: number
  factor_id: string
}

export interface SignalInfo {
  id: string
  timestamp: string
  direction: 'LONG' | 'SHORT' | 'FLAT'
  strength: number
  factor_id: string
  factor_name: string
}

export interface PositionInfo {
  direction: 'LONG' | 'SHORT' | 'FLAT'
  volume: number
  openPrice: number
  currentPrice: number
  unrealizedPnl: number
  marginUsed: number
}

export interface RegimeRadar {
  trend: number
  volatility: number
  liquidity: number
  momentum: number
  mean_reversion: number
  seasonality: number
}

export interface BacktestVsLive {
  metric: string
  backtest: number
  live: number
}

export interface SymbolStrategy {
  candidate_id: string
  template: string
  status: StrategyStatus
  sharpe_5d?: number
  max_dd?: number
  factor_info?: FactorInfo
}

export function useSymbolDetail(symbol: string) {
  const [strategies, setStrategies] = useState<SymbolStrategy[]>([])
  const [signals, setSignals] = useState<SignalInfo[]>([])
  const [position, setPosition] = useState<PositionInfo | null>(null)
  const [trades, setTrades] = useState<TradeRecord[]>([])
  const [regimeRadar, setRegimeRadar] = useState<RegimeRadar | null>(null)
  const [backtestLive, setBacktestLive] = useState<BacktestVsLive[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<number>(Date.now())

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const detailRes = await api.get(`/symbols/${symbol}`)
      const detail = detailRes.data

      const mappedStrategies: SymbolStrategy[] = (detail.running_strategies ?? []).map(
        (s: Record<string, unknown>) => ({
          candidate_id: String(s.candidate_id),
          template: String(s.template),
          status: String(s.status) as StrategyStatus,
          sharpe_5d: typeof s.sharpe_5d === 'number' ? s.sharpe_5d : undefined,
          max_dd: typeof s.max_dd === 'number' ? s.max_dd : undefined,
        })
      )
      setStrategies(mappedStrategies)

      if (detail.position) {
        setPosition({
          direction: detail.position.direction,
          volume: detail.position.volume,
          openPrice: detail.position.open_price,
          currentPrice: detail.position.current_price,
          unrealizedPnl: detail.position.unrealized_pnl,
          marginUsed: detail.position.margin_used,
        })
      }

      if (detail.regime_radar) {
        setRegimeRadar(detail.regime_radar as RegimeRadar)
      }

      const tradesRes = await api.get(`/trades?symbol=${symbol}&limit=50`)
      setTrades(tradesRes.data ?? [])

      const factorsRes = await api.get(`/factors?symbol=${symbol}`)
      const factors: FactorInfo[] = factorsRes.data ?? []
      const factorMap = new Map(factors.map((f) => [f.id, f]))

      setStrategies((prev) =>
        prev.map((s) => ({
          ...s,
          factor_info: factorMap.get(s.candidate_id),
        }))
      )

      const mockSignals: SignalInfo[] = factors.slice(0, 5).map((f, i) => ({
        id: `sig-${i}`,
        timestamp: new Date(Date.now() - i * 3600000).toISOString(),
        direction: i % 3 === 0 ? 'LONG' : i % 3 === 1 ? 'SHORT' : 'FLAT',
        strength: 0.5 + Math.random() * 0.5,
        factor_id: f.id,
        factor_name: f.name,
      }))
      setSignals(mockSignals)

      const mockBacktestLive: BacktestVsLive[] = [
        { metric: '夏普比率', backtest: 1.85, live: 1.62 },
        { metric: '年化收益', backtest: 0.32, live: 0.28 },
        { metric: '最大回撤', backtest: 0.08, live: 0.09 },
        { metric: '胜率', backtest: 0.58, live: 0.55 },
        { metric: '盈亏比', backtest: 1.9, live: 1.7 },
      ]
      setBacktestLive(mockBacktestLive)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载品种详情失败')
    } finally {
      setLoading(false)
    }
  }, [symbol])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  useEffect(() => {
    const unsubSymbol = wsClient.subscribe<{
      symbol: string
      position?: PositionInfo
      signals?: SignalInfo[]
    }>('symbol_update', (data) => {
      if (data.symbol !== symbol) return
      if (data.position) setPosition(data.position)
      if (data.signals) setSignals((prev) => [...data.signals!, ...prev].slice(0, 50))
      setLastUpdate(Date.now())
    })

    const unsubTrade = wsClient.subscribe<{
      symbol: string
      trade: TradeRecord
    }>('trade_signal', (data) => {
      if (data.symbol !== symbol) return
      setTrades((prev) => [data.trade, ...prev].slice(0, 50))
      setLastUpdate(Date.now())
    })

    return () => {
      unsubSymbol()
      unsubTrade()
    }
  }, [symbol])

  const filteredStrategies = useCallback(
    (statusFilter: StrategyStatus | 'ALL') => {
      if (statusFilter === 'ALL') return strategies
      return strategies.filter((s) => s.status === statusFilter)
    },
    [strategies]
  )

  const runningStrategy = useMemo(
    () => strategies.find((s) => s.status === 'RUNNING'),
    [strategies]
  )

  const regimeRadarData = useMemo(() => {
    if (!regimeRadar) return []
    return [
      { subject: '趋势', A: regimeRadar.trend * 100, fullMark: 100 },
      { subject: '波动', A: regimeRadar.volatility * 100, fullMark: 100 },
      { subject: '流动性', A: regimeRadar.liquidity * 100, fullMark: 100 },
      { subject: '动量', A: regimeRadar.momentum * 100, fullMark: 100 },
      { subject: '均值回归', A: regimeRadar.mean_reversion * 100, fullMark: 100 },
      { subject: '季节性', A: regimeRadar.seasonality * 100, fullMark: 100 },
    ]
  }, [regimeRadar])

  return {
    strategies,
    signals,
    position,
    trades,
    regimeRadar,
    regimeRadarData,
    backtestLive,
    loading,
    error,
    lastUpdate,
    filteredStrategies,
    runningStrategy,
    refresh: fetchData,
  }
}
