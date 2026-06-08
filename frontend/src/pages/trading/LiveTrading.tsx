import { useState, useCallback } from 'react'
import { useLiveTrading } from '@/hooks/useLiveTrading'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Activity,
  Play,
  Square,
  Star,
  AlertTriangle,
  RefreshCw,
  Clock,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { FactorDetailDialog } from '@/components/FactorDetailDialog'

const symbols = [
  { value: 'RB', label: '螺纹钢 (RB)' },
  { value: 'HC', label: '热卷 (HC)' },
  { value: 'I', label: '铁矿石 (I)' },
  { value: 'J', label: '焦炭 (J)' },
  { value: 'JM', label: '焦煤 (JM)' },
]

// 性能衰减指示器
function DecayIndicator({ decay }: { decay: number }) {
  if (decay >= -0.1) {
    return <Badge variant="default" className="bg-green-500">优秀</Badge>
  } else if (decay >= -0.3) {
    return <Badge variant="default" className="bg-yellow-500">良好</Badge>
  } else if (decay >= -0.5) {
    return <Badge variant="default" className="bg-orange-500">一般</Badge>
  } else {
    return <Badge variant="destructive">衰减严重</Badge>
  }
}

// 夏普比率指示器
function SharpeIndicator({ sharpe }: { sharpe: number }) {
  if (sharpe >= 1.5) {
    return <Badge variant="default" className="bg-green-500">{sharpe.toFixed(2)}</Badge>
  } else if (sharpe >= 1.0) {
    return <Badge variant="default" className="bg-blue-500">{sharpe.toFixed(2)}</Badge>
  } else if (sharpe >= 0.5) {
    return <Badge variant="default" className="bg-yellow-500">{sharpe.toFixed(2)}</Badge>
  } else {
    return <Badge variant="secondary">{sharpe.toFixed(2)}</Badge>
  }
}

// 实盘因子表格
function LiveFactorsTable({
  factors,
  loading,
  error,
  onRemove,
  removingId,
}: {
  factors: ReturnType<typeof useLiveTrading>['liveFactors']
  loading: boolean
  error: string | null
  onRemove: (factorId: string) => void
  removingId: string | null
}) {
  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    )
  }

  if (factors.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <Activity className="h-12 w-12 mx-auto mb-4 opacity-50" />
        <p>暂无实盘因子</p>
        <p className="text-sm">从候选因子中部署因子开始实盘交易</p>
      </div>
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>因子ID</TableHead>
          <TableHead>品种</TableHead>
          <TableHead>回测夏普</TableHead>
          <TableHead>实盘夏普</TableHead>
          <TableHead>衰减度</TableHead>
          <TableHead>运行天数</TableHead>
          <TableHead>状态</TableHead>
          <TableHead className="text-right">操作</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {factors.map((factor) => (
          <TableRow key={factor.factor_id}>
            <TableCell className="font-mono text-xs">
              {factor.factor_id.slice(-8)}
            </TableCell>
            <TableCell>{factor.symbol}</TableCell>
            <TableCell>
              <SharpeIndicator sharpe={factor.sharpe_ratio} />
            </TableCell>
            <TableCell>
              {factor.live_stats ? (
                <SharpeIndicator sharpe={factor.live_stats.live_sharpe_ratio} />
              ) : (
                <span className="text-muted-foreground">-</span>
              )}
            </TableCell>
            <TableCell>
              {factor.live_stats ? (
                <DecayIndicator decay={factor.live_stats.performance_decay} />
              ) : (
                <span className="text-muted-foreground">-</span>
              )}
            </TableCell>
            <TableCell>
              {factor.live_stats ? (
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {factor.live_stats.days_running} 天
                </span>
              ) : (
                <span className="text-muted-foreground">-</span>
              )}
            </TableCell>
            <TableCell>
              {factor.is_live ? (
                <Badge variant="default" className="bg-green-500">
                  <Activity className="h-3 w-3 mr-1" />
                  实盘运行
                </Badge>
              ) : (
                <Badge variant="secondary">已停止</Badge>
              )}
            </TableCell>
            <TableCell className="text-right">
              <div className="flex items-center justify-end gap-2">
                <FactorDetailDialog factor={factor} />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onRemove(factor.factor_id)}
                  disabled={removingId === factor.factor_id}
                >
                  {removingId === factor.factor_id ? (
                    <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
                  ) : (
                    <Square className="h-3 w-3 mr-1" />
                  )}
                  下线
                </Button>
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

// 候选因子表格
function CandidateFactorsTable({
  factors,
  loading,
  error,
  onDeploy,
  deployingId,
}: {
  factors: ReturnType<typeof useLiveTrading>['candidateFactors']
  loading: boolean
  error: string | null
  onDeploy: (factorId: string) => void
  deployingId: string | null
}) {
  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    )
  }

  if (factors.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <Star className="h-12 w-12 mx-auto mb-4 opacity-50" />
        <p>暂无候选因子</p>
        <p className="text-sm">从进化中心生成因子并标记为候选</p>
      </div>
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>因子ID</TableHead>
          <TableHead>品种</TableHead>
          <TableHead>表达式</TableHead>
          <TableHead>夏普比率</TableHead>
          <TableHead>最大回撤</TableHead>
          <TableHead>过拟合检验</TableHead>
          <TableHead className="text-right">操作</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {factors.map((factor) => (
          <TableRow key={factor.factor_id}>
            <TableCell className="font-mono text-xs">
              {factor.factor_id.slice(-8)}
            </TableCell>
            <TableCell>{factor.symbol}</TableCell>
            <TableCell className="max-w-xs truncate" title={factor.expression}>
              {factor.expression}
            </TableCell>
            <TableCell>
              <SharpeIndicator sharpe={factor.sharpe_ratio} />
            </TableCell>
            <TableCell>
              <span className={cn(
                factor.max_drawdown > 0.2 ? 'text-red-500' :
                factor.max_drawdown > 0.1 ? 'text-yellow-500' : 'text-green-500'
              )}>
                {(factor.max_drawdown * 100).toFixed(1)}%
              </span>
            </TableCell>
            <TableCell>
              {factor.overfitting_passed ? (
                <Badge variant="default" className="bg-green-500">
                  通过
                </Badge>
              ) : (
                <Badge variant="destructive">未通过</Badge>
              )}
            </TableCell>
            <TableCell className="text-right">
              <div className="flex items-center justify-end gap-2">
                <FactorDetailDialog factor={factor} />
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => onDeploy(factor.factor_id)}
                  disabled={deployingId === factor.factor_id || !factor.overfitting_passed}
                >
                  {deployingId === factor.factor_id ? (
                    <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
                  ) : (
                    <Play className="h-3 w-3 mr-1" />
                  )}
                  上线
                </Button>
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

// 性能汇总卡片
function PerformanceSummary({
  summary,
  loading,
}: {
  summary: ReturnType<typeof useLiveTrading>['summary']
  loading: boolean
}) {
  if (loading || !summary) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
    )
  }

  const avgSharpe = summary.avg_live_sharpe ?? 0
  const avgReturn = summary.avg_live_return ?? 0
  const positiveSharpeRatio = summary.positive_sharpe_ratio ?? 0

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <Card>
        <CardHeader className="pb-2">
          <CardDescription>实盘因子数</CardDescription>
          <CardTitle className="text-3xl">{summary.count}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">
            正在实盘交易的因子数量
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardDescription>平均实盘夏普</CardDescription>
          <CardTitle className={cn(
            "text-3xl",
            avgSharpe >= 1 ? 'text-green-500' :
            avgSharpe >= 0.5 ? 'text-yellow-500' : 'text-red-500'
          )}>
            {avgSharpe.toFixed(2)}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">
            所有实盘因子的平均夏普比率
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardDescription>平均收益</CardDescription>
          <CardTitle className={cn(
            "text-3xl",
            avgReturn >= 0 ? 'text-green-500' : 'text-red-500'
          )}>
            {(avgReturn * 100).toFixed(1)}%
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">
            所有实盘因子的平均收益率
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardDescription>正夏普比率</CardDescription>
          <CardTitle className="text-3xl">
            {(positiveSharpeRatio * 100).toFixed(0)}%
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">
            夏普比率大于0的因子占比
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

// 主页面
export default function LiveTrading() {
  const [selectedSymbol, setSelectedSymbol] = useState<string>('all')
  const [activeTab, setActiveTab] = useState('live')

  const {
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
    deployingId,
    removingId,
  } = useLiveTrading(selectedSymbol === 'all' ? undefined : selectedSymbol)

  const handleRefresh = useCallback(() => {
    refreshLiveFactors()
    refreshCandidateFactors()
    refreshSummary()
  }, [refreshLiveFactors, refreshCandidateFactors, refreshSummary])

  const handleDeploy = useCallback(async (factorId: string) => {
    try {
      await deployFactor(factorId)
    } catch (err) {
      // 错误已在hook中处理
    }
  }, [deployFactor])

  const handleRemove = useCallback(async (factorId: string) => {
    try {
      await removeFactor(factorId)
    } catch (err) {
      // 错误已在hook中处理
    }
  }, [removeFactor])

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Activity className="h-6 w-6 text-primary" />
            实盘监控
          </h1>
          <p className="text-muted-foreground">管理实盘交易因子，监控实盘性能</p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={selectedSymbol} onValueChange={setSelectedSymbol}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="所有品种" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">所有品种</SelectItem>
              {symbols.map((s) => (
                <SelectItem key={s.value} value={s.value}>
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={handleRefresh}>
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      {/* 性能汇总 */}
      <PerformanceSummary summary={summary} loading={summaryLoading} />

      {/* 因子列表 */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="live">
            <Activity className="h-4 w-4 mr-2" />
            实盘因子 ({liveFactors.length})
          </TabsTrigger>
          <TabsTrigger value="candidates">
            <Star className="h-4 w-4 mr-2" />
            候选因子 ({candidateFactors.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="live">
          <Card>
            <CardHeader>
              <CardTitle>实盘运行中的因子</CardTitle>
              <CardDescription>
                当前正在实盘交易的因子列表，包含实盘性能统计
              </CardDescription>
            </CardHeader>
            <CardContent>
              <LiveFactorsTable
                factors={liveFactors}
                loading={liveFactorsLoading}
                error={liveFactorsError}
                onRemove={handleRemove}
                removingId={removingId}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="candidates">
          <Card>
            <CardHeader>
              <CardTitle>候选因子池</CardTitle>
              <CardDescription>
                已通过过拟合检验的候选因子，可以部署到实盘
              </CardDescription>
            </CardHeader>
            <CardContent>
              <CandidateFactorsTable
                factors={candidateFactors}
                loading={candidateFactorsLoading}
                error={candidateFactorsError}
                onDeploy={handleDeploy}
                deployingId={deployingId}
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
