import { cn } from '@/lib/utils'

type SymbolStatus = 'running' | 'paused' | 'stopped' | 'error' | 'idle' | 'OFF' | 'PAPER' | 'LIVE' | ''

interface SymbolBadgeProps {
  status: SymbolStatus
  className?: string
}

const statusConfig: Record<
  SymbolStatus,
  { label: string; bg: string; text: string; dot: string }
> = {
  running: {
    label: '运行中',
    bg: 'bg-green-500/10',
    text: 'text-green-500',
    dot: 'bg-green-500',
  },
  paused: {
    label: '已暂停',
    bg: 'bg-yellow-500/10',
    text: 'text-yellow-500',
    dot: 'bg-yellow-500',
  },
  stopped: {
    label: '已停止',
    bg: 'bg-slate-500/10',
    text: 'text-slate-500',
    dot: 'bg-slate-500',
  },
  error: {
    label: '异常',
    bg: 'bg-red-500/10',
    text: 'text-red-500',
    dot: 'bg-red-500',
  },
  idle: {
    label: '空闲',
    bg: 'bg-gray-500/10',
    text: 'text-gray-500',
    dot: 'bg-gray-500',
  },
  OFF: {
    label: '空闲',
    bg: 'bg-gray-500/10',
    text: 'text-gray-500',
    dot: 'bg-gray-500',
  },
  PAPER: {
    label: '运行中',
    bg: 'bg-green-500/10',
    text: 'text-green-500',
    dot: 'bg-green-500',
  },
  LIVE: {
    label: '实盘',
    bg: 'bg-orange-500/10',
    text: 'text-orange-500',
    dot: 'bg-orange-500',
  },
  '': {
    label: '空闲',
    bg: 'bg-gray-500/10',
    text: 'text-gray-500',
    dot: 'bg-gray-500',
  },
}

export default function SymbolBadge({ status, className }: SymbolBadgeProps) {
  const config = statusConfig[status] ?? statusConfig.stopped

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium',
        config.bg,
        config.text,
        className
      )}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', config.dot)} />
      {config.label}
    </span>
  )
}
