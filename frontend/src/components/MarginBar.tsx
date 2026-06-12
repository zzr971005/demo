import { cn } from '@/lib/utils'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

interface MarginBarProps {
  used: number | undefined | null
  total: number | undefined | null
  className?: string
}

export default function MarginBar({ used, total, className }: MarginBarProps) {
  const safeUsed = used ?? 0
  const safeTotal = total ?? 0
  const percent = safeTotal > 0 ? Math.min((safeUsed / safeTotal) * 100, 100) : 0

  const getColor = (p: number) => {
    if (p >= 90) return 'bg-destructive'
    if (p >= 70) return 'bg-yellow-500'
    return 'bg-green-500'
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className={cn('w-full space-y-1', className)}>
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>保证金</span>
              <span>{percent.toFixed(1)}%</span>
            </div>
            <div className="relative h-2 w-full overflow-hidden rounded-full bg-primary/20">
              <div
                className={cn('h-full transition-all duration-500', getColor(percent))}
                style={{ width: `${percent}%` }}
              />
            </div>
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <p className="text-xs">
            已用: {safeUsed.toLocaleString()} / 总额: {safeTotal.toLocaleString()}
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
