import { useState } from 'react'
import { Database, Clock, CheckCircle, AlertTriangle, RefreshCw, Trash2, Play } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useCacheManagement } from '@/hooks/useCacheManagement'
import { cn } from '@/lib/utils'

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'pass':
    case 'correct':
    case 'normal':
    case 'running':
      return <CheckCircle className="h-4 w-4 text-green-500" />
    case 'warn':
    case 'abnormal':
      return <AlertTriangle className="h-4 w-4 text-yellow-500" />
    case 'fail':
    case 'error':
    case 'missing':
      return <AlertTriangle className="h-4 w-4 text-red-500" />
    default:
      return <AlertTriangle className="h-4 w-4 text-gray-500" />
  }
}

function QualityBadge({ quality }: { quality: string }) {
  const config = {
    correct: 'bg-green-500/10 text-green-500',
    abnormal: 'bg-yellow-500/10 text-yellow-500',
    error: 'bg-red-500/10 text-red-500',
  }
  const label = {
    correct: '正确',
    abnormal: '异常',
    error: '错误',
  }
  return (
    <Badge variant="outline" className={cn('text-[10px]', config[quality as keyof typeof config])}>
      {label[quality as keyof typeof label] || quality}
    </Badge>
  )
}

function StatusBadge({ status }: { status: string }) {
  const config = {
    normal: 'bg-green-500/10 text-green-500',
    expired: 'bg-yellow-500/10 text-yellow-500',
    missing: 'bg-red-500/10 text-red-500',
    error: 'bg-red-500/10 text-red-500',
  }
  const label = {
    normal: '正常',
    expired: '过期',
    missing: '缺失',
    error: '错误',
  }
  return (
    <Badge variant="outline" className={cn('text-[10px]', config[status as keyof typeof config])}>
      {label[status as keyof typeof label] || status}
    </Badge>
  )
}

export default function DataCacheManagement() {
  const {
    status,
    symbols,
    history,
    quality,
    scheduler,
    loading,
    error,
    refreshAll,
    triggerUpdate,
    triggerScheduler,
    deleteCache,
    cleanupExpired,
  } = useCacheManagement()

  const [updating, setUpdating] = useState(false)

  const handleIncrementalUpdate = async () => {
    try {
      setUpdating(true)
      await triggerUpdate('incremental')
      await refreshAll()
    } catch (err) {
      console.error('Update failed:', err)
    } finally {
      setUpdating(false)
    }
  }

  const handleTermStructureUpdate = async () => {
    try {
      setUpdating(true)
      await triggerUpdate('term_structure')
      await refreshAll()
    } catch (err) {
      console.error('Update failed:', err)
    } finally {
      setUpdating(false)
    }
  }

  const handleManualTrigger = async () => {
    try {
      setUpdating(true)
      await triggerScheduler()
      await refreshAll()
    } catch (err) {
      console.error('Trigger failed:', err)
    } finally {
      setUpdating(false)
    }
  }

  const handleDeleteCache = async (symbol: string, dataType: string) => {
    if (!confirm(`确定要删除 ${symbol} 的 ${dataType} 缓存吗？`)) return
    try {
      await deleteCache(symbol, dataType)
      await refreshAll()
    } catch (err) {
      console.error('Delete failed:', err)
    }
  }

  const handleCleanup = async () => {
    if (!confirm('确定要清理30天前的过期缓存吗？')) return
    try {
      await cleanupExpired(30)
      await refreshAll()
    } catch (err) {
      console.error('Cleanup failed:', err)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">数据缓存管理</h1>
          <p className="text-sm text-muted-foreground">管理所有品种的K线数据和期限结构数据缓存</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={refreshAll}
            disabled={loading}
          >
            <RefreshCw className={cn('h-4 w-4 mr-2', loading && 'animate-spin')} />
            刷新
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refreshAll()}
          >
            立即检查
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-500">
          {error}
        </div>
      )}

      {/* 概览卡片 */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {/* 缓存概览 */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Database className="h-4 w-4" />
              缓存概览
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">总品种数</span>
                <span className="font-medium">{status?.total_symbols || 0}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">总大小</span>
                <span className="font-medium">{status?.total_size || '0B'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">数据完整性</span>
                <span className="font-medium">{((status?.data_integrity || 0) * 100).toFixed(0)}%</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">最后更新</span>
                <span className="font-medium text-xs">{status?.last_update || '无'}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 定时任务 */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Clock className="h-4 w-4" />
              定时任务
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">状态</span>
                <div className="flex items-center gap-1">
                  <StatusIcon status={scheduler?.status || 'running'} />
                  <span className="font-medium text-xs">
                    {scheduler?.status === 'running' ? '✓运行中' : '已停止'}
                  </span>
                </div>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">下次执行</span>
                <span className="font-medium text-xs">{scheduler?.next_run || '20:30'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">执行频率</span>
                <span className="font-medium text-xs">每日收盘后</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">最后结果</span>
                <div className="flex items-center gap-1">
                  <StatusIcon status={scheduler?.last_result || 'success'} />
                  <span className="font-medium text-xs">{scheduler?.last_result || '成功'}</span>
                </div>
              </div>
              <div className="pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full"
                  onClick={handleManualTrigger}
                  disabled={updating}
                >
                  <Play className="h-3 w-3 mr-1" />
                  手动触发
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 数据质量 */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <CheckCircle className="h-4 w-4" />
              数据质量
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">数据正确性</span>
                <div className="flex items-center gap-1">
                  <StatusIcon status={quality?.integrity?.status || 'pass'} />
                  <span className="font-medium text-xs">{quality?.integrity?.details || '检查中'}</span>
                </div>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">备份一致性</span>
                <div className="flex items-center gap-1">
                  <StatusIcon status={quality?.backup_consistency?.status || 'pass'} />
                  <span className="font-medium text-xs">{quality?.backup_consistency?.details || '检查中'}</span>
                </div>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">期限结构</span>
                <div className="flex items-center gap-1">
                  <StatusIcon status={quality?.term_structure?.status || 'pass'} />
                  <span className="font-medium text-xs">{quality?.term_structure?.details || '检查中'}</span>
                </div>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">时效性</span>
                <div className="flex items-center gap-1">
                  <StatusIcon status={quality?.timeliness?.status || 'pass'} />
                  <span className="font-medium text-xs">{quality?.timeliness?.details || '检查中'}</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 品种缓存列表 */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium">品种缓存列表</CardTitle>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleIncrementalUpdate}
                disabled={updating}
              >
                <RefreshCw className={cn('h-3 w-3 mr-1', updating && 'animate-spin')} />
                增量更新
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleTermStructureUpdate}
                disabled={updating}
              >
                <RefreshCw className={cn('h-3 w-3 mr-1', updating && 'animate-spin')} />
                期限结构更新
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleCleanup}
              >
                <Trash2 className="h-3 w-3 mr-1" />
                清理过期
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs">品种</TableHead>
                <TableHead className="text-xs">数据类型</TableHead>
                <TableHead className="text-xs">时间范围</TableHead>
                <TableHead className="text-xs">数据量</TableHead>
                <TableHead className="text-xs">文件大小</TableHead>
                <TableHead className="text-xs">质量</TableHead>
                <TableHead className="text-xs">状态</TableHead>
                <TableHead className="text-xs">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {symbols.map((item, index) => (
                <TableRow key={`${item.symbol}-${item.data_type}-${index}`}>
                  <TableCell className="text-xs font-medium">{item.symbol}</TableCell>
                  <TableCell className="text-xs">
                    {item.data_type === 'main_1h' ? '主连1H' : 
                     item.data_type === 'main_1d' ? '主连1D' : 
                     item.data_type === 'term_structure' ? '期限结构' : item.data_type}
                  </TableCell>
                  <TableCell className="text-xs">{item.time_range}</TableCell>
                  <TableCell className="text-xs">{item.record_count.toLocaleString()}</TableCell>
                  <TableCell className="text-xs">{item.file_size}</TableCell>
                  <TableCell className="text-xs">
                    <QualityBadge quality={item.quality} />
                  </TableCell>
                  <TableCell className="text-xs">
                    <StatusBadge status={item.status} />
                  </TableCell>
                  <TableCell className="text-xs">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 text-xs"
                      onClick={() => handleDeleteCache(item.symbol, item.data_type)}
                    >
                      删除
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {symbols.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-xs text-muted-foreground">
                    暂无缓存数据
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 数据质量检查详情 */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">数据质量检查详情</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs">检查项</TableHead>
                <TableHead className="text-xs">结果</TableHead>
                <TableHead className="text-xs">详情</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow>
                <TableCell className="text-xs">数据完整性</TableCell>
                <TableCell className="text-xs">
                  <div className="flex items-center gap-1">
                    <StatusIcon status={quality?.integrity?.status || 'pass'} />
                    {quality?.integrity?.status === 'pass' ? '通过' : '失败'}
                  </div>
                </TableCell>
                <TableCell className="text-xs">{quality?.integrity?.details || '检查中'}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell className="text-xs">备份一致性</TableCell>
                <TableCell className="text-xs">
                  <div className="flex items-center gap-1">
                    <StatusIcon status={quality?.backup_consistency?.status || 'pass'} />
                    {quality?.backup_consistency?.status === 'pass' ? '通过' : '失败'}
                  </div>
                </TableCell>
                <TableCell className="text-xs">{quality?.backup_consistency?.details || '检查中'}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell className="text-xs">期限结构</TableCell>
                <TableCell className="text-xs">
                  <div className="flex items-center gap-1">
                    <StatusIcon status={quality?.term_structure?.status || 'pass'} />
                    {quality?.term_structure?.status === 'pass' ? '通过' : '失败'}
                  </div>
                </TableCell>
                <TableCell className="text-xs">{quality?.term_structure?.details || '检查中'}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell className="text-xs">时效性</TableCell>
                <TableCell className="text-xs">
                  <div className="flex items-center gap-1">
                    <StatusIcon status={quality?.timeliness?.status || 'pass'} />
                    {quality?.timeliness?.status === 'pass' ? '通过' : 
                     quality?.timeliness?.status === 'warn' ? '警告' : '失败'}
                  </div>
                </TableCell>
                <TableCell className="text-xs">{quality?.timeliness?.details || '检查中'}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 更新历史 */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">更新历史</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs">时间</TableHead>
                <TableHead className="text-xs">类型</TableHead>
                <TableHead className="text-xs">品种</TableHead>
                <TableHead className="text-xs">状态</TableHead>
                <TableHead className="text-xs">耗时</TableHead>
                <TableHead className="text-xs">详情</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {history.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="text-xs">{item.timestamp}</TableCell>
                  <TableCell className="text-xs">
                    {item.type === 'incremental' ? '增量' : 
                     item.type === 'full' ? '全量' : 
                     item.type === 'term_structure' ? '期限结构' : item.type}
                  </TableCell>
                  <TableCell className="text-xs">{item.symbols.length}个品种</TableCell>
                  <TableCell className="text-xs">
                    <div className="flex items-center gap-1">
                      <StatusIcon status={item.status} />
                      {item.status === 'success' ? '成功' : '失败'}
                    </div>
                  </TableCell>
                  <TableCell className="text-xs">{item.duration}</TableCell>
                  <TableCell className="text-xs">{item.message}</TableCell>
                </TableRow>
              ))}
              {history.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-xs text-muted-foreground">
                    暂无更新历史
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
