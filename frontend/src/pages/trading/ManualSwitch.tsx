import { useState, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  OctagonAlert,
  FileText,
  Power,
  Activity,
  Loader2,
  Ban,
  AlertCircle,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useManualSwitch, type SymbolMode } from '@/hooks/useManualSwitch'
import SwitchConfirmDialog from '@/components/SwitchConfirmDialog'
import EmergencyStopDialog from '@/components/EmergencyStopDialog'

const MODES: { key: SymbolMode; label: string; color: string }[] = [
  { key: 'OFF', label: 'OFF', color: 'bg-slate-500 hover:bg-slate-600' },
  { key: 'PAPER', label: 'PAPER', color: 'bg-blue-500 hover:bg-blue-600' },
  { key: 'LIVE', label: 'LIVE', color: 'bg-green-500 hover:bg-green-600' },
]

export default function ManualSwitch() {
  const {
    symbols,
    loading,
    emergencyLoading,
    updateSymbolMode,
    getLiveConfirmData,
    batchSetMode,
    emergencyStop,
    marginInsufficientSymbols,
    liveSymbols,
    paperSymbols,
  } = useManualSwitch()

  const [confirmOpen, setConfirmOpen] = useState(false)
  const [emergencyOpen, setEmergencyOpen] = useState(false)
  const [pendingSymbol, setPendingSymbol] = useState<string | null>(null)
  const [batchLoading, setBatchLoading] = useState<SymbolMode | null>(null)

  const confirmData = pendingSymbol ? getLiveConfirmData(pendingSymbol) : null

  const handleModeClick = useCallback(
    (symbol: string, mode: SymbolMode) => {
      if (mode === 'LIVE') {
        setPendingSymbol(symbol)
        setConfirmOpen(true)
      } else {
        updateSymbolMode(symbol, mode)
      }
    },
    [updateSymbolMode, getLiveConfirmData]
  )

  const handleConfirmLive = useCallback(async () => {
    if (!pendingSymbol) return
    try {
      await updateSymbolMode(pendingSymbol, 'LIVE')
      setConfirmOpen(false)
      setPendingSymbol(null)
    } catch {
      // error handled in hook
    }
  }, [pendingSymbol, updateSymbolMode])

  const handleBatch = useCallback(
    async (mode: SymbolMode) => {
      setBatchLoading(mode)
      try {
        await batchSetMode(mode)
      } finally {
        setBatchLoading(null)
      }
    },
    [batchSetMode]
  )

  const handleEmergency = useCallback(async () => {
    try {
      await emergencyStop()
      setEmergencyOpen(false)
    } catch {
      // error handled in hook
    }
  }, [emergencyStop])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">手动切换</h1>
          <p className="text-muted-foreground">手动干预因子与策略状态</p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="secondary" className="gap-1">
            <Activity className="h-3 w-3 text-green-500" />
            LIVE: {liveSymbols.length}
          </Badge>
          <Badge variant="secondary" className="gap-1">
            <FileText className="h-3 w-3 text-blue-500" />
            PAPER: {paperSymbols.length}
          </Badge>
          {marginInsufficientSymbols.length > 0 && (
            <Badge variant="destructive" className="gap-1">
              <AlertCircle className="h-3 w-3" />
              保证金不足: {marginInsufficientSymbols.length}
            </Badge>
          )}
        </div>
      </div>

      {/* Batch Actions + Emergency Stop */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-card p-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-muted-foreground">批量操作:</span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleBatch('PAPER')}
            disabled={batchLoading !== null}
            className="gap-1.5"
          >
            {batchLoading === 'PAPER' ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <FileText className="h-3.5 w-3.5 text-blue-500" />
            )}
            全部 Paper
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleBatch('OFF')}
            disabled={batchLoading !== null}
            className="gap-1.5"
          >
            {batchLoading === 'OFF' ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Power className="h-3.5 w-3.5 text-slate-500" />
            )}
            全部 OFF
          </Button>
        </div>

        <Button
          variant="destructive"
          size="sm"
          onClick={() => setEmergencyOpen(true)}
          disabled={emergencyLoading}
          className="gap-1.5"
        >
          {emergencyLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <OctagonAlert className="h-4 w-4" />
          )}
          全局熔断
        </Button>
      </div>

      {/* Symbol Switch Matrix */}
      <div className="rounded-xl border bg-card">
        <div className="flex items-center gap-4 border-b px-4 py-3">
          <span className="w-20 text-xs font-semibold uppercase tracking-wider text-muted-foreground">品种</span>
          <span className="w-16 text-xs font-semibold uppercase tracking-wider text-muted-foreground">状态</span>
          <span className="flex-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">模式切换</span>
          <span className="w-24 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">夏普(20d)</span>
          <span className="w-28 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">保证金</span>
          <span className="w-16 text-center text-xs font-semibold uppercase tracking-wider text-muted-foreground">禁用</span>
        </div>

        <div className="divide-y">
          {symbols.map((item) => {
            const isLoading = loading[item.symbol]
            const isDisabled = item.isMarginInsufficient
            const marginPct = item.marginTotal > 0 ? (item.marginUsed / item.marginTotal) * 100 : 0

            return (
              <div
                key={item.symbol}
                className={cn(
                  'flex items-center gap-4 px-4 py-3 transition-colors',
                  isDisabled && 'bg-muted/30'
                )}
              >
                {/* Symbol */}
                <div className="w-20">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold">{item.symbol}</span>
                    <span className="text-xs text-muted-foreground">{item.name}</span>
                  </div>
                </div>

                {/* Current Status Badge */}
                <div className="w-16">
                  <span
                    className={cn(
                      'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
                      item.mode === 'LIVE' && 'bg-green-500/10 text-green-500',
                      item.mode === 'PAPER' && 'bg-blue-500/10 text-blue-500',
                      item.mode === 'OFF' && 'bg-slate-500/10 text-slate-500'
                    )}
                  >
                    <span
                      className={cn(
                        'mr-1 h-1.5 w-1.5 rounded-full',
                        item.mode === 'LIVE' && 'bg-green-500',
                        item.mode === 'PAPER' && 'bg-blue-500',
                        item.mode === 'OFF' && 'bg-slate-500'
                      )}
                    />
                    {item.mode}
                  </span>
                </div>

                {/* Mode Buttons */}
                <div className="flex flex-1 items-center gap-1">
                  {MODES.map((mode) => {
                    const active = item.mode === mode.key
                    return (
                      <button
                        key={mode.key}
                        onClick={() => handleModeClick(item.symbol, mode.key)}
                        disabled={isDisabled || isLoading}
                        className={cn(
                          'relative rounded-md px-3 py-1.5 text-xs font-semibold transition-all',
                          active
                            ? `${mode.color} text-white shadow`
                            : 'bg-muted text-muted-foreground hover:bg-muted/80',
                          (isDisabled || isLoading) && 'cursor-not-allowed opacity-40'
                        )}
                      >
                        {isLoading && active ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          mode.label
                        )}
                      </button>
                    )
                  })}
                </div>

                {/* Sharpe */}
                <div className="w-24 text-right">
                  <span
                    className={cn(
                      'text-sm font-bold tabular-nums',
                      item.sharpe20d >= 2
                        ? 'text-green-500'
                        : item.sharpe20d >= 1
                          ? 'text-yellow-500'
                          : 'text-red-500'
                    )}
                  >
                    {item.sharpe20d.toFixed(2)}
                  </span>
                </div>

                {/* Margin */}
                <div className="w-28">
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div className="space-y-1">
                          <div className="flex justify-between text-xs text-muted-foreground">
                            <span>{marginPct.toFixed(0)}%</span>
                          </div>
                          <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-primary/10">
                            <div
                              className={cn(
                                'h-full transition-all duration-500',
                                marginPct >= 90
                                  ? 'bg-destructive'
                                  : marginPct >= 70
                                    ? 'bg-yellow-500'
                                    : 'bg-green-500'
                              )}
                              style={{ width: `${Math.min(marginPct, 100)}%` }}
                            />
                          </div>
                        </div>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="text-xs">
                          已用: {item.marginUsed.toLocaleString()} / 总额: {item.marginTotal.toLocaleString()}
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>

                {/* Disabled Indicator */}
                <div className="flex w-16 justify-center">
                  {isDisabled ? (
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Ban className="h-4 w-4 text-destructive" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="text-xs">保证金不足，已禁用LIVE切换</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  ) : (
                    <Switch
                      size="sm"
                      checked={item.mode !== 'OFF'}
                      onCheckedChange={(checked) => {
                        if (checked && item.mode === 'OFF') {
                          handleModeClick(item.symbol, 'PAPER')
                        } else if (!checked && item.mode !== 'OFF') {
                          handleModeClick(item.symbol, 'OFF')
                        }
                      }}
                      disabled={isLoading}
                      className="data-[state=checked]:bg-primary"
                    />
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-green-500" />
          LIVE - 实盘交易
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-blue-500" />
          PAPER - 模拟交易
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-slate-500" />
          OFF - 停止
        </div>
        <div className="flex items-center gap-1.5">
          <Ban className="h-3 w-3 text-destructive" />
          保证金不足品种已禁用
        </div>
      </div>

      {/* Dialogs */}
      <SwitchConfirmDialog
        open={confirmOpen}
        onOpenChange={(open) => {
          setConfirmOpen(open)
          if (!open) setPendingSymbol(null)
        }}
        data={confirmData}
        onConfirm={handleConfirmLive}
        loading={pendingSymbol ? loading[pendingSymbol] : false}
      />

      <EmergencyStopDialog
        open={emergencyOpen}
        onOpenChange={setEmergencyOpen}
        onConfirm={handleEmergency}
        loading={emergencyLoading}
      />
    </div>
  )
}
