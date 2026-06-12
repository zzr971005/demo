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
  ArrowRightCircle,
  CheckCircle,
  Clock,
  RefreshCw,
  Zap,
  TrendingUp,
  Shield,
} from 'lucide-react'
import {
  strategyReplacementApi,
  StrategyPerformance,
  ReplacementCandidate,
  ReplacementRule,
  ReplacementResult,
} from '@/lib/api'

const DEFAULT_SYMBOLS = [
  'KQ.m@SHFE.rb',
  'KQ.m@DCE.i',
  'KQ.m@SHFE.ag',
  'KQ.m@CZCE.MA',
]

export default function StrategyReplacement() {
  const [selectedSymbol, setSelectedSymbol] = useState(DEFAULT_SYMBOLS[0])
  const [performance, setPerformance] = useState<StrategyPerformance[]>([])
  const [candidates, setCandidates] = useState<ReplacementCandidate[]>([])
  const [rules, setRules] = useState<ReplacementRule[]>([])
  const [history, setHistory] = useState<ReplacementResult[]>([])
  const [loading, setLoading] = useState(true)
  const [autoCheckRunning, setAutoCheckRunning] = useState(false)

  useEffect(() => {
    fetchData()
  }, [selectedSymbol])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [perfRes, candRes, rulesRes, histRes] = await Promise.all([
        strategyReplacementApi.getPerformance(selectedSymbol),
        strategyReplacementApi.getCandidates(selectedSymbol),
        strategyReplacementApi.getRules(),
        strategyReplacementApi.getHistory(selectedSymbol),
      ])
      setPerformance(perfRes.data)
      setCandidates(candRes.data)
      setRules(rulesRes.data)
      setHistory(histRes.data)
    } catch (error) {
      console.error('Failed to fetch strategy replacement data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleToggleRule = async (ruleId: string, enabled: boolean) => {
    try {
      await strategyReplacementApi.toggleRule(ruleId, enabled)
      setRules(prev =>
        prev.map(r => (r.rule_id === ruleId ? { ...r, enabled } : r))
      )
    } catch (error) {
      console.error('Failed to toggle rule:', error)
    }
  }

  const handleReplace = async (candidate: ReplacementCandidate) => {
    try {
      await strategyReplacementApi.replaceStrategy({
        symbol: candidate.symbol,
        current_strategy: candidate.current_strategy,
        new_strategy: candidate.candidate_strategy,
        reason: candidate.reason,
        auto_confirm: true,
      })
      await fetchData()
    } catch (error) {
      console.error('Failed to replace strategy:', error)
    }
  }

  const handleAutoCheck = async () => {
    setAutoCheckRunning(true)
    try {
      await strategyReplacementApi.autoCheck(selectedSymbol)
      await fetchData()
    } catch (error) {
      console.error('Auto check failed:', error)
    } finally {
      setAutoCheckRunning(false)
    }
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Zap className="h-6 w-6" />
            策略替换管理
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            基于性能指标自动评估和替换策略
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

      <Tabs defaultValue="performance" className="space-y-4">
        <TabsList>
          <TabsTrigger value="performance" className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            策略性能
          </TabsTrigger>
          <TabsTrigger value="candidates" className="flex items-center gap-2">
            <ArrowRightCircle className="h-4 w-4" />
            替换候选
          </TabsTrigger>
          <TabsTrigger value="rules" className="flex items-center gap-2">
            <Shield className="h-4 w-4" />
            替换规则
          </TabsTrigger>
          <TabsTrigger value="history" className="flex items-center gap-2">
            <Clock className="h-4 w-4" />
            替换历史
          </TabsTrigger>
        </TabsList>

        <TabsContent value="performance" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>策略性能排名</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-3">
                  {[...Array(5)].map((_, i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>策略ID</TableHead>
                      <TableHead>夏普比率</TableHead>
                      <TableHead>最大回撤</TableHead>
                      <TableHead>胜率</TableHead>
                      <TableHead>总收益率</TableHead>
                      <TableHead>交易次数</TableHead>
                      <TableHead>更新时间</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {performance.map((p, index) => (
                      <TableRow key={p.strategy_id}>
                        <TableCell className="font-medium">
                          <div className="flex items-center gap-2">
                            <Badge variant="outline">#{index + 1}</Badge>
                            {p.strategy_id}
                          </div>
                        </TableCell>
                        <TableCell>
                          <span className={p.sharpe_ratio > 1.5 ? 'text-green-600 font-medium' : ''}>
                            {p.sharpe_ratio.toFixed(2)}
                          </span>
                        </TableCell>
                        <TableCell>
                          <span className={p.max_drawdown > -0.1 ? 'text-green-600' : 'text-red-600'}>
                            {(p.max_drawdown * 100).toFixed(2)}%
                          </span>
                        </TableCell>
                        <TableCell>
                          <span className={p.win_rate > 0.5 ? 'text-green-600' : ''}>
                            {(p.win_rate * 100).toFixed(1)}%
                          </span>
                        </TableCell>
                        <TableCell>
                          <span className={p.total_return > 0 ? 'text-green-600 font-medium' : 'text-red-600'}>
                            {(p.total_return * 100).toFixed(2)}%
                          </span>
                        </TableCell>
                        <TableCell>{p.trade_count}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {new Date(p.last_updated).toLocaleString()}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="candidates" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>替换候选列表</CardTitle>
              <Button
                onClick={handleAutoCheck}
                disabled={autoCheckRunning}
                className="flex items-center gap-2"
              >
                {autoCheckRunning ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    自动检查中...
                  </>
                ) : (
                  <>
                    <AlertCircle className="h-4 w-4" />
                    自动检查
                  </>
                )}
              </Button>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-3">
                  {[...Array(3)].map((_, i) => (
                    <Skeleton key={i} className="h-20 w-full" />
                  ))}
                </div>
              ) : candidates.length > 0 ? (
                <div className="space-y-4">
                  {candidates.map(candidate => (
                    <Card key={candidate.candidate_strategy} className="border-l-4 border-l-blue-500">
                      <CardContent className="pt-6">
                        <div className="flex items-center justify-between">
                          <div className="space-y-2">
                            <div className="flex items-center gap-3">
                              <Badge variant="outline" className="text-sm">
                                当前
                              </Badge>
                              <span className="font-medium">{candidate.current_strategy}</span>
                              <ArrowRightCircle className="h-5 w-5 text-muted-foreground mx-2" />
                              <Badge className="bg-green-600 text-sm">候选</Badge>
                              <span className="font-medium">{candidate.candidate_strategy}</span>
                            </div>
                            <p className="text-sm text-muted-foreground">{candidate.reason}</p>
                            <div className="flex items-center gap-6 mt-2">
                              <span className="text-sm">
                                置信度:{' '}
                                <span className={candidate.confidence > 0.7 ? 'text-green-600 font-medium' : ''}>
                                  {(candidate.confidence * 100).toFixed(0)}%
                                </span>
                              </span>
                              <span className="text-sm">
                                性能提升:{' '}
                                <span className="text-green-600 font-medium">
                                  {(candidate.performance_improvement * 100).toFixed(1)}%
                                </span>
                              </span>
                              <span className="text-sm">
                                风险评分:{' '}
                                <span className={candidate.risk_score < 0.3 ? 'text-green-600' : ''}>
                                  {candidate.risk_score.toFixed(2)}
                                </span>
                              </span>
                            </div>
                          </div>
                          <Button
                            onClick={() => handleReplace(candidate)}
                            className="flex items-center gap-2"
                          >
                            <CheckCircle className="h-4 w-4" />
                            执行替换
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <CheckCircle className="h-12 w-12 mx-auto mb-3 text-green-500" />
                  <p>当前策略表现良好，暂无替换候选</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="rules" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>自动替换规则</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-3">
                  {[...Array(4)].map((_, i) => (
                    <Skeleton key={i} className="h-16 w-full" />
                  ))}
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>规则名称</TableHead>
                      <TableHead>描述</TableHead>
                      <TableHead>触发条件</TableHead>
                      <TableHead>执行动作</TableHead>
                      <TableHead>优先级</TableHead>
                      <TableHead>状态</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rules.map(rule => (
                      <TableRow key={rule.rule_id}>
                        <TableCell className="font-medium">{rule.name}</TableCell>
                        <TableCell className="text-sm max-w-xs truncate">
                          {rule.description}
                        </TableCell>
                        <TableCell>
                          <code className="text-xs bg-muted px-2 py-1 rounded">
                            {rule.condition}
                          </code>
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">{rule.action}</Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">#{rule.priority}</Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <Switch
                              checked={rule.enabled}
                              onCheckedChange={checked => handleToggleRule(rule.rule_id, checked)}
                            />
                            <Label className={rule.enabled ? 'text-green-600' : 'text-muted-foreground'}>
                              {rule.enabled ? '已启用' : '已禁用'}
                            </Label>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>替换历史记录</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-3">
                  {[...Array(5)].map((_, i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : history.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>时间</TableHead>
                      <TableHead>品种</TableHead>
                      <TableHead>原策略</TableHead>
                      <TableHead>新策略</TableHead>
                      <TableHead>原因</TableHead>
                      <TableHead>状态</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {history.map(item => (
                      <TableRow key={item.transaction_id}>
                        <TableCell className="text-sm">
                          {new Date(item.timestamp).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{item.symbol}</Badge>
                        </TableCell>
                        <TableCell className="font-medium">{item.old_strategy}</TableCell>
                        <TableCell className="font-medium">{item.new_strategy}</TableCell>
                        <TableCell className="text-sm max-w-xs truncate">{item.reason}</TableCell>
                        <TableCell>
                          <Badge className="bg-green-600">成功</Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <Clock className="h-12 w-12 mx-auto mb-3" />
                  <p>暂无替换历史记录</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
