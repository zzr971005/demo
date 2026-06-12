import { useState, useCallback } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts'
import {
  Play,
  Square,
  RefreshCw,
  Settings,
  Activity,
  Zap,
  TrendingUp,
  Target,
  CheckCircle,
  XCircle,
  Clock,
  Cpu,
  GitBranch,
  BarChart3,
  AlertTriangle,
} from 'lucide-react'
import { useEvolutionCenter, type GenerationMetrics, type EvolutionFactorResult } from '@/hooks/useEvolutionCenter'
import { evolutionApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { cn } from '@/lib/utils'
import SymbolControlPanel from '@/components/SymbolControlPanel'
import { SYMBOLS } from '@/constants/symbols'

function StatusBadge({ status }: { status: string }) {
  const config = {
    IDLE: { color: 'bg-gray-500', label: '空闲' },
    RUNNING: { color: 'bg-green-500', label: '运行中' },
    STOPPED: { color: 'bg-yellow-500', label: '已停止' },
    ERROR: { color: 'bg-red-500', label: '错误' },
  }

  const { color, label } = config[status as keyof typeof config] || config.IDLE

  return (
    <Badge variant="outline" className={cn('gap-1', color.replace('bg-', 'text-'))}>
      <span className={cn('w-2 h-2 rounded-full', color)} />
      {label}
    </Badge>
  )
}

function ControlPanel({
  symbol,
  symbols,
  onSymbolChange,
  config,
  onConfigChange,
  status,
  onStart,
  onStop,
  onRefresh,
}: {
  symbol: string
  symbols: { symbol: string; name: string }[]
  onSymbolChange: (symbol: string) => void
  config: { generations: number; population_size: number; enable_overfitting_check: boolean; continuous_evolution: boolean }
  onConfigChange: (key: string, value: number | boolean) => void
  status: string
  onStart: () => void
  onStop: () => void
  onRefresh: () => void
}) {
  const isRunning = status === 'RUNNING'

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Settings className="h-5 w-5 text-primary" />
          进化控制
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 品种选择 */}
        <div>
          <label className="text-sm font-medium text-muted-foreground mb-2 block">选择品种</label>
          <select
            value={symbol}
            onChange={(e) => onSymbolChange(e.target.value)}
            disabled={isRunning}
            className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          >
            {symbols.map((s) => (
              <option key={s.symbol} value={s.symbol}>
                {s.symbol} - {s.name}
              </option>
            ))}
          </select>
        </div>

        {/* 参数配置 */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-muted-foreground mb-1 block">进化世代</label>
            <p className="text-xs text-muted-foreground mb-2">
              遗传编程迭代次数，每代基于优秀个体生成新策略
              {config.continuous_evolution && '（持续进化模式已启用，建议设为较大值）'}
            </p>
            <input
              type="number"
              value={config.generations}
              onChange={(e) => onConfigChange('generations', parseInt(e.target.value))}
              disabled={isRunning}
              min={5}
              max={99999999}
              className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring font-mono"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-muted-foreground mb-1 block">种群大小</label>
            <p className="text-xs text-muted-foreground mb-2">每代策略数量，越多越多样但计算越慢</p>
            <input
              type="number"
              value={config.population_size}
              onChange={(e) => onConfigChange('population_size', parseInt(e.target.value))}
              disabled={isRunning}
              min={10}
              max={500}
              className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring font-mono"
            />
          </div>
        </div>

        {/* 持续进化开关 */}
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="continuous-evolution"
            checked={config.continuous_evolution}
            onChange={(e) => onConfigChange('continuous_evolution', e.target.checked)}
            disabled={isRunning}
            className="h-4 w-4 rounded border-input"
          />
          <label htmlFor="continuous-evolution" className="text-sm">
            持续进化模式（永不停止）
          </label>
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="overfitting-check"
              checked={config.enable_overfitting_check}
              onChange={(e) => onConfigChange('enable_overfitting_check', e.target.checked)}
              disabled={isRunning}
              className="h-4 w-4 rounded border-input"
            />
            <label htmlFor="overfitting-check" className="text-sm">
              启用过拟合检验 (PBO/DSR/WFE)
            </label>
          </div>
          <div className="pl-6 space-y-1">
            <p className="text-xs text-muted-foreground"><span className="font-medium">PBO:</span> 回测过拟合概率，值越低越好(&lt;30%)</p>
            <p className="text-xs text-muted-foreground"><span className="font-medium">DSR:</span> 放气夏普比率，修正过乐观的夏普(&gt;60%)</p>
            <p className="text-xs text-muted-foreground"><span className="font-medium">WFE:</span> 样本外检验效率，衡量策略稳健性</p>
          </div>
        </div>

        {/* 状态显示 */}
        <div className="flex items-center justify-between py-2 border-t border-b border-border">
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">当前状态:</span>
            <StatusBadge status={status} />
          </div>
          <Button
            variant="outline"
            size="icon"
            onClick={onRefresh}
            disabled={isRunning}
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>

        {/* 操作按钮 */}
        <div className="flex gap-3">
          <button
            onClick={onStart}
            disabled={isRunning}
            className="group flex-1 flex items-center justify-center gap-2 h-10 rounded-xl border-2 border-green-200/80 bg-gradient-to-b from-green-50 to-green-100/90 text-green-700 text-sm font-semibold transition-all duration-200 hover:from-green-100 hover:to-green-200 hover:border-green-300 hover:shadow-lg hover:shadow-green-100/50 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98] active:shadow-none"
          >
            <Play className="h-4 w-4" />
            启动进化
          </button>
          <button
            onClick={onStop}
            disabled={!isRunning}
            className="group flex-1 flex items-center justify-center gap-2 h-10 rounded-xl border-2 border-red-200/80 bg-gradient-to-b from-red-50 to-red-100/90 text-red-700 text-sm font-semibold transition-all duration-200 hover:from-red-100 hover:to-red-200 hover:border-red-300 hover:shadow-lg hover:shadow-red-100/50 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98] active:shadow-none"
          >
            <Square className="h-4 w-4" />
            停止进化
          </button>
        </div>
      </CardContent>
    </Card>
  )
}

function EvolutionProgress({
  currentGeneration,
  totalGenerations,
  elapsedSeconds,
  estimatedRemainingSeconds,
}: {
  currentGeneration: number
  totalGenerations: number
  elapsedSeconds?: number
  estimatedRemainingSeconds?: number
}) {
  const isContinuous = totalGenerations > 100000
  const progress = totalGenerations > 0 ? (currentGeneration / totalGenerations) * 100 : 0

  const formatTime = (seconds?: number, isRemaining = false) => {
    if (isRemaining && isContinuous) return '∞'
    if (!seconds || seconds < 0) return '-'
    const hours = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)
    return `${hours}H ${mins.toString().padStart(2, '0')}M ${secs.toString().padStart(2, '0')}S`
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-primary" />
          进化进度
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">
              世代 {currentGeneration} {isContinuous ? '' : `/ ${totalGenerations}`}
            </span>
            <span className="text-sm text-muted-foreground font-mono">
              {isContinuous ? '∞' : `${progress.toFixed(1)}%`}
            </span>
          </div>
          <Progress value={isContinuous ? undefined : progress} className="h-3" />
        </div>

        <div className="grid grid-cols-3 gap-4 pt-2">
          <div className="text-center">
            <Clock className="h-4 w-4 mx-auto mb-1 text-muted-foreground" />
            <div className="text-lg font-mono font-bold">{formatTime(elapsedSeconds)}</div>
            <div className="text-xs text-muted-foreground">已用时间</div>
          </div>
          <div className="text-center">
            <TrendingUp className="h-4 w-4 mx-auto mb-1 text-muted-foreground" />
            <div className="text-lg font-mono font-bold">{formatTime(estimatedRemainingSeconds, true)}</div>
            <div className="text-xs text-muted-foreground">预计剩余</div>
          </div>
          <div className="text-center">
            <Cpu className="h-4 w-4 mx-auto mb-1 text-muted-foreground" />
            <div className="text-lg font-mono font-bold">
              {currentGeneration > 0 ? ((elapsedSeconds || 0) / currentGeneration).toFixed(5) : '0.00000'}s
            </div>
            <div className="text-xs text-muted-foreground">每代平均</div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function MetricsCharts({ generations }: { generations: GenerationMetrics[] }) {
  // 长时间运行只显示最近100代，避免图表过于拥挤
  const displayGenerations = generations.length > 100 
    ? generations.slice(-100) 
    : generations

  const chartData = displayGenerations.map((g) => ({
    gen: `G${g.generation}`,
    max_sharpe: parseFloat(g.max_sharpe.toFixed(3)),
    avg_sharpe: parseFloat(g.avg_sharpe.toFixed(3)),
    diversity: parseFloat(g.diversity_score.toFixed(3)),
    pbo: g.pbo !== undefined ? parseFloat((g.pbo * 100).toFixed(1)) : null,
    dsr: g.dsr !== undefined ? parseFloat((g.dsr * 100).toFixed(1)) : null,
    unique_expr: g.unique_expressions,
  }))

  const isEmpty = generations.length === 0

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* 夏普比率曲线 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-primary" />
            夏普比率趋势
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-56">
            {isEmpty ? (
              <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                等待进化数据...
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="gen" stroke="hsl(var(--muted-foreground))" fontSize={11} />
                  <YAxis domain={[-2, 'auto']} stroke="hsl(var(--muted-foreground))" fontSize={11} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '0.5rem',
                    }}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="max_sharpe"
                    name="最佳夏普"
                    stroke="#10b981"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="avg_sharpe"
                    name="平均夏普"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-primary" />
            种群多样性
          </CardTitle>
          <CardDescription className="text-xs">
            衡量策略之间的差异程度，值越高表示策略越多样化
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground mb-3">
            <span className="font-medium">多样性得分:</span> 显示种群中策略的多样性变化。
            过高的多样性可能导致收敛慢，过低则可能陷入局部最优。
          </p>
          <div className="h-56">
            {isEmpty ? (
              <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                等待进化数据...
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="gen" stroke="hsl(var(--muted-foreground))" fontSize={11} />
                  <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '0.5rem',
                    }}
                  />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="diversity"
                    name="多样性得分"
                    stroke="#8b5cf6"
                    fill="#8b5cf6"
                    fillOpacity={0.2}
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </CardContent>
      </Card>

      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Target className="h-4 w-4 text-primary" />
            过拟合检验指标
          </CardTitle>
          <CardDescription className="text-xs">
            评估策略回测结果的可靠性，防止过拟合
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4 mb-3 text-xs text-muted-foreground">
            <span><span className="font-medium text-red-500">PBO (%):</span> 回测过拟合概率，值越低越好(&lt;30%)</span>
            <span><span className="font-medium text-blue-500">DSR (%):</span> 放气夏普比率，修正过乐观的夏普(&gt;60%)</span>
          </div>
          <div className="h-56">
            {isEmpty ? (
              <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                等待进化数据...
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="gen" stroke="hsl(var(--muted-foreground))" fontSize={11} />
                  <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '0.5rem',
                    }}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="pbo"
                    name="PBO (%)"
                    stroke="#ef4444"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="dsr"
                    name="DSR (%)"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function BestFactorsTable({
  factors,
  onlyPassed,
  onOnlyPassedChange,
}: {
  factors: EvolutionFactorResult[]
  onlyPassed: boolean
  onOnlyPassedChange: (value: boolean) => void
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-primary" />
            最佳因子
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline">总计: {factors.length}</Badge>
            <Badge variant="outline" className="bg-green-500/10 text-green-600">
              通过: {factors.filter((f) => f.overfitting_passed).length}
            </Badge>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={onlyPassed}
                onChange={(e) => onOnlyPassedChange(e.target.checked)}
                className="h-4 w-4 rounded border-input"
              />
              仅显示通过过拟合检验的
            </label>
          </div>
        </CardTitle>
        <CardDescription className="text-xs mt-2">
          <span className="font-medium">综合评分公式：</span>
          评分 = 验证评分 × 0.4 + IC评分 × 0.4 + 稳定性评分 × 0.2
          <span className="text-muted-foreground ml-2">（IC评分基于多窗口IC均值，稳定性评分基于IC半衰期）</span>
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-3 px-2 font-medium">#</th>
                <th className="text-left py-3 px-2 font-medium">因子ID</th>
                <th className="text-left py-3 px-2 font-medium">世代</th>
                <th className="text-left py-3 px-2 font-medium">来源</th>
                <th className="text-right py-3 px-2 font-medium">综合评分</th>
                <th className="text-right py-3 px-2 font-medium">夏普</th>
                <th className="text-right py-3 px-2 font-medium">IC 24h</th>
                <th className="text-right py-3 px-2 font-medium">IC IR</th>
                <th className="text-right py-3 px-2 font-medium">IC半衰期</th>
                <th className="text-right py-3 px-2 font-medium">Calmar</th>
                <th className="text-right py-3 px-2 font-medium">年化收益率</th>
                <th className="text-right py-3 px-2 font-medium">最大回撤</th>
                <th className="text-right py-3 px-2 font-medium">胜率</th>
                <th className="text-center py-3 px-2 font-medium">过拟合检验</th>
              </tr>
            </thead>
            <tbody>
              {factors
                .filter((f) => !onlyPassed || f.overfitting_passed)
                .slice(0, 20)
                .map((factor, idx) => {
                  // 计算综合评分（前端显示用）
                  const sharpeNorm = Math.max(0, Math.min(1, (factor.sharpe_ratio + 2) / 7))
                  const calmarNorm = Math.max(0, Math.min(1, factor.calmar_ratio / 5))
                  const drawdownScore = Math.max(0, 1 - factor.max_drawdown)
                  const tradesNorm = Math.min(1, (factor.total_trades || 0) / 100)
                  const validationScore = sharpeNorm * 0.4 + calmarNorm * 0.2 + drawdownScore * 0.2 + factor.win_rate * 0.1 + tradesNorm * 0.1

                  // IC评分（如果有IC数据）
                  const icMean24h = (factor as any).ic_mean_24h || 0
                  const icIr = (factor as any).ic_ir || 0
                  const icHalfLife = (factor as any).ic_half_life || 0
                  const icScore = Math.max(0, icMean24h) * 0.6 + Math.max(0, icIr) * 0.2
                  const stabilityScore = Math.min(1, icHalfLife / 168) * 0.2

                  // 综合评分 = 验证评分 × 0.4 + IC评分 × 0.4 + 稳定性评分 × 0.2
                  const compositeScore = validationScore * 0.4 + icScore * 0.4 + stabilityScore * 0.2

                  return (
                    <tr key={factor.factor_id} className="border-b border-border hover:bg-accent/50">
                      <td className="py-2 px-2 text-muted-foreground font-mono">{idx + 1}</td>
                      <td className="py-2 px-2 font-mono font-medium">{factor.factor_id}</td>
                      <td className="py-2 px-2 font-mono">G{factor.generation}</td>
                      <td className="py-2 px-2">
                        <Badge variant="outline" className="text-xs">
                          {factor.origin}
                        </Badge>
                      </td>
                      <td className="py-2 px-2 text-right font-mono font-bold text-purple-600">
                        {compositeScore.toFixed(3)}
                      </td>
                      <td className="py-2 px-2 text-right font-mono font-medium text-green-600">
                        {factor.sharpe_ratio.toFixed(3)}
                      </td>
                      <td className="py-2 px-2 text-right font-mono text-blue-600">
                        {icMean24h > 0 ? icMean24h.toFixed(3) : '-'}
                      </td>
                      <td className="py-2 px-2 text-right font-mono">
                        {icIr > 0 ? icIr.toFixed(3) : '-'}
                      </td>
                      <td className="py-2 px-2 text-right font-mono">
                        {icHalfLife > 0 ? `${icHalfLife.toFixed(0)}h` : '-'}
                      </td>
                      <td className="py-2 px-2 text-right font-mono">{factor.calmar_ratio.toFixed(3)}</td>
                      <td className="py-2 px-2 text-right font-mono text-blue-600">
                        {(factor.total_return * 100).toFixed(1)}%
                      </td>
                      <td className="py-2 px-2 text-right font-mono text-red-600">
                        {(factor.max_drawdown * 100).toFixed(1)}%
                      </td>
                      <td className="py-2 px-2 text-right font-mono">
                        {(factor.win_rate * 100).toFixed(1)}%
                      </td>
                      <td className="py-2 px-2 text-center">
                        <div className="flex items-center justify-center gap-1">
                          {factor.overfitting_passed ? (
                            <CheckCircle className="h-4 w-4 text-green-500" />
                          ) : (
                            <XCircle className="h-4 w-4 text-red-500" />
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

export default function EvolutionCenter() {
  const [selectedSymbol, setSelectedSymbol] = useState('RB')
  const [onlyPassed, setOnlyPassed] = useState(true)
  const [diversityData, setDiversityData] = useState<any>(null)
  const [loadingDiversity, setLoadingDiversity] = useState(false)
  const [config, setConfig] = useState({
    generations: 99999999,
    population_size: 100,
    continuous_evolution: true,
    enable_overfitting_check: true,
  })

  const {
    status,
    generations,
    bestFactors,
    currentGeneration,
    totalGenerations,
    elapsedSeconds,
    estimatedRemainingSeconds,
    loading,
    error,
    startEvolution,
    stopEvolution,
    refresh,
  } = useEvolutionCenter(selectedSymbol)

  const handleConfigChange = useCallback((key: string, value: number | boolean) => {
    setConfig((prev) => ({ ...prev, [key]: value }))
  }, [])

  const handleStart = useCallback(() => {
    startEvolution({
      symbols: [selectedSymbol],
      generations: config.generations,
      population_size: config.population_size,
      max_stagnation: config.continuous_evolution ? 0 : 10,
      enable_overfitting_check: config.enable_overfitting_check,
      pbo_threshold: 0.3,
      dsr_threshold: 0.6,
      wfe_threshold: 0.7,
    })
  }, [selectedSymbol, config, startEvolution])

  const handleStop = useCallback(() => {
    stopEvolution(selectedSymbol)
  }, [stopEvolution, selectedSymbol])

  const handleDiversityCheck = useCallback(async () => {
    setLoadingDiversity(true)
    try {
      const response = await evolutionApi.getDiversityAnalysis(selectedSymbol)
      setDiversityData(response.data)
    } catch (error) {
      console.error('Failed to get diversity analysis:', error)
    } finally {
      setLoadingDiversity(false)
    }
  }, [selectedSymbol])

  // 品种列表（与后端 system.yaml 配置一致）
  const symbols = SYMBOLS.map((s) => ({ symbol: s.value, name: s.name }))

  return (
    <div className="flex gap-6">
      {/* 左侧主内容区 */}
      <div className="flex-1 space-y-6">
        {/* 页面标题 */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Zap className="h-6 w-6 text-primary" />
              进化中心
            </h1>
            <p className="text-muted-foreground">遗传编程因子自动挖掘与优化</p>
          </div>
          <Button variant="outline" onClick={refresh} disabled={loading}>
            <RefreshCw className={cn('h-4 w-4 mr-2', loading && 'animate-spin')} />
            刷新
          </Button>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="rounded-md border border-destructive bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        )}

        {/* 控制面板 + 进度 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ControlPanel
            symbol={selectedSymbol}
            symbols={symbols}
            onSymbolChange={setSelectedSymbol}
            config={config}
            onConfigChange={handleConfigChange}
            status={status.status}
            onStart={handleStart}
            onStop={handleStop}
            onRefresh={refresh}
          />
          <EvolutionProgress
            currentGeneration={currentGeneration}
            totalGenerations={totalGenerations}
            elapsedSeconds={elapsedSeconds}
            estimatedRemainingSeconds={estimatedRemainingSeconds}
          />
        </div>

        {/* 多样性检查 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <GitBranch className="h-5 w-5 text-primary" />
              因子多样性检查
            </CardTitle>
            <CardDescription>检查因子表达式的重复情况</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-3 mb-4">
              <Button
                onClick={handleDiversityCheck}
                disabled={loadingDiversity}
                variant="outline"
              >
                <RefreshCw className={cn('h-4 w-4 mr-2', loadingDiversity && 'animate-spin')} />
                检查多样性
              </Button>
            </div>

            {diversityData && (
              <>
                <div className="grid grid-cols-4 gap-4 mb-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold">{diversityData.total_factors}</div>
                    <div className="text-xs text-muted-foreground">总因子数</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold">{diversityData.unique_expressions}</div>
                    <div className="text-xs text-muted-foreground">唯一表达式</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold">{(diversityData.duplicate_rate * 100).toFixed(1)}%</div>
                    <div className="text-xs text-muted-foreground">重复率</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold">{diversityData.diversity_score.toFixed(3)}</div>
                    <div className="text-xs text-muted-foreground">多样性得分</div>
                  </div>
                </div>

                {diversityData.duplicate_rate > 0.3 && (
                  <Alert variant="destructive">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>
                      重复率过高 ({(diversityData.duplicate_rate * 100).toFixed(1)}%)，建议检查进化参数配置
                    </AlertDescription>
                  </Alert>
                )}

                {diversityData.duplicate_expressions.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-sm font-medium mb-2">重复表达式 (前10个)</h4>
                    <div className="space-y-1">
                      {diversityData.duplicate_expressions.slice(0, 10).map((item: { expression: string; count: number }, idx: number) => (
                        <div key={idx} className="flex items-center justify-between text-xs p-2 bg-accent rounded">
                          <span className="font-mono truncate flex-1">{item.expression}</span>
                          <Badge variant="outline" className="ml-2">{item.count}次</Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>

        {/* 指标图表 */}
        <MetricsCharts generations={generations} />

        {/* 最佳因子表格 */}
        <BestFactorsTable
          factors={bestFactors}
          onlyPassed={onlyPassed}
          onOnlyPassedChange={setOnlyPassed}
        />
      </div>

      {/* 右侧品种管理面板 */}
      <div className="hidden xl:block w-80 shrink-0">
        <SymbolControlPanel />
      </div>
    </div>
  )
}
