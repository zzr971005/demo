import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  CheckCircle2,
  Circle,
  Loader2,
  XCircle,
  Clock,
  TrendingDown,
  Filter,
  Search,
  Play,
  CheckSquare,
  BarChart3
} from 'lucide-react'
import api from '@/lib/api'

interface CycleStage {
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  start_time: string | null
  end_time: string | null
  input_count: number
  output_count: number
  drop_count: number
  error_message: string | null
}

interface EvolutionCycle {
  id: number
  symbol: string
  status: string
  start_time: string
  end_time: string | null
  stages: CycleStage[]
  total_factors: number
  passed_factors: number
  drop_rate: number
  generation: number
}

interface EvolutionStats {
  total_cycles: number
  completed_cycles: number
  running_cycles: number
  total_factors_evaluated: number
  total_factors_passed: number
  overall_drop_rate: number
}

const stageIcons: Record<string, React.ReactNode> = {
  Search: <Search className="h-4 w-4" />,
  Replay: <Play className="h-4 w-4" />,
  Validation: <CheckSquare className="h-4 w-4" />,
  Demo: <BarChart3 className="h-4 w-4" />,
  IC: <Filter className="h-4 w-4" />,
}

const statusConfig: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  pending: { color: 'bg-gray-500', icon: <Circle className="h-4 w-4" />, label: '等待中' },
  running: { color: 'bg-blue-500', icon: <Loader2 className="h-4 w-4 animate-spin" />, label: '运行中' },
  completed: { color: 'bg-green-500', icon: <CheckCircle2 className="h-4 w-4" />, label: '已完成' },
  failed: { color: 'bg-red-500', icon: <XCircle className="h-4 w-4" />, label: '失败' },
  skipped: { color: 'bg-gray-400', icon: <Clock className="h-4 w-4" />, label: '跳过' },
}

function StageCard({ stage }: { stage: CycleStage }) {
  const config = statusConfig[stage.status]
  const progress = stage.input_count > 0 
    ? ((stage.input_count - stage.drop_count) / stage.input_count) * 100 
    : 0
  const dropRate = stage.input_count > 0 
    ? (stage.drop_count / stage.input_count) * 100 
    : 0

  return (
    <Card className="relative overflow-hidden">
      <div className={`absolute left-0 top-0 h-full w-1 ${config.color}`} />
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {stageIcons[stage.name] || <Circle className="h-4 w-4" />}
            <CardTitle className="text-sm font-medium">{stage.name}</CardTitle>
          </div>
          <Badge variant={stage.status === 'running' ? 'default' : 'secondary'} className="gap-1">
            {config.icon}
            {config.label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="rounded bg-muted p-2">
            <div className="text-xs text-muted-foreground">输入</div>
            <div className="text-lg font-semibold">{stage.input_count}</div>
          </div>
          <div className="rounded bg-muted p-2">
            <div className="text-xs text-muted-foreground">输出</div>
            <div className="text-lg font-semibold text-green-600">{stage.output_count}</div>
          </div>
          <div className="rounded bg-muted p-2">
            <div className="text-xs text-muted-foreground">淘汰</div>
            <div className="text-lg font-semibold text-red-600">{stage.drop_count}</div>
          </div>
        </div>
        
        {stage.status !== 'pending' && (
          <>
            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <span>通过率</span>
                <span>{progress.toFixed(1)}%</span>
              </div>
              <Progress value={progress} className="h-2" />
            </div>
            <div className="flex items-center gap-1 text-xs text-red-500">
              <TrendingDown className="h-3 w-3" />
              <span>淘汰率: {dropRate.toFixed(1)}%</span>
            </div>
          </>
        )}

        {stage.start_time && (
          <div className="text-xs text-muted-foreground">
            开始: {new Date(stage.start_time).toLocaleTimeString()}
            {stage.end_time && (
              <span> · 结束: {new Date(stage.end_time).toLocaleTimeString()}</span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}


export default function ValidationMonitor() {
  const [cycles, setCycles] = useState<EvolutionCycle[]>([])
  const [stats, setStats] = useState<EvolutionStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [])

  const fetchData = async () => {
    try {
      const [cyclesRes, statsRes] = await Promise.all([
        api.get('/evolution/cycles'),
        api.get('/evolution/stats'),
      ])
      setCycles(cyclesRes.data)
      setStats(statsRes.data)
    } catch (error) {
      console.error('Failed to fetch evolution data:', error)
    } finally {
      setLoading(false)
    }
  }

  const runningCycles = cycles.filter(c => c.status === 'running')
  // 当前周期：只显示运行中的品种（如果有），否则显示第一个品种
  const currentCycles = runningCycles.length > 0 ? runningCycles : cycles.slice(0, 1)
  // 历史记录：显示非运行中的品种
  const historyCycles = cycles.filter(c => c.status !== 'running')

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6 p-6">
      {/* 统计卡片 */}
      {stats && (
        <div className="grid grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">总周期数</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_cycles}</div>
              <div className="text-xs text-muted-foreground">
                已完成: {stats.completed_cycles} · 运行中: {stats.running_cycles}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">评估因子数</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_factors_evaluated.toLocaleString()}</div>
              <div className="text-xs text-muted-foreground">
                通过: {stats.total_factors_passed.toLocaleString()}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">整体淘汰率</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">
                {(stats.overall_drop_rate * 100).toFixed(1)}%
              </div>
              <div className="text-xs text-muted-foreground">
                严格筛选确保质量
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">当前状态</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                {stats.running_cycles > 0 ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
                    <span className="text-lg font-medium">进化中</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                    <span className="text-lg font-medium">空闲</span>
                  </>
                )}
              </div>
              <div className="text-xs text-muted-foreground">
                {stats.running_cycles > 0 ? `${stats.running_cycles} 个品种正在进化` : '等待下次进化周期'}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <Tabs defaultValue="current" className="space-y-4">
        <TabsList>
          <TabsTrigger value="current">当前周期</TabsTrigger>
          <TabsTrigger value="history">历史记录</TabsTrigger>
        </TabsList>

        <TabsContent value="current" className="space-y-4">
          {currentCycles.length > 0 ? (
            <div className="space-y-4">
              {currentCycles.map((cycle) => (
                <div key={cycle.id} className="space-y-3">
                  <Card className="relative overflow-hidden">
                    <div className="absolute left-0 top-0 h-full w-1 bg-blue-500" />
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="text-lg font-semibold">
                            {cycle.symbol}
                          </h3>
                          <p className="text-xs text-muted-foreground">
                            周期 #{cycle.id} · 代数: {cycle.generation} · 开始: {new Date(cycle.start_time).toLocaleString()}
                          </p>
                        </div>
                        <Badge
                          variant={cycle.status === 'running' ? 'default' : 'secondary'}
                          className="gap-1"
                        >
                          {cycle.status === 'running' ? (
                            <>
                              <Loader2 className="h-3 w-3 animate-spin" />
                              运行中
                            </>
                          ) : (
                            <>
                              <Circle className="h-3 w-3" />
                              {cycle.status === 'completed' ? '已完成' : '待开始'}
                            </>
                          )}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">
                          总因子: {cycle.total_factors.toLocaleString()}
                        </span>
                        <span className="text-green-600">
                          通过: {cycle.passed_factors}
                        </span>
                        <span className="text-red-600">
                          淘汰: {(cycle.drop_rate * 100).toFixed(1)}%
                        </span>
                      </div>
                    </CardContent>
                  </Card>

                  {/* 5层筛选卡片 - 一行一个 */}
                  <div className="space-y-3">
                    {(Array.isArray(cycle.stages) ? cycle.stages : []).map((stage) => (
                      <StageCard key={stage.name} stage={stage} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Clock className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium">暂无运行中的进化周期</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  系统将在下一个进化窗口自动启动
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          <div className="flex items-center gap-2 mb-4">
            <Filter className="h-4 w-4" />
            <h2 className="text-lg font-semibold">历史记录</h2>
            <span className="text-sm text-muted-foreground">
              ({historyCycles.length} 个品种)
            </span>
          </div>
          
          {historyCycles.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {historyCycles.map((cycle) => (
                <Card key={cycle.id} className="relative overflow-hidden">
                  <div className="absolute left-0 top-0 h-full w-1 bg-gray-400" />
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-lg font-semibold">
                          {cycle.symbol}
                        </h3>
                        <p className="text-xs text-muted-foreground">
                          周期 #{cycle.id} · 代数: {cycle.generation}
                        </p>
                      </div>
                      <Badge 
                        variant={cycle.status === 'completed' ? 'default' : 'secondary'} 
                        className="gap-1"
                      >
                        {cycle.status === 'completed' ? (
                          <>
                            <CheckCircle2 className="h-3 w-3" />
                            已完成
                          </>
                        ) : (
                          <>
                            <Circle className="h-3 w-3" />
                            待开始
                          </>
                        )}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid grid-cols-2 gap-2">
                      {(Array.isArray(cycle.stages) ? cycle.stages : []).map((stage) => (
                        <StageCard key={stage.name} stage={stage} />
                      ))}
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">
                        总因子: {cycle.total_factors.toLocaleString()}
                      </span>
                      <span className="text-green-600">
                        通过: {cycle.passed_factors}
                      </span>
                      <span className="text-red-600">
                        淘汰: {(cycle.drop_rate * 100).toFixed(1)}%
                      </span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Clock className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium">暂无历史记录</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  所有品种都在当前运行中
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
