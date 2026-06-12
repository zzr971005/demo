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
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  RefreshCw,
  FileCheck,
  TrendingUp,
  DollarSign,
  Shield,
  Bell,
  Check,
  Play,
} from 'lucide-react'
import {
  positionApi,
  PositionData,
  ReconciliationResult,
  RiskReport,
  PositionAlert,
} from '@/lib/api'

const DEFAULT_SYMBOLS = [
  'KQ.m@SHFE.rb',
  'KQ.m@DCE.i',
  'KQ.m@SHFE.ag',
  'KQ.m@CZCE.MA',
]

export default function PositionReconciliation() {
  const [selectedSymbol, setSelectedSymbol] = useState(DEFAULT_SYMBOLS[0])
  const [positions, setPositions] = useState<PositionData[]>([])
  const [reconciliationHistory, setReconciliationHistory] = useState<ReconciliationResult[]>([])
  const [alerts, setAlerts] = useState<PositionAlert[]>([])
  const [riskReport, setRiskReport] = useState<RiskReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [reconciling, setReconciling] = useState(false)

  useEffect(() => {
    fetchData()
  }, [selectedSymbol])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [posRes, histRes, alertsRes, riskRes] = await Promise.all([
        positionApi.getCurrentPositions(selectedSymbol),
        positionApi.getReconciliationHistory(20),
        positionApi.getAlerts(),
        positionApi.getRiskReport(),
      ])
      setPositions(posRes.data)
      setReconciliationHistory(histRes.data)
      setAlerts(alertsRes.data)
      setRiskReport(riskRes.data)
    } catch (error) {
      console.error('Failed to fetch position data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleRunReconciliation = async () => {
    setReconciling(true)
    try {
      await positionApi.runReconciliation()
      await fetchData()
    } catch (error) {
      console.error('Failed to run reconciliation:', error)
    } finally {
      setReconciling(false)
    }
  }

  const handleAcknowledgeAlert = async (alertId: string) => {
    try {
      await positionApi.acknowledgeAlert(alertId)
      await fetchData()
    } catch (error) {
      console.error('Failed to acknowledge alert:', error)
    }
  }

  const handleAutoConfirm = async () => {
    try {
      await positionApi.autoConfirm(0.01)
      await fetchData()
    } catch (error) {
      console.error('Failed to auto confirm:', error)
    }
  }

  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'low':
        return 'text-green-600 bg-green-100'
      case 'medium':
        return 'text-yellow-600 bg-yellow-100'
      case 'high':
        return 'text-red-600 bg-red-100'
      default:
        return 'text-gray-600 bg-gray-100'
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'bg-red-600'
      case 'medium':
        return 'bg-yellow-600'
      case 'low':
        return 'bg-green-600'
      default:
        return 'bg-gray-600'
    }
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <FileCheck className="h-6 w-6" />
            仓位对账管理
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            持仓核对、风险监控和差异管理
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
          <Button
            onClick={handleRunReconciliation}
            disabled={reconciling}
            className="flex items-center gap-2"
          >
            {reconciling ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" />
                对账中...
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                执行对账
              </>
            )}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <DollarSign className="h-4 w-4" />
              总风险暴露
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ¥{riskReport?.total_exposure.toLocaleString() || '0'}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Shield className="h-4 w-4" />
              保证金使用率
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
            {((riskReport?.margin_utilization || 0) * 100).toFixed(1)}%
          </div>
          <div className="mt-1 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all ${(riskReport?.margin_utilization || 0) > 0.8 ? 'bg-red-500' : 'bg-green-500'}`}
              style={{ width: `${Math.min((riskReport?.margin_utilization || 0) * 100, 100)}%` }}
            />
          </div>
        </CardContent>
      </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              浮动盈亏
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${(riskReport?.total_unrealized_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              ¥{riskReport?.total_unrealized_pnl.toLocaleString() || '0'}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Bell className="h-4 w-4" />
              风险等级
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Badge className={`text-lg px-4 py-1 ${getRiskLevelColor(riskReport?.risk_level || 'low')}`}>
              {riskReport?.risk_level === 'low' ? '低风险' : riskReport?.risk_level === 'medium' ? '中风险' : '高风险'}
            </Badge>
          </CardContent>
        </Card>
      </div>

      {riskReport && riskReport.recommendations.length > 0 && (
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>风险建议</AlertTitle>
          <AlertDescription>
            <ul className="list-disc list-inside space-y-1">
              {(Array.isArray(riskReport.recommendations) ? riskReport.recommendations : []).map((rec, i) => (
                <li key={i}>{rec}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="positions" className="space-y-4">
        <TabsList>
          <TabsTrigger value="positions" className="flex items-center gap-2">
            <DollarSign className="h-4 w-4" />
            当前持仓
          </TabsTrigger>
          <TabsTrigger value="reconciliation" className="flex items-center gap-2">
            <FileCheck className="h-4 w-4" />
            对账记录
          </TabsTrigger>
          <TabsTrigger value="alerts" className="flex items-center gap-2">
            <Bell className="h-4 w-4" />
            风险告警
            {alerts.filter(a => !a.acknowledged).length > 0 && (
              <Badge variant="destructive" className="ml-1">
                {alerts.filter(a => !a.acknowledged).length}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="positions" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>持仓列表</CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={handleAutoConfirm}
              className="flex items-center gap-2"
            >
              <Check className="h-4 w-4" />
              自动确认差异
            </Button>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-3">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : positions.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>品种</TableHead>
                    <TableHead>方向</TableHead>
                    <TableHead>持仓量</TableHead>
                    <TableHead>开仓价</TableHead>
                    <TableHead>当前价</TableHead>
                    <TableHead>浮动盈亏</TableHead>
                    <TableHead>已实现盈亏</TableHead>
                    <TableHead>占用保证金</TableHead>
                    <TableHead>杠杆</TableHead>
                    <TableHead>更新时间</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {positions.map(pos => (
                    <TableRow key={`${pos.symbol}-${pos.direction}`}>
                      <TableCell>
                        <Badge variant="outline">{pos.symbol}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge className={pos.direction === 'long' ? 'bg-green-600' : 'bg-red-600'}>
                        {pos.direction === 'long' ? '做多' : '做空'}
                      </Badge>
                      </TableCell>
                      <TableCell className="font-medium">{pos.volume.toLocaleString()}</TableCell>
                      <TableCell>¥{pos.open_price.toLocaleString()}</TableCell>
                      <TableCell>¥{pos.current_price.toLocaleString()}</TableCell>
                      <TableCell>
                        <span className={pos.unrealized_pnl >= 0 ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>
                          ¥{pos.unrealized_pnl.toLocaleString()}
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className={pos.realized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                          ¥{pos.realized_pnl.toLocaleString()}
                        </span>
                      </TableCell>
                      <TableCell>¥{pos.margin_used.toLocaleString()}</TableCell>
                      <TableCell>{pos.leverage}x</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {new Date(pos.update_time).toLocaleString()}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <DollarSign className="h-12 w-12 mx-auto mb-3" />
                <p>暂无持仓数据</p>
              </div>
            )}
          </CardContent>
        </Card>
      </TabsContent>

        <TabsContent value="reconciliation" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>对账历史记录</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-3">
                  {[...Array(5)].map((_, i) => (
                    <Skeleton key={i} className="h-16 w-full" />
                  ))}
                </div>
              ) : reconciliationHistory.length > 0 ? (
                <div className="space-y-4">
                  {reconciliationHistory.map(rec => (
                    <Card key={rec.reconciliation_id} className="border-l-4 border-l-blue-500">
                      <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <Badge variant="outline">{rec.reconciliation_id}</Badge>
                            <Badge className={getSeverityColor(rec.status === 'completed' ? 'low' : 'high')}>
                              {rec.status === 'completed' ? '已完成' : rec.status}
                            </Badge>
                          </div>
                          <span className="text-sm text-muted-foreground">
                            {new Date(rec.end_time).toLocaleString()}
                          </span>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-5 gap-4 mb-4">
                          <div>
                            <div className="text-sm text-muted-foreground mb-1">总持仓</div>
                            <div className="text-xl font-bold">{rec.total_positions}</div>
                          </div>
                          <div>
                            <div className="text-sm text-muted-foreground mb-1">匹配</div>
                            <div className="text-xl font-bold text-green-600">{rec.matched_count}</div>
                          </div>
                          <div>
                            <div className="text-sm text-muted-foreground mb-1">不匹配</div>
                            <div className="text-xl font-bold text-red-600">{rec.mismatched_count}</div>
                          </div>
                          <div>
                            <div className="text-sm text-muted-foreground mb-1">待处理</div>
                            <div className="text-xl font-bold text-yellow-600">{rec.pending_count}</div>
                          </div>
                          <div>
                            <div className="text-sm text-muted-foreground mb-1">匹配率</div>
                            <div className="text-xl font-bold">{(rec.summary.match_rate * 100).toFixed(1)}%</div>
                          </div>
                        </div>

                        {rec.items.length > 0 && (
                          <div className="border-t pt-4">
                            <h4 className="text-sm font-medium mb-3">对账明细</h4>
                            <Table>
                              <TableHeader>
                                <TableRow>
                                  <TableHead>品种</TableHead>
                                  <TableHead>方向</TableHead>
                                  <TableHead>预期数量</TableHead>
                                  <TableHead>实际数量</TableHead>
                                  <TableHead>数量差异</TableHead>
                                  <TableHead>预期保证金</TableHead>
                                  <TableHead>实际保证金</TableHead>
                                  <TableHead>保证金差异</TableHead>
                                  <TableHead>状态</TableHead>
                                  <TableHead>差异</TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {(Array.isArray(rec.items) ? rec.items : []).map((item, i) => (
                                  <TableRow key={i}>
                                    <TableCell>
                                      <Badge variant="outline">{item.symbol}</Badge>
                                    </TableCell>
                                    <TableCell>
                                      <Badge className={item.direction === 'long' ? 'bg-green-600' : 'bg-red-600'}>
                                        {item.direction === 'long' ? '做多' : '做空'}
                                    </Badge>
                                    </TableCell>
                                    <TableCell>{item.expected_volume.toLocaleString()}</TableCell>
                                    <TableCell>{item.actual_volume.toLocaleString()}</TableCell>
                                    <TableCell className={Math.abs(item.volume_diff) > 0.1 ? 'text-red-600 font-medium' : ''}>
                                      {item.volume_diff > 0 ? '+' : ''}{item.volume_diff.toLocaleString()}
                                    </TableCell>
                                    <TableCell>¥{item.expected_margin.toLocaleString()}</TableCell>
                                    <TableCell>¥{item.actual_margin.toLocaleString()}</TableCell>
                                    <TableCell className={Math.abs(item.margin_diff) > 0.1 ? 'text-red-600 font-medium' : ''}>
                                      {item.margin_diff > 0 ? '+' : ''}¥{item.margin_diff.toLocaleString()}
                                    </TableCell>
                                    <TableCell>
                                      <Badge className={getSeverityColor(item.severity)}>
                                        {item.status === 'matched' ? '匹配' : item.status}
                                      </Badge>
                                    </TableCell>
                                    <TableCell className="text-sm max-w-xs truncate">
                                      {item.discrepancy || '-'}
                                    </TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <Clock className="h-12 w-12 mx-auto mb-3" />
                  <p>暂无对账记录</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="alerts" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>风险告警列表</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-3">
                  {[...Array(5)].map((_, i) => (
                    <Skeleton key={i} className="h-16 w-full" />
                  ))}
                </div>
              ) : alerts.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>告警ID</TableHead>
                      <TableHead>品种</TableHead>
                      <TableHead>类型</TableHead>
                      <TableHead>严重程度</TableHead>
                      <TableHead>消息</TableHead>
                      <TableHead>当前值</TableHead>
                      <TableHead>阈值</TableHead>
                      <TableHead>时间</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {alerts.map(alert => (
                      <TableRow key={alert.alert_id}>
                        <TableCell className="font-mono text-sm">{alert.alert_id}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{alert.symbol}</Badge>
                        </TableCell>
                        <TableCell>{alert.alert_type}</TableCell>
                        <TableCell>
                          <Badge className={getSeverityColor(alert.severity)}>
                            {alert.severity === 'high' ? '高' : alert.severity === 'medium' ? '中' : '低'}
                          </Badge>
                        </TableCell>
                        <TableCell className="max-w-xs truncate">{alert.message}</TableCell>
                        <TableCell>{alert.current_value.toLocaleString()}</TableCell>
                        <TableCell>{alert.threshold.toLocaleString()}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {new Date(alert.timestamp).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          {alert.acknowledged ? (
                            <Badge variant="secondary">已确认</Badge>
                          ) : (
                            <Badge variant="destructive">未处理</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          {!alert.acknowledged && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleAcknowledgeAlert(alert.alert_id)}
                              className="flex items-center gap-1"
                            >
                              <CheckCircle className="h-3 w-3" />
                              确认
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <CheckCircle className="h-12 w-12 mx-auto mb-3 text-green-500" />
                  <p>暂无风险告警</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
