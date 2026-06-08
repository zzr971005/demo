import axios, { AxiosInstance, AxiosError } from 'axios'

const api: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export interface SymbolStatus {
  symbol: string
  name: string
  // 后端 symbol_switches 返回 OFF/PAPER/LIVE，进化任务返回 running/paused/stopped/error/idle
  status: 'running' | 'paused' | 'stopped' | 'error' | 'idle' | 'OFF' | 'PAPER' | 'LIVE' | ''
  current_factor: string
  sharpe_ratio: number
  margin_used: number
  margin_total: number
  pnl_daily: number
  pnl_total: number
  updated_at: string
}

export interface FactorInfo {
  id: string
  name: string
  sharpe_ratio: number
  win_rate: number
  trade_count: number
  avg_return: number
  max_drawdown: number
  generation: number
  parent_id?: string
  created_at: string
}

export interface EvolutionNode {
  id: string
  factor_id: string
  generation: number
  sharpe_ratio: number
  parent_id?: string
  children: string[]
  created_at: string
}

export const symbolApi = {
  getAll: () => api.get<SymbolStatus[]>('/symbols'),
  getById: (symbol: string) => api.get<SymbolStatus>(`/symbols/${symbol}`),
  pause: (symbol: string) => api.post(`/symbols/${symbol}/pause`),
  resume: (symbol: string) => api.post(`/symbols/${symbol}/resume`),
  switchFactor: (symbol: string, factorId: string) =>
    api.post(`/symbols/${symbol}/switch`, { factor_id: factorId }),
}

export interface EvolutionFactor {
  id: string
  name?: string
  symbol: string
  expression: string
  sharpe_ratio: number
  calmar_ratio: number
  max_drawdown: number
  total_return: number
  win_rate: number
  total_trades: number
  trade_count?: number
  avg_trade_return: number
  node_count: number
  tree_depth: number
  generation: number
  origin: string
  is_running: boolean
  is_candidate: boolean
  created_at: string
}

export const factorApi = {
  getBySymbol: (symbol: string) => api.get<{ symbol: string; total: number; factors: EvolutionFactor[] }>(`/evolution/factors?symbol=${symbol}`),
  getEvolutionTree: (symbol: string) => api.get<{ symbol: string; total_nodes: number; tree: EvolutionNode[] }>(`/factors/evolution?symbol=${symbol}`),
}

// 进化中心 API
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

export const evolutionApi = {
  getStatus: (symbol?: string) => api.get<EvolutionStatus>(`/evolution/status${symbol ? `?symbol=${symbol}` : ''}`),
  getGenerations: (symbol?: string) =>
    api.get<{ symbol: string; total: number; generations: GenerationMetrics[] }>(
      `/evolution/generations?limit=100000${symbol ? `&symbol=${symbol}` : ''}`
    ),
  getResults: (symbol: string, onlyPassed?: boolean) =>
    api.get<{ symbol: string; total: number; passed: number; factors: EvolutionFactorResult[] }>(
      `/evolution/results?symbol=${symbol}&only_passed=${onlyPassed ? 'true' : 'false'}`
    ),
  start: (config: StartEvolutionRequest) => api.post('/evolution/start', config),
  stop: (params?: { task_id?: string; symbol?: string }) => api.post('/evolution/stop', params),
  getTasks: (_status?: string) => api.get('/evolution/tasks'),
  getDiversityAnalysis: (symbol: string, generation?: number) =>
    api.get<{
      symbol: string
      generation: number | null
      total_factors: number
      unique_expressions: number
      duplicate_rate: number
      duplicate_expressions: Array<{ expression: string; count: number }>
      diversity_score: number
      generation_stats: Record<number, { total: number; unique: number; duplicate_rate: number }>
    }>(`/evolution/diversity-analysis?symbol=${symbol}${generation ? `&generation=${generation}` : ''}`),
}

// 实盘交易API
export interface LiveFactor {
  factor_id: string
  task_id: string
  symbol: string
  expression: string
  generation: number
  origin: string
  sharpe_ratio: number
  calmar_ratio: number
  max_drawdown: number
  total_return: number
  win_rate: number
  total_trades: number
  avg_trade_pnl: number
  turnover_rate: number
  pbo?: number
  dsr?: number
  wfe?: number
  overfitting_passed: boolean
  node_count: number
  tree_depth: number
  is_live: boolean
  is_candidate: boolean
  live_since?: string
  rank_in_generation?: number
  overall_rank?: number
  created_at: string
  live_stats?: LiveStats
}

export interface LiveStats {
  factor_id: string
  symbol: string
  live_sharpe_ratio: number
  live_total_return: number
  live_max_drawdown: number
  live_win_rate: number
  live_total_trades: number
  live_pnl_total: number
  live_pnl_daily: number
  bt_sharpe_ratio: number
  bt_total_return: number
  bt_max_drawdown: number
  performance_decay: number
  days_running: number
  is_active: boolean
  last_updated: string
}

export interface LiveStatsUpdateRequest {
  live_sharpe_ratio?: number
  live_total_return?: number
  live_max_drawdown?: number
  live_win_rate?: number
  live_total_trades?: number
  live_pnl_total?: number
  live_pnl_daily?: number
  days_running?: number
}

export interface LivePerformanceSummary {
  count: number
  avg_live_sharpe: number
  avg_live_return: number
  avg_performance_decay: number
  positive_sharpe_ratio: number
  factors: LiveStats[]
}

export interface BacktestLiveComparison {
  factor_id: string
  symbol: string
  expression: string
  backtest: {
    sharpe_ratio: number
    total_return: number
    max_drawdown: number
    win_rate: number
  }
  live: {
    sharpe_ratio: number
    total_return: number
    max_drawdown: number
    win_rate: number
    total_trades: number
    pnl_total: number
  }
  decay: number
  days_running: number
}

export const liveTradingApi = {
  // 因子部署
  deployFactor: (factorId: string) =>
    api.post<{ success: boolean; factor_id: string; symbol?: string; message: string }>(
      '/live/deploy',
      { factor_id: factorId }
    ),
  removeFactor: (factorId: string) =>
    api.post<{ success: boolean; factor_id: string; message: string }>(
      '/live/remove',
      { factor_id: factorId }
    ),
  markAsCandidate: (factorId: string) =>
    api.post<{ success: boolean; factor_id: string; message: string }>(
      `/live/candidate/${factorId}`
    ),

  // 因子查询
  getLiveFactors: (symbol?: string) =>
    api.get<{ symbol: string; total: number; factors: LiveFactor[] }>(
      `/live/factors${symbol ? `?symbol=${symbol}` : ''}`
    ),
  getCandidateFactors: (symbol?: string) =>
    api.get<{ symbol: string; total: number; factors: LiveFactor[] }>(
      `/live/candidates${symbol ? `?symbol=${symbol}` : ''}`
    ),
  getLiveFactorDetail: (factorId: string) =>
    api.get<{ factor: LiveFactor; live_stats?: LiveStats }>(`/live/factors/${factorId}`),

  // 实盘统计
  updateLiveStats: (factorId: string, stats: LiveStatsUpdateRequest) =>
    api.post<{ success: boolean; factor_id: string; data?: LiveStats; message?: string }>(
      `/live/stats/${factorId}`,
      stats
    ),
  getLiveStats: (factorId: string) =>
    api.get<{ factor_id: string; stats: LiveStats }>(`/live/stats/${factorId}`),
  getLiveSummary: (symbol?: string) =>
    api.get<LivePerformanceSummary>(`/live/summary${symbol ? `?symbol=${symbol}` : ''}`),
  getAllLiveStats: (symbol?: string) =>
    api.get<{ symbol: string; total: number; stats: LiveStats[] }>(
      `/live/all-stats${symbol ? `?symbol=${symbol}` : ''}`
    ),

  // 对比分析
  compareBacktestLive: (factorIds: string[]) =>
    api.get<{ total: number; comparisons: BacktestLiveComparison[] }>(
      `/live/compare?factor_ids=${factorIds.join(',')}`
    ),
}

// ============================================
// 进化周期API (Validation Monitor)
// ============================================

export interface CycleStage {
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  start_time: string | null
  end_time: string | null
  input_count: number
  output_count: number
  drop_count: number
  error_message: string | null
}

export interface EvolutionCycle {
  id: number
  symbol: string
  status: string
  start_time: string
  end_time: string | null
  stages: CycleStage[]
  total_factors: number
  passed_factors: number
  drop_rate: number
}

export interface EvolutionStats {
  total_cycles: number
  completed_cycles: number
  running_cycles: number
  total_factors_evaluated: number
  total_factors_passed: number
  overall_drop_rate: number
}

export const evolutionCyclesApi = {
  getCycles: (symbol?: string) =>
    api.get<EvolutionCycle[]>(`/evolution/cycles${symbol ? `?symbol=${symbol}` : ''}`),
  getCycleById: (cycleId: number) => api.get<EvolutionCycle>(`/evolution/cycles/${cycleId}`),
  getStats: () => api.get<EvolutionStats>('/evolution/stats'),
  getCurrentCycle: () => api.get<EvolutionCycle | null>('/evolution/current'),
}

// ============================================
// 基线对比API (Baseline Comparison)
// ============================================

export interface MetricData {
  name: string
  value: number
  strategy_value: number
  baseline_value: number
  improvement: number
  unit: string
  is_better: boolean
}

export interface EquityPoint {
  date: string
  strategy_equity: number
  baseline_equity: number
}

export interface MonthlyReturn {
  month: string
  strategy_return: number
  baseline_return: number
}

export interface DrawdownPoint {
  date: string
  strategy_drawdown: number
  baseline_drawdown: number
}

export interface BaselineComparisonData {
  symbol: string
  baseline_name: string
  time_period: string
  metrics: MetricData[]
  equity_curve: EquityPoint[]
  monthly_returns: MonthlyReturn[]
  drawdown_curve: DrawdownPoint[]
  win_rate_comparison: {
    long_win_rate: number
    short_win_rate: number
    baseline_win_rate: number
  }
  trade_analysis: {
    total_trades: number
    winning_trades: number
    losing_trades: number
    avg_win: number
    avg_loss: number
    max_win: number
    max_loss: number
    consecutive_wins: number
    consecutive_losses: number
  }
}

export interface BaselineStrategy {
  id: string
  name: string
}

export const baselineApi = {
  getStrategies: () => api.get<BaselineStrategy[]>('/baseline/strategies'),
  getComparison: (symbol: string, baseline: string = 'buy_and_hold') =>
    api.get<BaselineComparisonData>(`/baseline/comparison/${symbol}?baseline=${baseline}`),
  getAllBaselines: (symbol: string) =>
    api.get<{
      symbol: string
      strategy_formula: string | null
      baselines: Array<{
        baseline_type: string
        baseline_name: string
        metrics: Array<{
          name: string
          strategy_value: number
          baseline_value: number
        }>
        equity_curve: Array<{
          date: string
          strategy_equity: number
          baseline_equity: number
        }>
      }>
    }>(`/baseline/all-baselines/${symbol}`),
  getSummary: (symbol: string) => api.get<{
    symbol: string
    baseline_name: string
    time_period: string
    key_metrics: Record<string, {
      strategy: number
      baseline: number
      improvement: number
      is_better: boolean
    }>
    strategy_outperforms: number
    total_metrics: number
  }>(`/baseline/summary/${symbol}`),
}

// ============================================
// 策略替换API (Strategy Replacement)
// ============================================

export interface StrategyPerformance {
  strategy_id: string
  symbol: string
  sharpe_ratio: number
  max_drawdown: number
  win_rate: number
  total_return: number
  trade_count: number
  last_updated: string
}

export interface ReplacementCandidate {
  current_strategy: string
  candidate_strategy: string
  symbol: string
  reason: string
  confidence: number
  performance_improvement: number
  risk_score: number
}

export interface ReplacementRequest {
  symbol: string
  current_strategy: string
  new_strategy: string
  reason?: string
  auto_confirm?: boolean
}

export interface ReplacementResult {
  success: boolean
  symbol: string
  old_strategy: string
  new_strategy: string
  timestamp: string
  reason: string
  transaction_id: string
}

export interface ReplacementRule {
  rule_id: string
  name: string
  description: string
  condition: string
  action: string
  priority: number
  enabled: boolean
  created_at: string
}

export const strategyReplacementApi = {
  getPerformance: (symbol: string) => api.get<StrategyPerformance[]>(`/strategy/performance/${symbol}`),
  getCandidates: (symbol: string) => api.get<ReplacementCandidate[]>(`/strategy/candidates/${symbol}`),
  replaceStrategy: (request: ReplacementRequest) => api.post<ReplacementResult>('/strategy/replace', request),
  getRules: () => api.get<ReplacementRule[]>('/strategy/rules'),
  toggleRule: (ruleId: string, enabled: boolean) => api.put<{ success: boolean; rule_id: string; enabled: boolean }>(`/strategy/rules/${ruleId}/toggle`, { enabled }),
  getHistory: (symbol?: string) => api.get<ReplacementResult[]>(`/strategy/history${symbol ? `?symbol=${symbol}` : ''}`),
  autoCheck: (symbol: string) => api.post<{
    need_replacement: boolean
    candidate?: ReplacementCandidate
    auto_triggered: boolean
    message: string
  }>(`/strategy/auto-check/${symbol}`),
}

// ============================================
// 调度器API (Scheduler)
// ============================================

export interface ScheduledTask {
  task_id: string
  name: string
  symbol: string
  cron_expression: string
  task_type: string
  next_run_time: string | null
  last_run_time: string | null
  status: string
  enabled: boolean
  priority: number
  retry_count: number
  max_retries: number
}

export interface TaskExecution {
  execution_id: string
  task_id: string
  start_time: string
  end_time: string | null
  status: string
  result?: Record<string, any>
  error_message?: string
}

export interface SchedulerStatus {
  running: boolean
  total_tasks: number
  enabled_tasks: number
  running_tasks: number
  total_executions: number
  last_execution_time: string | null
}

export interface CreateTaskRequest {
  name: string
  symbol: string
  cron_expression: string
  task_type?: string
  priority?: number
  enabled?: boolean
}

export const schedulerApi = {
  getStatus: () => api.get<SchedulerStatus>('/scheduler/status'),
  start: () => api.post<{ success: boolean; message: string }>('/scheduler/start'),
  stop: () => api.post<{ success: boolean; message: string }>('/scheduler/stop'),
  getTasks: (symbol?: string) => api.get<ScheduledTask[]>(`/scheduler/tasks${symbol ? `?symbol=${symbol}` : ''}`),
  getTask: (taskId: string) => api.get<ScheduledTask>(`/scheduler/tasks/${taskId}`),
  createTask: (task: CreateTaskRequest) => api.post<ScheduledTask>('/scheduler/tasks', task),
  enableTask: (taskId: string) => api.post<{ success: boolean; task_id: string; enabled: boolean }>(`/scheduler/tasks/${taskId}/enable`),
  disableTask: (taskId: string) => api.post<{ success: boolean; task_id: string; enabled: boolean }>(`/scheduler/tasks/${taskId}/disable`),
  triggerTask: (taskId: string) => api.post<{ success: boolean; task_id: string; message: string }>(`/scheduler/tasks/${taskId}/trigger`),
  deleteTask: (taskId: string) => api.delete<{ success: boolean; task_id: string }>(`/scheduler/tasks/${taskId}`),
  getExecutions: (taskId?: string, limit: number = 50) =>
    api.get<TaskExecution[]>(`/scheduler/executions${taskId ? `?task_id=${taskId}&limit=${limit}` : `?limit=${limit}`}`),
}

// ============================================
// 仓位对账API (Position Reconciliation)
// ============================================

export interface PositionData {
  symbol: string
  direction: string
  volume: number
  open_price: number
  current_price: number
  unrealized_pnl: number
  realized_pnl: number
  margin_used: number
  leverage: number
  update_time: string
}

export interface ReconciliationItem {
  symbol: string
  direction: string
  expected_volume: number
  actual_volume: number
  volume_diff: number
  expected_margin: number
  actual_margin: number
  margin_diff: number
  status: string
  discrepancy: string
  severity: string
}

export interface ReconciliationResult {
  reconciliation_id: string
  start_time: string
  end_time: string
  total_positions: number
  matched_count: number
  mismatched_count: number
  pending_count: number
  items: ReconciliationItem[]
  summary: {
    total_expected_volume: number
    total_actual_volume: number
    total_expected_margin: number
    total_actual_margin: number
    match_rate: number
  }
  status: string
}

export interface PositionAlert {
  alert_id: string
  symbol: string
  alert_type: string
  severity: string
  message: string
  current_value: number
  threshold: number
  timestamp: string
  acknowledged: boolean
}

export interface RiskReport {
  report_id: string
  generated_at: string
  total_exposure: number
  total_margin_used: number
  margin_utilization: number
  total_unrealized_pnl: number
  total_realized_pnl: number
  risk_level: string
  alerts: PositionAlert[]
  recommendations: string[]
}

export const positionApi = {
  getCurrentPositions: (symbol?: string) => api.get<PositionData[]>(`/position/current${symbol ? `?symbol=${symbol}` : ''}`),
  runReconciliation: () => api.post<ReconciliationResult>('/position/reconcile'),
  getReconciliationHistory: (limit: number = 10) => api.get<ReconciliationResult[]>(`/position/reconciliation/history?limit=${limit}`),
  getReconciliationDetail: (reconciliationId: string) => api.get<ReconciliationResult>(`/position/reconciliation/${reconciliationId}`),
  getAlerts: (severity?: string, acknowledged?: boolean) =>
    api.get<PositionAlert[]>(`/position/alerts${severity ? `?severity=${severity}` : ''}${acknowledged !== undefined ? `&acknowledged=${acknowledged}` : ''}`),
  acknowledgeAlert: (alertId: string) => api.put<{ success: boolean; alert_id: string; acknowledged: boolean }>(`/position/alerts/${alertId}/acknowledge`),
  getRiskReport: () => api.get<RiskReport>('/position/risk-report'),
  confirmPosition: (symbol: string, notes?: string) => api.post<{
    success: boolean
    symbol: string
    confirmed_at: string
    notes?: string
    message: string
  }>(`/position/confirm/${symbol}`, { notes }),
  autoConfirm: (threshold: number = 0.01) => api.post<{
    success: boolean
    confirmed_count: number
    total_count: number
    threshold: number
    timestamp: string
  }>('/position/auto-confirm', { threshold }),
}

// ============================================
// 数据完整性检查API (Data Integrity)
// ============================================

export interface IntegrityIssue {
  type: string
  table: string
  severity: string
  details: Record<string, any>
}

export interface IntegrityCheckResult {
  duplicate_expressions: IntegrityIssue[]
  missing_ic_fields: IntegrityIssue[]
  abnormal_factor_values: IntegrityIssue[]
  inconsistent_generations: IntegrityIssue[]
  total_issues: number
  summary: {
    duplicate_expressions: number
    missing_ic_fields: number
    abnormal_factor_values: number
    inconsistent_generations: number
  }
}

export const dataIntegrityApi = {
  runFullCheck: () => api.get<IntegrityCheckResult>('/data-integrity/check'),
  checkDuplicates: () => api.get<IntegrityIssue[]>('/data-integrity/duplicates'),
  checkMissingIC: () => api.get<IntegrityIssue[]>('/data-integrity/missing-ic'),
  checkAbnormalValues: () => api.get<IntegrityIssue[]>('/data-integrity/abnormal-values'),
  checkGenerations: () => api.get<IntegrityIssue[]>('/data-integrity/generations'),
}

export default api
