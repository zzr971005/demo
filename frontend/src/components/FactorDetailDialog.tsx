import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ExpressionVisualizer } from './ExpressionVisualizer'
import { Eye, Activity, TrendingUp, AlertTriangle, CheckCircle } from 'lucide-react'
import type { LiveFactor } from '@/lib/api'

interface FactorDetailDialogProps {
  factor: LiveFactor
  trigger?: React.ReactNode
}

/**
 * 过拟合检验指示器
 */
function OverfittingBadge({
  pbo,
  dsr,
  wfe,
}: {
  pbo?: number
  dsr?: number
  wfe?: number
}) {
  const checks = [
    { label: 'PBO', value: pbo, threshold: 0.3, pass: pbo !== undefined ? pbo < 0.3 : undefined },
    { label: 'DSR', value: dsr, threshold: 0.6, pass: dsr !== undefined ? dsr > 0.6 : undefined },
    { label: 'WFE', value: wfe, threshold: 0.7, pass: wfe !== undefined ? wfe > 0.7 : undefined },
  ]

  return (
    <div className="flex items-center gap-2">
      {checks.map((check) => (
        <Badge
          key={check.label}
          variant={check.pass === true ? 'default' : check.pass === false ? 'destructive' : 'secondary'}
          className="text-xs"
        >
          {check.pass === true ? (
            <CheckCircle className="h-3 w-3 mr-1" />
          ) : check.pass === false ? (
            <AlertTriangle className="h-3 w-3 mr-1" />
          ) : null}
          {check.label}: {check.value !== undefined ? check.value.toFixed(2) : '-'}
        </Badge>
      ))}
    </div>
  )
}

/**
 * 性能指标卡片
 */
function MetricCard({
  label,
  value,
  unit = '',
  icon: Icon,
  trend,
}: {
  label: string
  value: number
  unit?: string
  icon: React.ElementType
  trend?: 'up' | 'down' | 'neutral'
}) {
  const trendColors = {
    up: 'text-green-500',
    down: 'text-red-500',
    neutral: 'text-gray-500',
  }

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">{label}</span>
          </div>
          {trend && (
            <span className={trendColors[trend]}>
              {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'}
            </span>
          )}
        </div>
        <div className="mt-2">
          <span className="text-2xl font-bold font-mono">
            {typeof value === 'number' ? value.toFixed(2) : value}
          </span>
          {unit && <span className="text-sm text-muted-foreground ml-1">{unit}</span>}
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * 因子详情弹窗
 */
export function FactorDetailDialog({ factor, trigger }: FactorDetailDialogProps) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="ghost" size="sm">
            <Eye className="h-4 w-4 mr-1" />
            详情
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            因子详情
            <Badge variant={factor.is_live ? 'default' : 'secondary'}>
              {factor.is_live ? '实盘' : '候选'}
            </Badge>
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* 基本信息 */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-sm text-muted-foreground">因子ID</span>
              <p className="font-mono text-sm">{factor.factor_id}</p>
            </div>
            <div>
              <span className="text-sm text-muted-foreground">品种</span>
              <p className="font-medium">{factor.symbol}</p>
            </div>
            <div>
              <span className="text-sm text-muted-foreground">进化世代</span>
              <p className="font-medium">第 {factor.generation} 代</p>
            </div>
            <div>
              <span className="text-sm text-muted-foreground">来源</span>
              <p className="font-medium capitalize">{factor.origin}</p>
            </div>
          </div>

          {/* 过拟合检验 */}
          <div>
            <h4 className="text-sm font-medium mb-2">过拟合检验</h4>
            <OverfittingBadge pbo={factor.pbo} dsr={factor.dsr} wfe={factor.wfe} />
          </div>

          {/* 性能指标 */}
          <div>
            <h4 className="text-sm font-medium mb-3">回测性能</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <MetricCard
                label="夏普比率"
                value={factor.sharpe_ratio}
                icon={TrendingUp}
                trend={factor.sharpe_ratio > 1.5 ? 'up' : factor.sharpe_ratio > 1.0 ? 'neutral' : 'down'}
              />
              <MetricCard
                label="最大回撤"
                value={factor.max_drawdown * 100}
                unit="%"
                icon={AlertTriangle}
                trend={factor.max_drawdown < 0.1 ? 'up' : factor.max_drawdown < 0.2 ? 'neutral' : 'down'}
              />
              <MetricCard
                label="总收益"
                value={factor.total_return * 100}
                unit="%"
                icon={TrendingUp}
                trend={factor.total_return > 0 ? 'up' : 'down'}
              />
              <MetricCard
                label="胜率"
                value={factor.win_rate * 100}
                unit="%"
                icon={Activity}
                trend={factor.win_rate > 0.55 ? 'up' : factor.win_rate > 0.45 ? 'neutral' : 'down'}
              />
            </div>
          </div>

          {/* 实盘性能（如果有） */}
          {factor.live_stats && (
            <div>
              <h4 className="text-sm font-medium mb-3">实盘性能</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <MetricCard
                  label="实盘夏普"
                  value={factor.live_stats.live_sharpe_ratio}
                  icon={TrendingUp}
                  trend={factor.live_stats.live_sharpe_ratio > factor.sharpe_ratio * 0.9 ? 'up' : 'down'}
                />
                <MetricCard
                  label="实盘收益"
                  value={factor.live_stats.live_total_return * 100}
                  unit="%"
                  icon={TrendingUp}
                  trend={factor.live_stats.live_total_return > 0 ? 'up' : 'down'}
                />
                <MetricCard
                  label="性能衰减"
                  value={factor.live_stats.performance_decay * 100}
                  unit="%"
                  icon={AlertTriangle}
                  trend={factor.live_stats.performance_decay < 0.1 ? 'up' : 'down'}
                />
                <MetricCard
                  label="运行天数"
                  value={factor.live_stats.days_running}
                  unit="天"
                  icon={Activity}
                />
              </div>
            </div>
          )}

          {/* 表达式可视化 */}
          <ExpressionVisualizer expression={factor.expression} />

          {/* 其他统计 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">其他统计</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">交易次数</span>
                  <p className="font-mono font-medium">{factor.total_trades}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">平均盈亏</span>
                  <p className="font-mono font-medium">{factor.avg_trade_pnl?.toFixed(2)}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">换手率</span>
                  <p className="font-mono font-medium">{(factor.turnover_rate * 100).toFixed(1)}%</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Calmar比率</span>
                  <p className="font-mono font-medium">{factor.calmar_ratio.toFixed(2)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export default FactorDetailDialog
