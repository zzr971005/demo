import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { AlertTriangle, CheckCircle2, XCircle, TrendingUp, TrendingDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { LiveConfirmData } from '@/hooks/useManualSwitch'

interface SwitchConfirmDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  data: LiveConfirmData | null
  onConfirm: () => void
  loading?: boolean
}

export default function SwitchConfirmDialog({
  open,
  onOpenChange,
  data,
  onConfirm,
  loading = false,
}: SwitchConfirmDialogProps) {
  if (!data) return null

  const safeSharpe20d = data.sharpe20d ?? 0
  const safeMaxDrawdown20d = data.maxDrawdown20d ?? 0

  const allPassed = data.selfChecks.every((c) => c.passed)
  const failedChecks = data.selfChecks.filter((c) => !c.passed)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-500" />
            LIVE 模式切换确认
          </DialogTitle>
          <DialogDescription>
            确认将 <span className="font-semibold text-foreground">{data.name} ({data.symbol})</span> 切换至实盘交易？
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* 近20日指标 */}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg border bg-muted/50 p-3">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <TrendingUp className="h-3.5 w-3.5" />
                近20日夏普
              </div>
              <div
                className={cn(
                  'mt-1 text-lg font-bold',
                  safeSharpe20d >= 2
                    ? 'text-green-500'
                    : safeSharpe20d >= 1
                      ? 'text-yellow-500'
                      : 'text-red-500'
                )}
              >
                {safeSharpe20d.toFixed(2)}
              </div>
            </div>
            <div className="rounded-lg border bg-muted/50 p-3">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <TrendingDown className="h-3.5 w-3.5" />
                近20日最大回撤
              </div>
              <div
                className={cn(
                  'mt-1 text-lg font-bold',
                  safeMaxDrawdown20d > -0.05
                    ? 'text-green-500'
                    : safeMaxDrawdown20d > -0.1
                      ? 'text-yellow-500'
                      : 'text-red-500'
                )}
              >
                {(safeMaxDrawdown20d * 100).toFixed(1)}%
              </div>
            </div>
          </div>

          {/* 自检结果 */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              自检结果
            </h4>
            <div className="space-y-1.5">
              {data.selfChecks.map((check) => (
                <div
                  key={check.name}
                  className={cn(
                    'flex items-center justify-between rounded-md border px-3 py-2',
                    check.passed
                      ? 'border-green-500/20 bg-green-500/5'
                      : 'border-red-500/20 bg-red-500/5'
                  )}
                >
                  <div className="flex items-center gap-2">
                    {check.passed ? (
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-500" />
                    )}
                    <span className="text-sm font-medium">{check.label}</span>
                  </div>
                  <span
                    className={cn(
                      'text-xs',
                      check.passed ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                    )}
                  >
                    {check.detail}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {!allPassed && (
            <div className="rounded-md border border-destructive/20 bg-destructive/5 p-3 text-sm text-destructive">
              <span className="font-semibold">无法切换：</span>
              {failedChecks.map((c) => c.label).join('、')} 未通过
            </div>
          )}
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            取消
          </Button>
          <Button
            variant="default"
            onClick={onConfirm}
            disabled={!allPassed || loading}
            className={cn(
              'bg-green-600 hover:bg-green-700 text-white',
              (!allPassed || loading) && 'opacity-50 cursor-not-allowed'
            )}
          >
            {loading ? '切换中...' : '确认切换 LIVE'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
