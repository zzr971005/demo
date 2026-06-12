import { Suspense, ReactNode } from 'react'
import { Loader2 } from 'lucide-react'

interface LazyLoadProps {
  children: ReactNode
  fallback?: ReactNode
}

export function LazyLoad({ children, fallback }: LazyLoadProps) {
  const defaultFallback = (
    <div className="flex h-full items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
    </div>
  )

  return (
    <Suspense fallback={fallback || defaultFallback}>
      {children}
    </Suspense>
  )
}
