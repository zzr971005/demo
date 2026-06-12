import { useState, useCallback, useEffect } from 'react'
import { evolutionApi } from '@/lib/api'
import { wsClient } from '@/lib/websocket'

// 世代指标
export interface GenerationMetrics {
  generation: number
  avg_sharpe: number
  max_sharpe: number
  min_sharpe: number
  top_10_sharpe: number
  diversity_score: number
  avg_fitness: number
  best_fitness: number
  unique_expressions: number
  pbo?: number
  dsr?: number
  wfe?: number
  created_at: string
}

// 进化结果因子
export interface EvolutionFactorResult {
  factor_id: string
  expression: string
  generation: number
  origin: string
  sharpe_ratio: number
  calmar_ratio: number
  max_drawdown: number
  total_return: number
  win_rate: number
  total_trades: number
  avg_trade_return: number
  pbo?: number
  dsr?: number
  wfe?: number
  overfitting_passed: boolean
  node_count: number
  tree_depth: number
  created_at: string
}

// 进化状态
export interface EvolutionStatus {
  status: string
  current_generation: number
  total_generations: number
  population_size: number
  elite_count: number
  current_symbol?: string
  start_time?: string
  elapsed_seconds?: number
  estimated_remaining_seconds?: number
}

// 进化启动请求
export interface StartEvolutionRequest {
  symbols: string[]
  generations: number
  population_size: number
  max_stagnation: number
  enable_overfitting_check: boolean
  pbo_threshold: number
  dsr_threshold: number
  wfe_threshold: number
}

export function useEvolutionCenter(symbol: string) {
  const [status, setStatus] = useState<EvolutionStatus>({
    status: 'IDLE',
    current_generation: 0,
    total_generations: 30,
    population_size: 0,
    elite_count: 0,
  })
  const [generations, setGenerations] = useState<GenerationMetrics[]>([])
  const [bestFactors, setBestFactors] = useState<EvolutionFactorResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 获取进化状态
  const fetchStatus = useCallback(async () => {
    try {
      setLoading(true)
      const response = await evolutionApi.getStatus(symbol)
      setStatus(response.data)
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取状态失败')
    } finally {
      setLoading(false)
    }
  }, [symbol])

  // 获取世代历史
  const fetchGenerations = useCallback(async () => {
    try {
      setLoading(true)
      const response = await evolutionApi.getGenerations(symbol)
      // 只要成功响应就更新数据（即使是空数组）
      if (response.data && Array.isArray(response.data.generations)) {
        setGenerations(response.data.generations)
      }
    } catch (err) {
      // 静默失败 - 保留已有数据，不清空
      console.warn('获取世代历史失败:', err)
    } finally {
      setLoading(false)
    }
  }, [symbol])

  // 获取最佳因子
  const fetchBestFactors = useCallback(async () => {
    try {
      setLoading(true)
      const response = await evolutionApi.getResults(symbol, true)
      // 只要成功响应就更新数据（即使是空数组）
      if (response.data && Array.isArray(response.data.factors)) {
        setBestFactors(response.data.factors)
      }
    } catch (err) {
      // 静默失败 - 保留已有数据，不清空
      console.warn('获取最佳因子失败:', err)
    } finally {
      setLoading(false)
    }
  }, [symbol])

  // 启动进化
  const startEvolution = useCallback(async (config: StartEvolutionRequest) => {
    try {
      setError(null)
      await evolutionApi.start(config)
      // 启动后立即刷新状态
      setTimeout(fetchStatus, 1000)
    } catch (err) {
      setError(err instanceof Error ? err.message : '启动失败')
      throw err
    }
  }, [fetchStatus])

  // 停止进化
  const stopEvolution = useCallback(async (symbol?: string) => {
    try {
      await evolutionApi.stop(symbol ? { symbol } : undefined)
      // 停止后刷新状态
      setTimeout(fetchStatus, 500)
    } catch (err) {
      setError(err instanceof Error ? err.message : '停止失败')
      throw err
    }
  }, [fetchStatus])

  // 刷新全部数据
  const refresh = useCallback(async () => {
    await Promise.all([
      fetchStatus(),
      fetchGenerations(),
      fetchBestFactors(),
    ])
  }, [fetchStatus, fetchGenerations, fetchBestFactors])

  // 初始加载
  useEffect(() => {
    refresh()
  }, [refresh])

  // 定期刷新数据（运行中每3秒，其他状态每10秒）
  useEffect(() => {
    const intervalTime = status.status === 'RUNNING' ? 3000 : 10000
    const interval = setInterval(refresh, intervalTime)
    return () => clearInterval(interval)
  }, [status.status, refresh])

  // WebSocket 监听进化进度更新
  useEffect(() => {
    const unsub = wsClient.subscribe<{
      tasks: Array<{
        task_id: string
        symbol: string
        status: string
        current_generation: number
        max_generations: number
        best_fitness: number
        best_sharpe: number
        avg_sharpe: number
        diversity_score: number
        unique_expressions: number
        started_at?: string
        last_heartbeat?: string
      }>
      timestamp: string
    }>('evolution_progress', (data) => {
      if (!data.tasks) return
      
      // 找到当前品种的任务
      const task = data.tasks.find((t) => t.symbol === symbol)
      if (task) {
        setStatus((prev) => ({
          ...prev,
          status: task.status,
          current_generation: task.current_generation,
          total_generations: task.max_generations,
        }))
      }
    })

    return unsub
  }, [symbol])

  return {
    status,
    generations,
    bestFactors,
    currentGeneration: status.current_generation,
    totalGenerations: status.total_generations,
    elapsedSeconds: status.elapsed_seconds,
    estimatedRemainingSeconds: status.estimated_remaining_seconds,
    loading,
    error,
    startEvolution,
    stopEvolution,
    refresh,
  }
}
