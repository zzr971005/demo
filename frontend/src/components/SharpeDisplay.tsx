import { cn } from '@/lib/utils'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

interface SharpeDisplayProps {
  value: number | undefined | null
  className?: string
}

export default function SharpeDisplay({ value, className }: SharpeDisplayProps) {
  const safeValue = value ?? 0
  const getColor = (v: number) => {
    if (v >= 2) return 'text-green-500'
    if (v >= 1) return 'text-yellow-500'
    if (v >= 0) return 'text-slate-500'
    return 'text-red-500'
  }

  const getLabel = (v: number) => {
    if (v >= 2) return '优秀'
    if (v >= 1) return '良好'
    if (v >= 0) return '一般'
    return '差'
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className={cn('flex items-center gap-2', className)}>
            <span className="text-xs text-muted-foreground">夏普</span>
            <span className={cn('text-sm font-bold tabular-nums', getColor(safeValue))}>
              {safeValue.toFixed(2)}
            </span>
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <p className="text-xs">
            夏普比率: {safeValue.toFixed(3)} ({getLabel(safeValue)})
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
