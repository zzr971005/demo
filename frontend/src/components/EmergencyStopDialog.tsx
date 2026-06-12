import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogAction,
  AlertDialogCancel,
} from '@/components/ui/alert-dialog'
import { OctagonAlert, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface EmergencyStopDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: () => void
  loading?: boolean
}

export default function EmergencyStopDialog({
  open,
  onOpenChange,
  onConfirm,
  loading = false,
}: EmergencyStopDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogMedia className="bg-destructive/10">
            {loading ? (
              <Loader2 className="h-6 w-6 animate-spin text-destructive" />
            ) : (
              <OctagonAlert className="h-6 w-6 text-destructive" />
            )}
          </AlertDialogMedia>
          <AlertDialogTitle className="text-destructive">紧急停止确认</AlertDialogTitle>
          <AlertDialogDescription>
            此操作将立即<strong>终止所有品种的交易</strong>，并将所有状态重置为 OFF。
            <br /><br />
            该操作不可逆，请仅在紧急情况下使用。
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={loading}>取消</AlertDialogCancel>
          <AlertDialogAction
            onClick={(e) => {
              e.preventDefault()
              onConfirm()
            }}
            disabled={loading}
            className={cn(
              'bg-destructive text-destructive-foreground hover:bg-destructive/90',
              loading && 'opacity-70'
            )}
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                停止中...
              </>
            ) : (
              '确认紧急停止'
            )}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
