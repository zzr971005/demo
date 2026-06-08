import { useState } from 'react'
import {
  Play,
  Pause,
  Square,
  RefreshCw,
  Activity,
  Zap,
  CheckCircle,
  AlertCircle,
  Clock,
  ChevronDown,
  ChevronUp,
  TrendingUp,
  TrendingDown,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'
import { useSymbols } from '@/hooks/useSymbols'
import { evolutionApi } from '@/lib/api'

// 品种分组配置
const SYMBOL_GROUPS = {
  lowMargin: {
    title: '低保证金品种',
    symbols: ['RB', 'MA', 'M', 'TA', 'FG', 'SR', 'SA', 'PP'],
    color: 'blue',
  },
  highMargin: {
    title: '高保证金品种',
    symbols: ['AU', 'CU', 'SC', 'IF'],
    color: 'purple',
  },
}

// 状态配置（兼容 symbol_switches 的 OFF/PAPER/LIVE 和进化任务的 idle/running/paused/error）
const STATUS_CONFIG: Record<string, { label: string; color: string; textColor: string; icon: React.ElementType }> = {
  idle: {
    label: '空闲',
    color: 'bg-gray-500',
    textColor: 'text-gray-500',
    icon: Clock,
  },
  running: {
    label: '运行中',
    color: 'bg-green-500',
    textColor: 'text-green-500',
    icon: Activity,
  },
  paused: {
    label: '已暂停',
    color: 'bg-yellow-500',
    textColor: 'text-yellow-500',
    icon: Pause,
  },
  error: {
    label: '错误',
    color: 'bg-red-500',
    textColor: 'text-red-500',
    icon: AlertCircle,
  },
  OFF: {
    label: '空闲',
    color: 'bg-gray-500',
    textColor: 'text-gray-500',
    icon: Clock,
  },
  PAPER: {
    label: '运行中',
    color: 'bg-green-500',
    textColor: 'text-green-500',
    icon: Activity,
  },
  LIVE: {
    label: '实盘',
    color: 'bg-orange-500',
    textColor: 'text-orange-500',
    icon: Zap,
  },
}

// 品种中文名映射
const SYMBOL_NAMES: Record<string, string> = {
  RB: '螺纹钢',
  MA: '甲醇',
  M: '豆粕',
  TA: 'PTA',
  FG: '玻璃',
  SR: '白糖',
  SA: '纯碱',
  PP: '聚丙烯',
  AU: '黄金',
  CU: '铜',
  SC: '原油',
  IF: '股指',
}

interface SymbolCardProps {
  symbol: string
  name: string
  status: string
  sharpe_ratio: number
  margin_used: number
  margin_total: number
  pnl_daily: number
  onStart: () => void
  onStop: () => void
}

function SymbolCard({
  symbol,
  name,
  status,
  sharpe_ratio,
  margin_used,
  margin_total,
  pnl_daily,
  onStart,
  onStop,
}: SymbolCardProps) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.idle
  const StatusIcon = config.icon
  const marginPercent = margin_total > 0 ? (margin_used / margin_total) * 100 : 0
  const isRunning = status === 'PAPER' || status === 'LIVE' || status === 'running'

  return (
    <Card className="bg-card/80 backdrop-blur-sm border-border/50 hover:border-primary/30 transition-all duration-200 hover:shadow-md">
      <CardContent className="p-3 space-y-2">
        {/* 头部：品种名和状态 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-bold text-sm text-foreground">{symbol}</span>
            <span className="text-xs text-muted-foreground">{name}</span>
          </div>
          <div className="flex items-center gap-1">
            <StatusIcon className={cn('h-3.5 w-3.5', config.textColor)} />
            <span className={cn('text-xs font-medium', config.textColor)}>{config.label}</span>
          </div>
        </div>

        {/* 指标行 */}
        <div className="grid grid-cols-2 gap-2">
          <div className="flex items-center gap-1">
            <TrendingUp className={cn('h-3 w-3', sharpe_ratio >= 0 ? 'text-green-500' : 'text-red-500')} />
            <span className="text-xs font-mono">{sharpe_ratio.toFixed(2)}</span>
          </div>
          <div className="flex items-center gap-1">
            {pnl_daily >= 0 ? (
              <TrendingUp className="h-3 w-3 text-green-500" />
            ) : (
              <TrendingDown className="h-3 w-3 text-red-500" />
            )}
            <span className={cn('text-xs font-mono', pnl_daily >= 0 ? 'text-green-500' : 'text-red-500')}>
              {pnl_daily >= 0 ? '+' : ''}{pnl_daily.toFixed(2)}%
            </span>
          </div>
        </div>

        {/* 保证金进度条 */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">保证金</span>
            <span className="font-mono">{marginPercent.toFixed(0)}%</span>
          </div>
          <Progress
            value={Math.min(marginPercent, 100)}
            className="h-1.5"
            style={{
              background: marginPercent > 80 ? 'rgba(239, 68, 68, 0.2)' : undefined,
            }}
          />
        </div>

        {/* 操作按钮 */}
        <div className="flex gap-2 pt-1">
          {isRunning ? (
            <button
              onClick={onStop}
              title="停止进化"
              className="group flex items-center justify-center w-8 h-7 rounded-md border border-red-200 bg-red-50/50 text-red-600 transition-all duration-150 hover:border-red-300 hover:bg-red-100 hover:shadow-sm active:scale-95 active:bg-red-200"
            >
              <Square className="h-3.5 w-3.5" />
            </button>
          ) : (
            <button
              onClick={onStart}
              title="启动进化"
              className="group flex items-center justify-center w-8 h-7 rounded-md border border-green-200 bg-green-50/50 text-green-600 transition-all duration-150 hover:border-green-300 hover:bg-green-100 hover:shadow-sm active:scale-95 active:bg-green-200"
            >
              <Play className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

interface SymbolGroupProps {
  title: string
  symbols: string[]
  color: string
  symbolList: { symbol: string; name: string; status: string; sharpe_ratio: number; margin_used: number; margin_total: number; pnl_daily: number }[]
  onStart: (symbol: string) => void
  onStop: (symbol: string) => void
}

function SymbolGroup({ title, symbols, color, symbolList, onStart, onStop }: SymbolGroupProps) {
  const [expanded, setExpanded] = useState(true)
  const filteredSymbols = symbolList.filter((s) => symbols.includes(s.symbol))
  
  const colorClasses = {
    blue: {
      header: 'bg-blue-50 border-blue-200',
      icon: 'text-blue-500',
      badge: 'bg-blue-100 text-blue-600',
    },
    purple: {
      header: 'bg-purple-50 border-purple-200',
      icon: 'text-purple-500',
      badge: 'bg-purple-100 text-purple-600',
    },
  }

  const runningCount = filteredSymbols.filter((s) => s.status === 'running').length

  return (
    <div className="space-y-2">
      {/* 分组头部 */}
      <button
        className={cn(
          'w-full flex items-center justify-between rounded-lg px-3 py-2 text-sm font-medium transition-colors',
          colorClasses[color as keyof typeof colorClasses].header
        )}
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <Zap className={cn('h-4 w-4', colorClasses[color as keyof typeof colorClasses].icon)} />
          <span>{title}</span>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary" className={colorClasses[color as keyof typeof colorClasses].badge}>
            {runningCount}/{symbols.length} 运行中
          </Badge>
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </button>

      {/* 分组内容 */}
      {expanded && (
        <div className="grid grid-cols-1 gap-2 pl-1">
          {filteredSymbols.map((item) => (
            <SymbolCard
              key={item.symbol}
              symbol={item.symbol}
              name={item.name}
              status={item.status}
              sharpe_ratio={item.sharpe_ratio}
              margin_used={item.margin_used}
              margin_total={item.margin_total}
              pnl_daily={item.pnl_daily}
              onStart={() => onStart(item.symbol)}
              onStop={() => onStop(item.symbol)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default function SymbolControlPanel() {
  const { symbols, refresh } = useSymbols()
  const [continuousEvolution, setContinuousEvolution] = useState(false)

  // 构建完整的品种列表（包含所有12个品种）
  const allSymbols = Object.values(SYMBOL_GROUPS).flatMap((g) => g.symbols)
  const symbolList = allSymbols.map((symbol) => {
    const existing = symbols.find((s) => s.symbol === symbol)
    return {
      symbol,
      name: SYMBOL_NAMES[symbol] || symbol,
      status: existing?.status || 'idle',
      sharpe_ratio: existing?.sharpe_ratio || 0,
      margin_used: existing?.margin_used || 0,
      margin_total: existing?.margin_total || 100000,
      pnl_daily: existing?.pnl_daily || 0,
    }
  })

  // 后端返回 OFF/PAPER/LIVE，需要重新计算计数
  const runningCount = symbolList.filter(
    (s) => s.status === 'PAPER' || s.status === 'LIVE' || s.status === 'running'
  ).length
  const pausedCount = symbolList.filter((s) => s.status === 'paused').length
  const errorCount = symbolList.filter((s) => s.status === 'error').length

  // 启动单个品种进化
  const handleStart = async (symbol: string) => {
    try {
      await evolutionApi.start({
        symbols: [symbol],
        generations: continuousEvolution ? 999999 : 30,
        population_size: 100,
        max_stagnation: continuousEvolution ? 0 : 10,
        enable_overfitting_check: true,
        pbo_threshold: 0.3,
        dsr_threshold: 0.6,
        wfe_threshold: 0.7,
      })
      console.log(`已启动品种 ${symbol} 的进化${continuousEvolution ? '（持续模式）' : ''}`)
      // 延迟刷新状态
      setTimeout(refresh, 1000)
    } catch (error) {
      console.error(`启动品种 ${symbol} 进化失败:`, error)
    }
  }

  // 停止单个品种进化
  const handleStopSingle = async (symbol: string) => {
    try {
      await evolutionApi.stop({ symbol })
      console.log(`已停止品种 ${symbol} 的进化`)
      setTimeout(refresh, 500)
    } catch (error) {
      console.error(`停止品种 ${symbol} 进化失败:`, error)
    }
  }

  // 批量启动所有品种进化
  const handleStartAll = async () => {
    try {
      await evolutionApi.start({
        symbols: allSymbols,
        generations: continuousEvolution ? 999999 : 30,
        population_size: 100,
        max_stagnation: continuousEvolution ? 0 : 10,
        enable_overfitting_check: true,
        pbo_threshold: 0.3,
        dsr_threshold: 0.6,
        wfe_threshold: 0.7,
      })
      console.log(`已启动所有品种进化${continuousEvolution ? '（持续模式）' : ''}`)
      setTimeout(refresh, 1000)
    } catch (error) {
      console.error('启动所有品种进化失败:', error)
    }
  }

  // 批量停止所有品种进化
  const handleStopAll = async () => {
    try {
      await evolutionApi.stop()
      console.log('已停止所有品种进化')
      setTimeout(refresh, 500)
    } catch (error) {
      console.error('停止所有品种进化失败:', error)
    }
  }

  return (
    <Card className="h-full sticky top-6 overflow-hidden">
      <CardHeader className="bg-gradient-to-r from-primary/10 to-accent/10 border-b border-border">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <Activity className="h-5 w-5 text-primary" />
              品种管理
            </CardTitle>
            <CardDescription className="text-xs">实时监控与批量操作</CardDescription>
          </div>
          <div className="flex items-center gap-1">
            <Badge className="bg-green-100 text-green-600">
              <CheckCircle className="h-3 w-3 mr-1" />
              {runningCount} 运行
            </Badge>
            <Badge className="bg-yellow-100 text-yellow-600">
              {pausedCount} 暂停
            </Badge>
            {errorCount > 0 && (
              <Badge className="bg-red-100 text-red-600">
                <AlertCircle className="h-3 w-3 mr-1" />
                {errorCount} 错误
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-3 space-y-4 max-h-[calc(100vh-200px)] overflow-y-auto pr-1">
        {/* 批量操作按钮 */}
        <div className="flex gap-2">
          <button
            onClick={handleStartAll}
            className="group flex-1 flex items-center justify-center gap-1.5 h-8 rounded-lg border border-green-200/70 bg-gradient-to-b from-green-50 to-green-100/80 text-green-700 text-xs font-medium transition-all duration-150 hover:from-green-100 hover:to-green-200 hover:shadow-sm active:scale-[0.98] active:shadow-none"
          >
            <Play className="h-3.5 w-3.5" />
            <span>全部启动</span>
          </button>
          <button
            onClick={handleStopAll}
            className="group flex-1 flex items-center justify-center gap-1.5 h-8 rounded-lg border border-red-200/70 bg-gradient-to-b from-red-50 to-red-100/80 text-red-700 text-xs font-medium transition-all duration-150 hover:from-red-100 hover:to-red-200 hover:shadow-sm active:scale-[0.98] active:shadow-none"
          >
            <Square className="h-3.5 w-3.5" />
            <span>全部停止</span>
          </button>
          <button
            onClick={refresh}
            className="group flex items-center justify-center w-8 h-8 rounded-lg border border-slate-200/70 bg-gradient-to-b from-slate-50 to-slate-100/80 text-slate-600 transition-all duration-150 hover:from-slate-100 hover:to-slate-200 hover:shadow-sm active:scale-[0.98] active:shadow-none"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>

        {/* 持续进化模式开关 */}
        <div className="flex items-center justify-between px-1 py-2 bg-muted/50 rounded-lg">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="continuous-evolution-panel"
              checked={continuousEvolution}
              onChange={(e) => setContinuousEvolution(e.target.checked)}
              className="h-3.5 w-3.5 rounded border-input"
            />
            <label htmlFor="continuous-evolution-panel" className="text-xs text-muted-foreground">
              持续进化模式（永不停止）
            </label>
          </div>
          {continuousEvolution && (
            <span className="text-xs text-green-600 font-medium">已启用</span>
          )}
        </div>

        {/* 品种分组 */}
        <div className="space-y-4">
          {Object.entries(SYMBOL_GROUPS).map(([key, group]) => (
            <SymbolGroup
              key={key}
              title={group.title}
              symbols={group.symbols}
              color={group.color}
              symbolList={symbolList}
              onStart={handleStart}
              onStop={handleStopSingle}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  )
}