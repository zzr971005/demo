import { useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  LineChart,
  Line,
} from 'recharts'
import {
  Activity,
  TrendingUp,
  TrendingDown,
  Minus,
  Signal,
  History,
  BarChart3,
  Scale,
  RefreshCw,
  Clock,
  DollarSign,
  Target,
  Shield,
} from 'lucide-react'
import { useSymbolDetail, type StrategyStatus } from '@/hooks/useSymbolDetail'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { cn, formatNumber } from '@/lib/utils'

const statusConfig: Record<
  StrategyStatus,
  { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }
> = {
  RUNNING: { label: '运行中', variant: 'default' },
  PAPER: { label: '模拟', variant: 'secondary' },
  SEED: { label: '种子', variant: 'outline' },
}

function SignalBadge({ direction }: { direction: string }) {
  if (direction === 'LONG')
    return (
      <Badge className="bg-red-500/10 text-red-500 hover:bg-red-500/20">
        <TrendingUp className="mr-1 h-3 w-3" />
        多
      </Badge>
    )
  if (direction === 'SHORT')
    return (
      <Badge className="bg-green-500/10 text-green-500 hover:bg-green-500/20">
        <TrendingDown className="mr-1 h-3 w-3" />
        空
      </Badge>
    )
  return (
    <Badge variant="outline">
      <Minus className="mr-1 h-3 w-3" />
      平
    </Badge>
  )
}

function PositionCard({ position }: { position: import('@/hooks/useSymbolDetail').PositionInfo | null }) {
  if (!position || position.direction === 'FLAT') {
    return (
      <div className="flex h-32 items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground">
        当前无持仓
      </div>
    )
  }

  const isLong = position.direction === 'LONG'
  const pnlColor = position.unrealizedPnl >= 0 ? 'text-green-500' : 'text-red-500'

  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Scale className="h-4 w-4 text-primary" />
          <span className="text-sm font-semibold">当前持仓</span>
        </div>
        <Badge className={isLong ? 'bg-red-500/10 text-red-500' : 'bg-green-500/10 text-green-500'}>
          {isLong ? '多' : '空'} {position.volume}手
        </Badge>
      </div>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <div className="text-xs text-muted-foreground">开仓价</div>
          <div className="font-mono font-medium">{formatNumber(position.openPrice)}</div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground">最新价</div>
          <div className="font-mono font-medium">{formatNumber(position.currentPrice)}</div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground">浮动盈亏</div>
          <div className={cn('font-mono font-medium', pnlColor)}>
            {position.unrealizedPnl >= 0 ? '+' : ''}
            {formatNumber(position.unrealizedPnl)}
          </div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground">占用保证金</div>
          <div className="font-mono font-medium">{formatNumber(position.marginUsed)}</div>
        </div>
      </div>
    </div>
  )
}

function StrategyList({
  strategies,
  selectedId,
  onSelect,
}: {
  strategies: import('@/hooks/useSymbolDetail').SymbolStrategy[]
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  if (strategies.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
        暂无策略
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {strategies.map((s) => {
        const cfg = statusConfig[s.status]
        return (
          <button
            key={s.candidate_id}
            onClick={() => onSelect(s.candidate_id)}
            className={cn(
              'flex w-full items-center justify-between rounded-md border px-3 py-2 text-left text-sm transition-colors',
              selectedId === s.candidate_id
                ? 'border-primary bg-primary/5'
                : 'border-border bg-card hover:bg-accent'
            )}
          >
            <div className="flex flex-col gap-0.5">
              <span className="font-mono font-medium">
                {s.factor_info?.name ?? s.candidate_id.slice(0, 8)}
              </span>
              <span className="text-xs text-muted-foreground">{s.template}</span>
            </div>
            <div className="flex flex-col items-end gap-0.5">
              <Badge variant={cfg.variant}>{cfg.label}</Badge>
              {typeof s.sharpe_5d === 'number' && (
                <span className="font-mono text-xs text-muted-foreground">
                  S={formatNumber(s.sharpe_5d)}
                </span>
              )}
            </div>
          </button>
        )
      })}
    </div>
  )
}

export default function SymbolDetail() {
  const { symbol } = useParams<{ symbol: string }>()
  const safeSymbol = symbol ?? ''
  const [statusFilter, setStatusFilter] = useState<StrategyStatus | 'ALL'>('ALL')
  const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(null)

  const {
    signals,
    position,
    trades,
    regimeRadarData,
    backtestLive,
    loading,
    error,
    refresh,
    filteredStrategies,
  } = useSymbolDetail(safeSymbol)

  const displayedStrategies = filteredStrategies(statusFilter)

  const backtestData = backtestLive.map((b) => ({
    metric: b.metric,
    回测: Number((b.backtest * (b.metric === '夏普比率' || b.metric === '盈亏比' ? 1 : 100)).toFixed(2)),
    实盘: Number((b.live * (b.metric === '夏普比率' || b.metric === '盈亏比' ? 1 : 100)).toFixed(2)),
  }))

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Activity className="h-6 w-6 text-primary" />
            品种详情: {safeSymbol}
          </h1>
          <p className="text-muted-foreground">品种运行状态与因子表现</p>
        </div>
        <Button variant="outline" size="sm" onClick={refresh} disabled={loading}>
          <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
        </Button>
      </div>

      {error && (
        <div className="rounded-md border border-destructive bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="space-y-4">
          <div className="rounded-lg border bg-card p-4">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <Target className="h-4 w-4 text-primary" />
                策略列表
              </div>
              <div className="flex gap-1">
                {(['ALL', 'RUNNING', 'PAPER', 'SEED'] as const).map((s) => (
                  <Button
                    key={s}
                    variant={statusFilter === s ? 'default' : 'ghost'}
                    size="sm"
                    className="h-7 px-2 text-xs"
                    onClick={() => setStatusFilter(s)}
                  >
                    {s === 'ALL' ? '全部' : statusConfig[s].label}
                  </Button>
                ))}
              </div>
            </div>
            <StrategyList
              strategies={displayedStrategies}
              selectedId={selectedStrategyId}
              onSelect={setSelectedStrategyId}
            />
          </div>

          <PositionCard position={position} />
        </div>

        <div className="lg:col-span-2 space-y-4">
          <Tabs defaultValue="signals" className="w-full">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="signals" className="gap-1">
                <Signal className="h-4 w-4" />
                信号
              </TabsTrigger>
              <TabsTrigger value="trades" className="gap-1">
                <History className="h-4 w-4" />
                交易记录
              </TabsTrigger>
              <TabsTrigger value="regime" className="gap-1">
                <BarChart3 className="h-4 w-4" />
                Regime
              </TabsTrigger>
              <TabsTrigger value="baseline" className="gap-1">
                <Shield className="h-4 w-4" />
                研究基线
              </TabsTrigger>
            </TabsList>

            <TabsContent value="signals" className="mt-4 space-y-4">
              <div className="rounded-lg border bg-card p-4">
                <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
                  <Signal className="h-4 w-4 text-primary" />
                  当前信号
                </div>
                {signals.length > 0 ? (
                  <div className="space-y-2">
                    {signals.slice(0, 5).map((sig) => (
                      <div
                        key={sig.id}
                        className="flex items-center justify-between rounded-md border border-border bg-accent/30 px-3 py-2 text-sm"
                      >
                        <div className="flex items-center gap-3">
                          <SignalBadge direction={sig.direction} />
                          <span className="font-mono text-xs text-muted-foreground">
                            {sig.factor_name}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-muted-foreground">
                          <span>强度: {formatNumber(sig.strength)}</span>
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {new Date(sig.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex h-24 items-center justify-center text-sm text-muted-foreground">
                    暂无信号
                  </div>
                )}
              </div>

              <div className="rounded-lg border bg-card p-4">
                <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
                  <History className="h-4 w-4 text-primary" />
                  信号历史
                </div>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={signals
                        .slice()
                        .reverse()
                        .map((s, i) => ({
                          idx: i + 1,
                          strength: s.strength,
                          direction: s.direction,
                        }))}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="idx" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                      <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} domain={[0, 1]} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'hsl(var(--card))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '0.5rem',
                        }}
                      />
                      <Line
                        type="stepAfter"
                        dataKey="strength"
                        name="信号强度"
                        stroke="#3b82f6"
                        strokeWidth={2}
                        dot={{ r: 3 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="trades" className="mt-4">
              <div className="rounded-lg border bg-card p-4">
                <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
                  <DollarSign className="h-4 w-4 text-primary" />
                  交易记录
                </div>
                {trades.length > 0 ? (
                  <div className="max-h-96 overflow-auto">
                    <table className="w-full text-sm">
                      <thead className="sticky top-0 bg-card">
                        <tr className="border-b text-left text-xs text-muted-foreground">
                          <th className="pb-2 pr-4">时间</th>
                          <th className="pb-2 pr-4">方向</th>
                          <th className="pb-2 pr-4">价格</th>
                          <th className="pb-2 pr-4">手数</th>
                          <th className="pb-2">盈亏</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {trades.map((t) => (
                          <tr key={t.id} className="text-xs">
                            <td className="py-2 pr-4 font-mono text-muted-foreground">
                              {new Date(t.timestamp).toLocaleString()}
                            </td>
                            <td className="py-2 pr-4">
                              <SignalBadge direction={t.direction} />
                            </td>
                            <td className="py-2 pr-4 font-mono">{formatNumber(t.price)}</td>
                            <td className="py-2 pr-4 font-mono">{t.volume}</td>
                            <td className={cn('py-2 font-mono font-medium', t.pnl >= 0 ? 'text-green-500' : 'text-red-500')}>
                              {t.pnl >= 0 ? '+' : ''}
                              {formatNumber(t.pnl)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
                    暂无交易记录
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="regime" className="mt-4">
              <div className="rounded-lg border bg-card p-4">
                <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
                  <BarChart3 className="h-4 w-4 text-primary" />
                  市场状态雷达
                </div>
                {regimeRadarData.length > 0 ? (
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <RadarChart data={regimeRadarData}>
                        <PolarGrid stroke="hsl(var(--border))" />
                        <PolarAngleAxis
                          dataKey="subject"
                          tick={{ fill: 'hsl(var(--foreground))', fontSize: 12 }}
                        />
                        <PolarRadiusAxis
                          angle={30}
                          domain={[0, 100]}
                          tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }}
                        />
                        <Radar
                          name="当前状态"
                          dataKey="A"
                          stroke="#3b82f6"
                          fill="#3b82f6"
                          fillOpacity={0.3}
                          strokeWidth={2}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: 'hsl(var(--card))',
                            border: '1px solid hsl(var(--border))',
                            borderRadius: '0.5rem',
                          }}
                        />
                      </RadarChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
                    暂无Regime数据
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="baseline" className="mt-4 space-y-4">
              <div className="rounded-lg border bg-card p-4">
                <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
                  <Shield className="h-4 w-4 text-primary" />
                  回测 vs 实盘对比
                </div>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={backtestData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="metric" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                      <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'hsl(var(--card))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '0.5rem',
                        }}
                      />
                      <Legend />
                      <Bar dataKey="回测" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="实盘" fill="#10b981" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="rounded-lg border bg-card p-4">
                <div className="mb-3 text-sm font-semibold">偏差分析</div>
                <div className="space-y-2">
                  {backtestLive.map((b) => {
                    const diff = b.live - b.backtest
                    const isWorse =
                      (b.metric === '最大回撤' && diff > 0) ||
                      (b.metric !== '最大回撤' && diff < 0)
                    return (
                      <div
                        key={b.metric}
                        className="flex items-center justify-between rounded-md bg-accent/30 px-3 py-2 text-sm"
                      >
                        <span className="text-muted-foreground">{b.metric}</span>
                        <div className="flex items-center gap-3">
                          <span className="font-mono text-xs">
                            回测 {formatNumber(b.backtest)}
                          </span>
                          <span className="font-mono text-xs">
                            实盘 {formatNumber(b.live)}
                          </span>
                          <Badge
                            variant="outline"
                            className={cn(
                              'font-mono text-xs',
                              isWorse ? 'text-red-500 border-red-500/30' : 'text-green-500 border-green-500/30'
                            )}
                          >
                            {diff >= 0 ? '+' : ''}
                            {formatNumber(diff)}
                          </Badge>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  )
}
