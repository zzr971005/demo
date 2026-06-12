import { useMemo, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from 'recharts'
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Activity,
  BarChart3,
  Layers,
  AlertTriangle,
  Info,
  AlertCircle,
  Zap,
  ArrowRight,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

import SymbolBadge from '@/components/SymbolBadge'
import SharpeDisplay from '@/components/SharpeDisplay'
import MarginBar from '@/components/MarginBar'
import { useSymbols } from '@/hooks/useSymbols'
import { useDashboard, type AlertLog } from '@/hooks/useDashboard'
import { cn, formatCurrency, formatNumber } from '@/lib/utils'

function MetricCard({
  title,
  value,
  sub,
  icon: Icon,
  trend,
  variant = 'default',
}: {
  title: string
  value: string
  sub?: string
  icon: React.ElementType
  trend?: 'up' | 'down' | 'neutral'
  variant?: 'default' | 'danger' | 'success'
}) {
  const variantStyles = {
    default: 'bg-card text-card-foreground',
    danger: 'bg-destructive/10 text-destructive border-destructive/20',
    success: 'bg-green-500/10 text-green-600 border-green-500/20',
  }

  return (
    <Card className={cn('border', variantStyles[variant])}>
      <CardContent className="flex items-center justify-between p-4">
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground">{title}</p>
          <p className="text-xl font-bold tabular-nums">{value}</p>
          {sub && <p className="text-xs text-muted-foreground">{sub}</p>}
        </div>
        <div className="flex flex-col items-end gap-1">
          <Icon className="h-5 w-5 text-muted-foreground" />
          {trend === 'up' && <TrendingUp className="h-4 w-4 text-green-500" />}
          {trend === 'down' && <TrendingDown className="h-4 w-4 text-red-500" />}
        </div>
      </CardContent>
    </Card>
  )
}

function SharpeSparkline({ values }: { values: number[] }) {
  const min = Math.min(...values, 0)
  const max = Math.max(...values, 0)
  const range = max - min || 1

  return (
    <svg className="h-6 w-20" viewBox="0 0 100 24" preserveAspectRatio="none">
      <polyline
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        points={values
          .map((v, i) => {
            const x = (i / (values.length - 1)) * 100
            const y = 24 - ((v - min) / range) * 24
            return `${x},${y}`
          })
          .join(' ')}
        className={cn(
          values[values.length - 1] >= 2
            ? 'text-green-500'
            : values[values.length - 1] >= 1
              ? 'text-yellow-500'
              : 'text-slate-400'
        )}
      />
    </svg>
  )
}

function SymbolCard({ symbol }: { symbol: ReturnType<typeof useSymbols>['symbols'][number] }) {
  const statusBorder: Record<string, string> = {
    running: 'border-green-500/30',
    paused: 'border-yellow-500/30',
    stopped: 'border-slate-500/30',
    error: 'border-red-500/30',
    idle: 'border-gray-500/30',
    OFF: 'border-gray-500/30',
    PAPER: 'border-green-500/30',
    LIVE: 'border-orange-500/30',
    '': 'border-gray-500/30',
  }

  return (
    <Card
      className={cn(
        'group relative overflow-hidden border transition-all hover:shadow-md',
        statusBorder[symbol.status] ?? statusBorder['']
      )}
    >
      <CardContent className="p-3">
        <div className="mb-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold">{symbol.symbol}</span>
            <SymbolBadge status={symbol.status} />
          </div>
          <SharpeSparkline values={symbol.sharpe5d} />
        </div>

        <p className="mb-2 text-xs text-muted-foreground truncate">{symbol.current_factor}</p>

        <div className="mb-2">
          <MarginBar used={symbol.margin_used} total={symbol.margin_total} />
        </div>

        <div className="flex items-center justify-between">
          <SharpeDisplay value={symbol.sharpe_ratio} />
          <div className="flex items-center gap-1">
            <span
              className={cn(
                'text-xs font-medium tabular-nums',
                symbol.pnl_daily >= 0 ? 'text-green-500' : 'text-red-500'
              )}
            >
              {symbol.pnl_daily >= 0 ? '+' : ''}
              {formatNumber(symbol.pnl_daily)}
            </span>
            <Link to={`/symbol/${symbol.symbol}`}>
              <Button variant="ghost" size="icon" className="h-6 w-6">
                <ArrowRight className="h-3 w-3" />
              </Button>
            </Link>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function AlertIcon({ level }: { level: AlertLog['level'] }) {
  switch (level) {
    case 'critical':
      return <Zap className="h-4 w-4 text-red-500" />
    case 'error':
      return <AlertCircle className="h-4 w-4 text-red-500" />
    case 'warning':
      return <AlertTriangle className="h-4 w-4 text-yellow-500" />
    default:
      return <Info className="h-4 w-4 text-blue-500" />
  }
}

function AlertBadge({ level }: { level: AlertLog['level'] }) {
  const config = {
    info: 'bg-blue-500/10 text-blue-500',
    warning: 'bg-yellow-500/10 text-yellow-500',
    error: 'bg-red-500/10 text-red-500',
    critical: 'bg-red-500/20 text-red-600',
  }
  return (
    <Badge variant="outline" className={cn('text-[10px]', config[level])}>
      {level === 'critical' ? '严重' : level === 'error' ? '错误' : level === 'warning' ? '警告' : '信息'}
    </Badge>
  )
}

function AlertLogList({ alerts }: { alerts: AlertLog[] }) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0
    }
  }, [alerts.length])

  return (
    <div
      ref={scrollRef}
      className="h-80 overflow-y-auto pr-2 space-y-2"
    >
      {alerts.length === 0 && (
        <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
          暂无告警
        </div>
      )}
      {alerts.map((alert) => (
        <div
          key={alert.id}
          className="flex items-start gap-3 rounded-md border bg-card/50 p-3 transition-colors hover:bg-accent/50"
        >
          <AlertIcon level={alert.level} />
          <div className="flex-1 space-y-1">
            <div className="flex items-center gap-2">
              <AlertBadge level={alert.level} />
              {alert.symbol && (
                <span className="text-xs font-medium text-muted-foreground">{alert.symbol}</span>
              )}
            </div>
            <p className="text-sm">{alert.message}</p>
            <p className="text-xs text-muted-foreground">
              {new Date(alert.timestamp).toLocaleString('zh-CN')}
            </p>
          </div>
        </div>
      ))}
    </div>
  )
}

export default function Dashboard() {
  const { symbols, runningCount, totalCount } = useSymbols()
  const { metrics, equityCurve, alerts } = useDashboard()

  const chartData = useMemo(() => {
    return equityCurve.map((d) => ({
      ...d,
      equityLabel: (d.equity / 10000).toFixed(2) + '万',
    }))
  }, [equityCurve])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">仪表盘</h1>
          <p className="text-sm text-muted-foreground">期货自动进化因子挖掘系统总览</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="gap-1">
            <Layers className="h-3 w-3" />
            {runningCount}/{totalCount} 运行中
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <MetricCard
          title="总资金"
          value={formatCurrency(metrics.totalEquity)}
          sub={`今日 ${metrics.todayPnl >= 0 ? '+' : ''}${formatNumber(metrics.todayPnl)}`}
          icon={DollarSign}
          trend={metrics.todayPnl >= 0 ? 'up' : 'down'}
        />
        <MetricCard
          title="今日收益"
          value={`${metrics.todayReturn >= 0 ? '+' : ''}${formatNumber(metrics.todayReturn)}%`}
          icon={TrendingUp}
          trend={metrics.todayReturn >= 0 ? 'up' : 'down'}
          variant={metrics.todayReturn < 0 ? 'danger' : 'success'}
        />
        <MetricCard
          title="最大回撤"
          value={`${formatNumber(metrics.maxDrawdown)}%`}
          icon={TrendingDown}
          variant="danger"
        />
        <MetricCard
          title="夏普比率"
          value={formatNumber(metrics.sharpeRatio)}
          icon={BarChart3}
          trend={metrics.sharpeRatio >= 1 ? 'up' : 'neutral'}
        />
        <MetricCard
          title="交易次数"
          value={String(metrics.totalTrades)}
          icon={Activity}
        />
        <MetricCard
          title="运行品种"
          value={`${metrics.runningSymbols}`}
          sub={`共 ${totalCount} 个品种`}
          icon={Layers}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">全局资金曲线</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="ddGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="hsl(var(--destructive))" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="hsl(var(--destructive))" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }}
                    axisLine={{ stroke: 'hsl(var(--border))' }}
                    tickLine={false}
                  />
                  <YAxis
                    yAxisId="left"
                    tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(v: number) => (v / 10000).toFixed(0) + '万'}
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(v: number) => v + '%'}
                  />
                  <RechartsTooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '0.5rem',
                      fontSize: '12px',
                    }}
                    labelStyle={{ color: 'hsl(var(--foreground))' }}
                  />
                  <Area
                    yAxisId="left"
                    type="monotone"
                    dataKey="equity"
                    stroke="hsl(var(--primary))"
                    fill="url(#equityGradient)"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4 }}
                  />
                  <Area
                    yAxisId="right"
                    type="monotone"
                    dataKey="drawdown"
                    stroke="hsl(var(--destructive))"
                    fill="url(#ddGradient)"
                    strokeWidth={1.5}
                    dot={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">实时告警</CardTitle>
          </CardHeader>
          <CardContent>
            <AlertLogList alerts={alerts} />
          </CardContent>
        </Card>
      </div>

      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold">品种矩阵</h2>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-green-500" />
              运行
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-yellow-500" />
              暂停
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-slate-500" />
              停止
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-red-500" />
              异常
            </span>
          </div>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
          {symbols.map((s) => (
            <SymbolCard key={s.symbol} symbol={s} />
          ))}
          {symbols.length === 0 && (
            <div className="col-span-full flex h-32 items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground">
              暂无品种数据
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
