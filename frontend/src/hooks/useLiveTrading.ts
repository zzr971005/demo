import { useState, useCallback, useEffect } from 'react'
import { liveTradingApi, LiveFactor, LiveStats, LivePerformanceSummary, BacktestLiveComparison } from '@/lib/api'

export interface UseLiveTradingReturn {
  // 实盘因子
  liveFactors: LiveFactor[]
  liveFactorsLoading: boolean
  liveFactorsError: string | null
  refreshLiveFactors: () => Promise<void>

  // 候选因子
  candidateFactors: LiveFactor[]
  candidateFactorsLoading: boolean
  candidateFactorsError: string | null
  refreshCandidateFactors: () => Promise<void>

  // 性能汇总
  summary: LivePerformanceSummary | null
  summaryLoading: boolean
  refreshSummary: () => Promise<void>

  // 操作
  deployFactor: (factorId: string) => Promise<void>
  removeFactor: (factorId: string) => Promise<void>
  markAsCandidate: (factorId: string) => Promise<void>

  // 操作状态
  deployingId: string | null
  removingId: string | null
  markingId: string | null
}

export function useLiveTrading(symbol?: string): UseLiveTradingReturn {
  // 实盘因子状态
  const [liveFactors, setLiveFactors] = useState<LiveFactor[]>([])
  const [liveFactorsLoading, setLiveFactorsLoading] = useState(false)
  const [liveFactorsError, setLiveFactorsError] = useState<string | null>(null)

  // 候选因子状态
  const [candidateFactors, setCandidateFactors] = useState<LiveFactor[]>([])
  const [candidateFactorsLoading, setCandidateFactorsLoading] = useState(false)
  const [candidateFactorsError, setCandidateFactorsError] = useState<string | null>(null)

  // 性能汇总状态
  const [summary, setSummary] = useState<LivePerformanceSummary | null>(null)
  const [summaryLoading, setSummaryLoading] = useState(false)

  // 操作状态
  const [deployingId, setDeployingId] = useState<string | null>(null)
  const [removingId, setRemovingId] = useState<string | null>(null)
  const [markingId, setMarkingId] = useState<string | null>(null)

  // 获取实盘因子
  const refreshLiveFactors = useCallback(async () => {
    try {
      setLiveFactorsLoading(true)
      setLiveFactorsError(null)
      const response = await liveTradingApi.getLiveFactors(symbol)
      setLiveFactors(response.data.factors || [])
    } catch (err) {
      setLiveFactorsError(err instanceof Error ? err.message : '获取实盘因子失败')
      setLiveFactors([])
    } finally {
      setLiveFactorsLoading(false)
    }
  }, [symbol])

  // 获取候选因子
  const refreshCandidateFactors = useCallback(async () => {
    try {
      setCandidateFactorsLoading(true)
      setCandidateFactorsError(null)
      const response = await liveTradingApi.getCandidateFactors(symbol)
      setCandidateFactors(response.data.factors || [])
    } catch (err) {
      setCandidateFactorsError(err instanceof Error ? err.message : '获取候选因子失败')
      setCandidateFactors([])
    } finally {
      setCandidateFactorsLoading(false)
    }
  }, [symbol])

  // 获取性能汇总
  const refreshSummary = useCallback(async () => {
    try {
      setSummaryLoading(true)
      const response = await liveTradingApi.getLiveSummary(symbol)
      setSummary(response.data)
    } catch (err) {
      // 静默失败
      setSummary(null)
    } finally {
      setSummaryLoading(false)
    }
  }, [symbol])

  // 部署因子
  const deployFactor = useCallback(async (factorId: string) => {
    try {
      setDeployingId(factorId)
      await liveTradingApi.deployFactor(factorId)
      // 刷新列表
      await Promise.all([
        refreshLiveFactors(),
        refreshCandidateFactors(),
        refreshSummary(),
      ])
    } catch (err) {
      throw err
    } finally {
      setDeployingId(null)
    }
  }, [refreshLiveFactors, refreshCandidateFactors, refreshSummary])

  // 移除因子
  const removeFactor = useCallback(async (factorId: string) => {
    try {
      setRemovingId(factorId)
      await liveTradingApi.removeFactor(factorId)
      // 刷新列表
      await Promise.all([
        refreshLiveFactors(),
        refreshSummary(),
      ])
    } catch (err) {
      throw err
    } finally {
      setRemovingId(null)
    }
  }, [refreshLiveFactors, refreshSummary])

  // 标记为候选
  const markAsCandidate = useCallback(async (factorId: string) => {
    try {
      setMarkingId(factorId)
      await liveTradingApi.markAsCandidate(factorId)
      // 刷新列表
      await Promise.all([
        refreshCandidateFactors(),
        refreshSummary(),
      ])
    } catch (err) {
      throw err
    } finally {
      setMarkingId(null)
    }
  }, [refreshCandidateFactors, refreshSummary])

  // 初始加载
  useEffect(() => {
    refreshLiveFactors()
    refreshCandidateFactors()
    refreshSummary()
  }, [refreshLiveFactors, refreshCandidateFactors, refreshSummary])

  return {
    liveFactors,
    liveFactorsLoading,
    liveFactorsError,
    refreshLiveFactors,
    candidateFactors,
    candidateFactorsLoading,
    candidateFactorsError,
    refreshCandidateFactors,
    summary,
    summaryLoading,
    refreshSummary,
    deployFactor,
    removeFactor,
    markAsCandidate,
    deployingId,
    removingId,
    markingId,
  }
}

// 单个因子详情的hook
export interface UseLiveFactorDetailReturn {
  factor: LiveFactor | null
  liveStats: LiveStats | null
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
  updateStats: (stats: Parameters<typeof liveTradingApi.updateLiveStats>[1]) => Promise<void>
}

export function useLiveFactorDetail(factorId: string): UseLiveFactorDetailReturn {
  const [factor, setFactor] = useState<LiveFactor | null>(null)
  const [liveStats, setLiveStats] = useState<LiveStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await liveTradingApi.getLiveFactorDetail(factorId)
      setFactor(response.data.factor)
      setLiveStats(response.data.live_stats || null)
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取因子详情失败')
      setFactor(null)
      setLiveStats(null)
    } finally {
      setLoading(false)
    }
  }, [factorId])

  const updateStats = useCallback(async (stats: Parameters<typeof liveTradingApi.updateLiveStats>[1]) => {
    try {
      await liveTradingApi.updateLiveStats(factorId, stats)
      await refresh()
    } catch (err) {
      throw err
    }
  }, [factorId, refresh])

  useEffect(() => {
    if (factorId) {
      refresh()
    }
  }, [factorId, refresh])

  return {
    factor,
    liveStats,
    loading,
    error,
    refresh,
    updateStats,
  }
}

// 回测与实盘对比的hook
export interface UseBacktestLiveComparisonReturn {
  comparisons: BacktestLiveComparison[]
  loading: boolean
  error: string | null
  refresh: (factorIds: string[]) => Promise<void>
}

export function useBacktestLiveComparison(): UseBacktestLiveComparisonReturn {
  const [comparisons, setComparisons] = useState<BacktestLiveComparison[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async (factorIds: string[]) => {
    if (factorIds.length === 0) {
      setComparisons([])
      return
    }

    try {
      setLoading(true)
      setError(null)
      const response = await liveTradingApi.compareBacktestLive(factorIds)
      setComparisons(response.data.comparisons || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取对比数据失败')
      setComparisons([])
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    comparisons,
    loading,
    error,
    refresh,
  }
}
