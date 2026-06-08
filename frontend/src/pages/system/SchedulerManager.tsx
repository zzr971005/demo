import { useState, useEffect } from 'react'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import {
  AlertCircle,
  Calendar,
  Clock,
  Play,
  Pause,
  RefreshCw,
  Settings,
  Activity,
  CheckCircle,
  XCircle,
  Trash2,
} from 'lucide-react'
import {
  schedulerApi,
  ScheduledTask,
  TaskExecution,
  SchedulerStatus,
} from '@/lib/api'

const DEFAULT_SYMBOLS = [
  'KQ.m@SHFE.rb',
  'KQ.m@DCE.i',
  'KQ.m@SHFE.ag',
  'KQ.m@CZCE.MA',
]

export default function SchedulerManager() {
  const [selectedSymbol, setSelectedSymbol] = useState(DEFAULT_SYMBOLS[0])
  const [tasks, setTasks] = useState<ScheduledTask[]>([])
  const [executions, setExecutions] = useState<TaskExecution[]>([])
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatus | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchData()
  }, [selectedSymbol])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [statusRes, tasksRes, execRes] = await Promise.all([
        schedulerApi.getStatus(),
        schedulerApi.getTasks(selectedSymbol),
        schedulerApi.getExecutions(),
      ])
      setSchedulerStatus(statusRes.data)
      setTasks(tasksRes.data)
      setExecutions(execRes.data)
    } catch (error) {
      console.error('Failed to fetch scheduler data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleStartScheduler = async () => {
    try {
      await schedulerApi.start()
      await fetchData()
    } catch (error) {
      console.error('Failed to start scheduler:', error)
    }
  }

  const handleStopScheduler = async () => {
    try {
      await schedulerApi.stop()
      await fetchData()
    } catch (error) {
      console.error('Failed to stop scheduler:', error)
    }
  }

  const handleToggleTask = async (taskId: string, enabled: boolean) => {
    try {
      if (enabled) {
        await schedulerApi.enableTask(taskId)
      } else {
        await schedulerApi.disableTask(taskId)
      }
      await fetchData()
    } catch (error) {
      console.error('Failed to toggle task:', error)
    }
  }

  const handleTriggerTask = async (taskId: string) => {
    try {
      await schedulerApi.triggerTask(taskId)
      await fetchData()
    } catch (error) {
      console.error('Failed to trigger task:', error)
    }
  }

  const handleDeleteTask = async (taskId: string) => {
    try {
      await schedulerApi.deleteTask(taskId)
      await fetchData()
    } catch (error) {
      console.error('Failed to delete task:', error)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'bg-green-600'
      case 'completed':
        return 'bg-blue-600'
      case 'failed':
        return 'bg-red-600'
      case 'pending':
        return 'bg-yellow-600'
      default:
        return 'bg-gray-600'
    }
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Settings className="h-6 w-6" />
            调度器管理
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            管理定时进化任务和执行计划
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={selectedSymbol} onValueChange={setSelectedSymbol}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="选择品种" />
            </SelectTrigger>
            <SelectContent>
              {DEFAULT_SYMBOLS.map(symbol => (
                <SelectItem key={symbol} value={symbol}>
                  {symbol}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" size="icon" onClick={fetchData}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">调度器状态</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <div
                className={`h-3 w-3 rounded-full ${schedulerStatus?.running ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`}
              />
              <span className="text-2xl font-bold">
                {schedulerStatus?.running ? '运行中' : '已停止'}
              </span>
            </div>
            <div className="mt-2 flex gap-2">
              <Button
                size="sm"
                onClick={handleStartScheduler}
                disabled={schedulerStatus?.running}
                className="flex items-center gap-1"
              >
                <Play className="h-3 w-3" />
                启动
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={handleStopScheduler}
                disabled={!schedulerStatus?.running}
                className="flex items-center gap-1"
              >
                <Pause className="h-3 w-3" />
                停止
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">任务统计</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{schedulerStatus?.total_tasks || 0}</div>
            <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
              <span>已启用: {schedulerStatus?.enabled_tasks || 0}</span>
              <span>运行中: {schedulerStatus?.running_tasks || 0}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">执行统计</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{schedulerStatus?.total_executions || 0}</div>
            <div className="text-xs text-muted-foreground mt-2">
              上次执行: {schedulerStatus?.last_execution_time
                ? new Date(schedulerStatus.last_execution_time).toLocaleString()
                : '无'}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">下次执行</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">20:30</div>
            <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
              <Calendar className="h-3 w-3" />
              每日自动进化
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="tasks" className="space-y-4">
        <TabsList>
          <TabsTrigger value="tasks" className="flex items-center gap-2">
            <Activity className="h-4 w-4" />
            任务列表
          </TabsTrigger>
          <TabsTrigger value="executions" className="flex items-center gap-2">
            <Clock className="h-4 w-4" />
            执行记录
          </TabsTrigger>
        </TabsList>

        <TabsContent value="tasks" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>调度任务列表</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-3">
                  {[...Array(5)].map((_, i) => (
                    <Skeleton key={i} className="h-16 w-full" />
                  ))}
                </div>
              ) : tasks.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>任务ID</TableHead>
                      <TableHead>任务名称</TableHead>
                      <TableHead>品种</TableHead>
                      <TableHead>Cron表达式</TableHead>
                      <TableHead>类型</TableHead>
                      <TableHead>下次执行</TableHead>
                      <TableHead>上次执行</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {tasks.map(task => (
                      <TableRow key={task.task_id}>
                        <TableCell className="font-medium font-mono text-sm">
                          {task.task_id}
                        </TableCell>
                        <TableCell className="font-medium">{task.name}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{task.symbol}</Badge>
                        </TableCell>
                        <TableCell>
                          <code className="text-xs bg-muted px-2 py-1 rounded">
                            {task.cron_expression}
                          </code>
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">{task.task_type}</Badge>
                        </TableCell>
                        <TableCell className="text-sm">
                          {task.next_run_time
                            ? new Date(task.next_run_time).toLocaleString()
                            : '-'}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {task.last_run_time
                            ? new Date(task.last_run_time).toLocaleString()
                            : '从未执行'}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <Switch
                              checked={task.enabled}
                              onCheckedChange={checked => handleToggleTask(task.task_id, checked)}
                            />
                            <Label className={task.enabled ? 'text-green-600' : 'text-muted-foreground'}>
                              {task.enabled ? '已启用' : '已禁用'}
                            </Label>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleTriggerTask(task.task_id)}
                              className="flex items-center gap-1"
                            >
                              <Play className="h-3 w-3" />
                              立即执行
                            </Button>
                            <Button
                              size="sm"
                              variant="destructive"
                              onClick={() => handleDeleteTask(task.task_id)}
                              className="flex items-center gap-1"
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <Calendar className="h-12 w-12 mx-auto mb-3" />
                  <p>暂无调度任务</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="executions" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>执行记录</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-3">
                  {[...Array(10)].map((_, i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : executions.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>执行ID</TableHead>
                      <TableHead>任务ID</TableHead>
                      <TableHead>开始时间</TableHead>
                      <TableHead>结束时间</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>结果</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {executions.map(exec => (
                      <TableRow key={exec.execution_id}>
                        <TableCell className="font-mono text-sm">{exec.execution_id}</TableCell>
                        <TableCell className="font-mono text-sm">{exec.task_id}</TableCell>
                        <TableCell className="text-sm">
                          {new Date(exec.start_time).toLocaleString()}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {exec.end_time ? new Date(exec.end_time).toLocaleString() : '-'}
                        </TableCell>
                        <TableCell>
                          <Badge className={getStatusColor(exec.status)}>
                            {exec.status === 'running' && (
                              <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
                            )}
                            {exec.status === 'completed' && (
                              <CheckCircle className="h-3 w-3 mr-1" />
                            )}
                            {exec.status === 'failed' && (
                              <XCircle className="h-3 w-3 mr-1" />
                            )}
                            {exec.status === 'running' ? '运行中' : exec.status === 'completed' ? '成功' : exec.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm max-w-xs truncate">
                          {exec.error_message ? (
                            <span className="text-red-600 flex items-center gap-1">
                              <AlertCircle className="h-3 w-3" />
                              {exec.error_message}
                            </span>
                          ) : (
                            <span className="text-green-600 flex items-center gap-1">
                              <CheckCircle className="h-3 w-3" />
                              执行成功
                            </span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <Clock className="h-12 w-12 mx-auto mb-3" />
                  <p>暂无执行记录</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
