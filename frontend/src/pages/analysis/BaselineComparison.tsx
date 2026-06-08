import { useState, useEffect } from 'react'
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  Area,
  AreaChart,
  Line,
  LineChart,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  TrendingUp,
  TrendingDown,
  BarChart3,
  LineChart as LineChartIcon,
  Activity,
  Target,
  Zap,
  ArrowUp,
  ArrowDown,
  LayoutGrid,
} from 'lucide-react'
import api, { baselineApi } from '@/lib/api'

interface MetricData {
  name: string
  value: number
  strategy_value: number
  baseline_value: number
  improvement: number
  unit: string
  is_better: boolean
}

interface EquityPoint {
  date: string
  strategy_equity: number
  baseline_equity: number
}

interface MonthlyReturn {
  month: string
  strategy_return: number
  baseline_return: number
}

interface DrawdownPoint {
  date: string
  strategy_drawdown: number
  baseline_drawdown: number
}

interface BaselineComparisonData {
  symbol: string
  baseline_name: string
  time_period: string
  metrics: MetricData[]
  equity_curve: EquityPoint[]
  monthly_returns: MonthlyReturn[]
  drawdown_curve: DrawdownPoint[]
  win_rate_comparison: {
    long_win_rate: number
    short_win_rate: number
    baseline_win_rate: number
  }
  trade_analysis: {
    total_trades: number
    winning_trades: number
    losing_trades: number
    avg_win: number
    avg_loss: number
    max_win: number
    max_loss: number
    consecutive_wins: number
    consecutive_losses: number
  }
}

interface SymbolComparisonRow {
  symbol: string
  baseline_name: string
  time_period: string
  metrics: {
    name: string
    strategy_value: number
    baseline_value: number
  }[]
}

interface BaselineStrategy {
  id: string
  name: string
}

const ALL_SYMBOLS = [
  'RB', 'I', 'J', 'JM',
  'MA', 'TA', 'FG', 'SR', 'PP', 'L',
  'IF', 'IC', 'IH', 'IM'
]

const BASELINE_STRATEGIES_INFO: Record<string, BaselineStrategyInfo> = {
  buy_and_hold: {
    id: 'buy_and_hold',
    name: '买入持有',
    description: '最简单的被动投资策略，开多后持有至期末',
    method: '在期初以开盘价开多，全程满仓持有至期末',
    position: '全程满仓开多 (100%)',
    entryCondition: '期初开多买入',
    exitCondition: '期末平仓卖出'
  },
  sma_crossover: {
    id: 'sma_crossover',
    name: '双均线交叉',
    description: '基于均线交叉的趋势跟踪策略',
    method: '短期均线上穿长期均线时开多，下穿时开空',
    position: '满仓开多/空仓切换 (0% 或 100%)',
    entryCondition: '10日均线 > 30日均线 开多',
    exitCondition: '10日均线 < 30日均线 开空'
  },
  momentum: {
    id: 'momentum',
    name: '动量策略',
    description: '基于价格动量的趋势跟踪策略',
    method: '价格动量超过阈值时开多，低于负阈值时开空',
    position: '多空切换 (-100%, 0%, 100%)',
    entryCondition: '20日动量 > 2% 开多，< -2% 开空',
    exitCondition: '动量回归至 ±2% 范围内平仓'
  },
  mean_reversion: {
    id: 'mean_reversion',
    name: '均值回归',
    description: '基于价格偏离均值的反转策略',
    method: '价格显著偏离均值时反向交易',
    position: '多空切换 (-100%, 0%, 100%)',
    entryCondition: 'Z-score > 1.0 开空，< -1.0 开多',
    exitCondition: 'Z-score 回归至 ±1.0 范围内平仓'
  }
}

function formatValue(value: number, unit: string): string {
  if (unit === '%') {
    return `${(value * 100).toFixed(2)}%`
  }
  if (unit === '次' || unit === '天') {
    return `${value}${unit}`
  }
  return value.toFixed(2)
}

function mergeAllBaselinesData(data: AllBaselinesData) {
  // Merge equity curves from all baselines into a single dataset
  const merged: Record<string, any> = {}
  
  data.baselines.forEach(baseline => {
    baseline.equity_curve.forEach(point => {
      if (!merged[point.date]) {
        merged[point.date] = { date: point.date }
      }
      merged[point.date][baseline.baseline_type] = point.baseline_equity
      // Strategy equity is the same across all baselines, so we can use any
      if (!merged[point.date].strategy) {
        merged[point.date].strategy = point.strategy_equity
      }
    })
  })
  
  return Object.values(merged).sort((a, b) => a.date.localeCompare(b.date))
}

function MetricCard({ metric }: { metric: MetricData }) {
  const isImproved = metric.is_better
    ? metric.strategy_value > metric.baseline_value
    : metric.strategy_value < metric.baseline_value

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{metric.name}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-2xl font-bold">
                {formatValue(metric.strategy_value, metric.unit)}
              </div>
              <div className="text-xs text-muted-foreground">策略</div>
            </div>
            <div className="text-right">
              <div className="text-lg font-medium">
                {formatValue(metric.baseline_value, metric.unit)}
              </div>
              <div className="text-xs text-muted-foreground">基线</div>
            </div>
          </div>
          <div
            className={`flex items-center gap-1 text-sm ${
              isImproved ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {isImproved ? (
              <ArrowUp className="h-4 w-4" />
            ) : (
              <ArrowDown className="h-4 w-4" />
            )}
            <span>
              {metric.unit === '%'
                ? `${(metric.improvement * 100).toFixed(2)}pp`
                : metric.improvement.toFixed(2)}
              {metric.unit !== '%' && metric.unit !== '次' && metric.unit !== '天'
                ? metric.unit
                : ''}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

interface BaselineStrategyInfo {
  id: string
  name: string
  description: string
  method: string
  position: string
  entryCondition: string
  exitCondition: string
}

interface AllBaselinesData {
  symbol: string
  strategy_formula: string | null
  baselines: Array<{
    baseline_type: string
    baseline_name: string
    metrics: Array<{
      name: string
      strategy_value: number
      baseline_value: number
    }>
    equity_curve: Array<{
      date: string
      strategy_equity: number
      baseline_equity: number
    }>
  }>
}

export default function BaselineComparisonPage() {
  const [selectedSymbol, setSelectedSymbol] = useState('RB')
  const [selectedBaseline, setSelectedBaseline] = useState('buy_and_hold')
  const [baselineStrategies, setBaselineStrategies] = useState<BaselineStrategy[]>([])
  const [comparisonData, setComparisonData] = useState<BaselineComparisonData | null>(null)
  const [allBaselinesData, setAllBaselinesData] = useState<AllBaselinesData | null>(null)
  const [allSymbolsData, setAllSymbolsData] = useState<SymbolComparisonRow[]>([])
  const [loading, setLoading] = useState(true)
  const [crossLoading, setCrossLoading] = useState(false)

  useEffect(() => {
    fetchBaselineStrategies()
  }, [])

  useEffect(() => {
    fetchComparisonData()
    fetchAllBaselinesData()
  }, [selectedSymbol, selectedBaseline])

  const fetchBaselineStrategies = async () => {
    try {
      const response = await api.get('/baseline/strategies')
      setBaselineStrategies(response.data)
    } catch (error) {
      console.error('Failed to fetch baseline strategies:', error)
    }
  }

  const fetchComparisonData = async () => {
    setLoading(true)
    try {
      const response = await api.get(
        `/baseline/comparison/${selectedSymbol}?baseline=${selectedBaseline}`
      )
      setComparisonData(response.data)
    } catch (error) {
      console.error('Failed to fetch comparison data:', error)
      setComparisonData(null)
    } finally {
      setLoading(false)
    }
  }

  const fetchAllBaselinesData = async () => {
    try {
      const response = await baselineApi.getAllBaselines(selectedSymbol)
      setAllBaselinesData(response.data)
    } catch (error) {
      console.error('Failed to fetch all baselines data:', error)
      setAllBaselinesData(null)
    }
  }

  const fetchAllSymbolsComparison = async () => {
    setCrossLoading(true)
    try {
      const response = await api.get(
        `/baseline/all-symbols?baseline=${selectedBaseline}`
      )
      setAllSymbolsData(response.data)
    } catch (error) {
      console.error('Failed to fetch all symbols comparison:', error)
      setAllSymbolsData([])
    } finally {
      setCrossLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4" />
          <p className="text-muted-foreground">加载中...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">研究基线对比</h1>
          {comparisonData && (
            <p className="text-sm text-muted-foreground mt-1">
              {comparisonData.time_period}
            </p>
          )}
        </div>
        <div className="flex items-center gap-4">
          <Select value={selectedSymbol} onValueChange={setSelectedSymbol}>
            <SelectTrigger className="w-32">
              <SelectValue placeholder="选择品种" />
            </SelectTrigger>
            <SelectContent>
              {ALL_SYMBOLS.map((symbol) => (
                <SelectItem key={symbol} value={symbol}>
                  {symbol}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={selectedBaseline} onValueChange={setSelectedBaseline}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="选择基线策略" />
            </SelectTrigger>
            <SelectContent>
              {baselineStrategies.map((strategy) => (
                <SelectItem key={strategy.id} value={strategy.id}>
                  {strategy.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview" className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            全基线概览
          </TabsTrigger>
          <TabsTrigger value="single" className="flex items-center gap-2">
            <Target className="h-4 w-4" />
            单品种对比
          </TabsTrigger>
          <TabsTrigger
            value="cross"
            className="flex items-center gap-2"
            onClick={fetchAllSymbolsComparison}
          >
            <LayoutGrid className="h-4 w-4" />
            横向对比
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          {allBaselinesData ? (
            <>
              <div className="flex items-center gap-2 mb-4">
                <Badge variant="outline" className="text-base px-3 py-1">
                  {allBaselinesData.symbol}
                </Badge>
                {allBaselinesData.strategy_formula && (
                  <Badge variant="secondary" className="text-base px-3 py-1">
                    策略: {allBaselinesData.strategy_formula.substring(0, 30)}...
                  </Badge>
                )}
              </div>

              <Card className="border-2 border-primary/20">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-xl">
                    <LineChartIcon className="h-6 w-6" />
                    4种基线策略收益曲线对比
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={500}>
                    <LineChart data={mergeAllBaselinesData(allBaselinesData)}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis 
                        dataKey="date" 
                        tick={{ fontSize: 12, fill: '#6b7280' }}
                        stroke="#6b7280"
                      />
                      <YAxis 
                        tick={{ fontSize: 12, fill: '#6b7280' }}
                        stroke="#6b7280"
                        label={{ value: '权益', angle: -90, position: 'insideLeft', fill: '#6b7280' }}
                        domain={['auto', 'auto']}
                        allowDataOverflow={true}
                      />
                      <Tooltip 
                        contentStyle={{
                          backgroundColor: 'rgba(255, 255, 255, 0.98)',
                          border: '2px solid #e5e7eb',
                          borderRadius: '12px',
                          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)'
                        }}
                      />
                      <Legend 
                        verticalAlign="top" 
                        height={40}
                        iconType="line"
                        wrapperStyle={{ paddingTop: '10px' }}
                      />
                      <Line
                        type="monotone"
                        dataKey="strategy"
                        name="策略"
                        stroke="#60a5fa"
                        strokeWidth={3}
                        dot={false}
                        activeDot={{ r: 6, fill: '#60a5fa' }}
                      />
                      <Line
                        type="monotone"
                        dataKey="buy_and_hold"
                        name="买入持有"
                        stroke="#a78bfa"
                        strokeWidth={2.5}
                        dot={false}
                        activeDot={{ r: 5, fill: '#a78bfa' }}
                      />
                      <Line
                        type="monotone"
                        dataKey="sma_crossover"
                        name="双均线交叉"
                        stroke="#34d399"
                        strokeWidth={2.5}
                        dot={false}
                        activeDot={{ r: 5, fill: '#34d399' }}
                      />
                      <Line
                        type="monotone"
                        dataKey="momentum"
                        name="动量策略"
                        stroke="#fbbf24"
                        strokeWidth={2.5}
                        dot={false}
                        activeDot={{ r: 5, fill: '#fbbf24' }}
                      />
                      <Line
                        type="monotone"
                        dataKey="mean_reversion"
                        name="均值回归"
                        stroke="#f472b6"
                        strokeWidth={2.5}
                        dot={false}
                        activeDot={{ r: 5, fill: '#f472b6' }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              <div className="grid grid-cols-2 gap-6">
                {(Array.isArray(allBaselinesData.baselines) ? allBaselinesData.baselines : []).map((baseline) => {
                  const totalReturn = baseline.metrics.find(m => m.name === '总收益率')
                  const sharpe = baseline.metrics.find(m => m.name === '夏普比率')
                  const maxDrawdown = baseline.metrics.find(m => m.name === '最大回撤')
                  const winRate = baseline.metrics.find(m => m.name === '胜率')
                  const strategyInfo = BASELINE_STRATEGIES_INFO[baseline.baseline_type]
                  
                  const returnBetter = totalReturn && totalReturn.strategy_value > totalReturn.baseline_value
                  
                  return (
                    <Card key={baseline.baseline_type} className={`border-2 ${returnBetter ? 'border-green-500/40 bg-green-50/30' : 'border-red-500/40 bg-red-50/30'}`}>
                      <CardHeader className="pb-4">
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-base font-semibold">{baseline.baseline_name}</CardTitle>
                          <Badge variant={returnBetter ? 'default' : 'destructive'} className={returnBetter ? 'bg-green-600' : ''}>
                            {returnBetter ? '优于基线' : '劣于基线'}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">{strategyInfo?.description}</p>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        {/* 策略说明 */}
                        <div className="bg-muted/50 rounded-lg p-3 space-y-2">
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            <div>
                              <div className="font-medium text-muted-foreground">交易方法</div>
                              <div className="text-xs">{strategyInfo?.method}</div>
                            </div>
                            <div>
                              <div className="font-medium text-muted-foreground">仓位设置</div>
                              <div className="text-xs">{strategyInfo?.position}</div>
                            </div>
                            <div>
                              <div className="font-medium text-muted-foreground">入场条件</div>
                              <div className="text-xs">{strategyInfo?.entryCondition}</div>
                            </div>
                            <div>
                              <div className="font-medium text-muted-foreground">出场条件</div>
                              <div className="text-xs">{strategyInfo?.exitCondition}</div>
                            </div>
                          </div>
                        </div>
                        
                        {/* 绩效指标 */}
                        <div>
                          <div className="text-xs text-muted-foreground mb-2">总收益率</div>
                          <div className={`text-2xl font-bold ${returnBetter ? 'text-green-600' : 'text-red-600'}`}>
                            {totalReturn ? `${(totalReturn.strategy_value * 100).toFixed(2)}%` : 'N/A'}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            基线: {totalReturn ? `${(totalReturn.baseline_value * 100).toFixed(2)}%` : 'N/A'}
                          </div>
                        </div>
                        <div className="grid grid-cols-4 gap-3 text-xs">
                          <div className="bg-muted/30 rounded p-2">
                            <div className="text-muted-foreground text-[10px]">夏普</div>
                            <div className="font-semibold text-sm">{sharpe ? sharpe.strategy_value.toFixed(2) : 'N/A'}</div>
                          </div>
                          <div className="bg-muted/30 rounded p-2">
                            <div className="text-muted-foreground text-[10px]">胜率</div>
                            <div className="font-semibold text-sm">{winRate ? `${(winRate.strategy_value * 100).toFixed(1)}%` : 'N/A'}</div>
                          </div>
                          <div className="bg-muted/30 rounded p-2">
                            <div className="text-muted-foreground text-[10px]">回撤</div>
                            <div className="font-semibold text-sm text-red-600">{maxDrawdown ? `${(maxDrawdown.strategy_value * 100).toFixed(2)}%` : 'N/A'}</div>
                          </div>
                          <div className="bg-muted/30 rounded p-2">
                            <div className="text-muted-foreground text-[10px]">对比</div>
                            <div className={`font-semibold text-sm ${returnBetter ? 'text-green-600' : 'text-red-600'}`}>
                              {returnBetter ? '优于' : '劣于'}
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            </>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <BarChart3 className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium">暂无基线对比数据</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  请确保该品种有可用的候选因子
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="single" className="space-y-4">
          {comparisonData ? (
            <>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-base px-3 py-1">
                  {comparisonData.symbol}
                </Badge>
                <Badge variant="secondary" className="text-base px-3 py-1">
                  基线: {comparisonData.baseline_name}
                </Badge>
              </div>

              <div className="grid grid-cols-5 gap-4">
                {comparisonData.metrics.slice(0, 5).map((metric) => (
                  <MetricCard key={metric.name} metric={metric} />
                ))}
              </div>

              <Tabs defaultValue="equity" className="space-y-4">
                <TabsList>
                  <TabsTrigger value="equity" className="flex items-center gap-2">
                    <TrendingUp className="h-4 w-4" />
                    权益曲线
                  </TabsTrigger>
                  <TabsTrigger value="drawdown" className="flex items-center gap-2">
                    <TrendingDown className="h-4 w-4" />
                    回撤曲线
                  </TabsTrigger>
                  <TabsTrigger value="monthly" className="flex items-center gap-2">
                    <BarChart3 className="h-4 w-4" />
                    月度收益
                  </TabsTrigger>
                  <TabsTrigger value="metrics" className="flex items-center gap-2">
                    <Activity className="h-4 w-4" />
                    详细指标
                  </TabsTrigger>
                  <TabsTrigger value="trades" className="flex items-center gap-2">
                    <Zap className="h-4 w-4" />
                    交易分析
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="equity" className="space-y-4">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <LineChartIcon className="h-5 w-5" />
                        权益曲线对比
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ResponsiveContainer width="100%" height={400}>
                        <AreaChart data={comparisonData.equity_curve}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                          <YAxis tick={{ fontSize: 12 }} />
                          <Tooltip />
                          <Legend />
                          <Area
                            type="monotone"
                            dataKey="strategy_equity"
                            name="策略权益"
                            stroke="#2563eb"
                            fill="#3b82f6"
                            fillOpacity={0.1}
                          />
                          <Area
                            type="monotone"
                            dataKey="baseline_equity"
                            name="基线权益"
                            stroke="#64748b"
                            fill="#94a3b8"
                            fillOpacity={0.1}
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="drawdown" className="space-y-4">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <TrendingDown className="h-5 w-5" />
                        回撤曲线对比
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ResponsiveContainer width="100%" height={400}>
                        <AreaChart data={comparisonData.drawdown_curve}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                          <YAxis tick={{ fontSize: 12 }} />
                          <Tooltip />
                          <Legend />
                          <Area
                            type="monotone"
                            dataKey="strategy_drawdown"
                            name="策略回撤"
                            stroke="#dc2626"
                            fill="#ef4444"
                            fillOpacity={0.1}
                          />
                          <Area
                            type="monotone"
                            dataKey="baseline_drawdown"
                            name="基线回撤"
                            stroke="#64748b"
                            fill="#94a3b8"
                            fillOpacity={0.1}
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="monthly" className="space-y-4">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <BarChart3 className="h-5 w-5" />
                        月度收益对比
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ResponsiveContainer width="100%" height={400}>
                        <BarChart data={comparisonData.monthly_returns}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                          <YAxis tick={{ fontSize: 12 }} />
                          <Tooltip />
                          <Legend />
                          <Bar
                            dataKey="strategy_return"
                            name="策略收益"
                            fill="#22c55e"
                            radius={[4, 4, 0, 0]}
                          />
                          <Bar
                            dataKey="baseline_return"
                            name="基线收益"
                            fill="#64748b"
                            radius={[4, 4, 0, 0]}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="metrics" className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    {(Array.isArray(comparisonData.metrics) ? comparisonData.metrics : []).map((metric) => (
                      <MetricCard key={metric.name} metric={metric} />
                    ))}
                  </div>

                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Target className="h-5 w-5" />
                        胜率对比
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-3 gap-4">
                        <Card>
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm">做多胜率</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="text-2xl font-bold text-green-600">
                              {(comparisonData.win_rate_comparison.long_win_rate * 100).toFixed(1)}%
                            </div>
                          </CardContent>
                        </Card>
                        <Card>
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm">做空胜率</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="text-2xl font-bold text-red-600">
                              {(comparisonData.win_rate_comparison.short_win_rate * 100).toFixed(1)}%
                            </div>
                          </CardContent>
                        </Card>
                        <Card>
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm">基线胜率</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="text-2xl font-bold text-gray-600">
                              {(comparisonData.win_rate_comparison.baseline_win_rate * 100).toFixed(1)}%
                            </div>
                          </CardContent>
                        </Card>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="trades" className="space-y-4">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Zap className="h-5 w-5" />
                        交易分析
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>指标</TableHead>
                            <TableHead className="text-right">数值</TableHead>
                            <TableHead>指标</TableHead>
                            <TableHead className="text-right">数值</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          <TableRow>
                            <TableCell>总交易次数</TableCell>
                            <TableCell className="text-right font-medium">
                              {comparisonData.trade_analysis.total_trades}
                            </TableCell>
                            <TableCell>盈利交易</TableCell>
                            <TableCell className="text-right font-medium text-green-600">
                              {comparisonData.trade_analysis.winning_trades}
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell>亏损交易</TableCell>
                            <TableCell className="text-right font-medium text-red-600">
                              {comparisonData.trade_analysis.losing_trades}
                            </TableCell>
                            <TableCell>平均盈利</TableCell>
                            <TableCell className="text-right font-medium text-green-600">
                              ¥{comparisonData.trade_analysis.avg_win.toLocaleString()}
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell>平均亏损</TableCell>
                            <TableCell className="text-right font-medium text-red-600">
                              ¥{Math.abs(comparisonData.trade_analysis.avg_loss).toLocaleString()}
                            </TableCell>
                            <TableCell>最大盈利</TableCell>
                            <TableCell className="text-right font-medium text-green-600">
                              ¥{comparisonData.trade_analysis.max_win.toLocaleString()}
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell>最大亏损</TableCell>
                            <TableCell className="text-right font-medium text-red-600">
                              ¥{Math.abs(comparisonData.trade_analysis.max_loss).toLocaleString()}
                            </TableCell>
                            <TableCell>连续盈利</TableCell>
                            <TableCell className="text-right font-medium text-green-600">
                              {comparisonData.trade_analysis.consecutive_wins} 次
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell>连续亏损</TableCell>
                            <TableCell className="text-right font-medium text-red-600">
                              {comparisonData.trade_analysis.consecutive_losses} 次
                            </TableCell>
                            <TableCell></TableCell>
                            <TableCell></TableCell>
                          </TableRow>
                        </TableBody>
                      </Table>
                    </CardContent>
                  </Card>
                </TabsContent>
              </Tabs>
            </>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <TrendingUp className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium">暂无数据</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  该品种缺少足够的历史数据进行回测
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="cross" className="space-y-4">
          {crossLoading ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mb-4" />
                <p className="text-muted-foreground">加载横向对比数据...</p>
              </CardContent>
            </Card>
          ) : allSymbolsData.length > 0 ? (
            <>
              <div className="flex items-center gap-2 mb-4">
                <Badge variant="outline" className="text-base px-3 py-1">
                  共 {allSymbolsData.length} 个品种
                </Badge>
                <Badge variant="secondary" className="text-base px-3 py-1">
                  基线: {baselineStrategies.find(s => s.id === selectedBaseline)?.name || selectedBaseline}
                </Badge>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="h-5 w-5" />
                    多品种横向对比
                  </CardTitle>
                </CardHeader>
                <CardContent className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>品种</TableHead>
                        <TableHead className="text-right">总收益率</TableHead>
                        <TableHead className="text-right">夏普比率</TableHead>
                        <TableHead className="text-right">最大回撤</TableHead>
                        <TableHead className="text-right">卡玛比率</TableHead>
                        <TableHead className="text-right">胜率</TableHead>
                        <TableHead className="text-right">交易次数</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {allSymbolsData.map((row) => {
                        const totalReturn = row.metrics.find(m => m.name === '总收益率')
                        const sharpe = row.metrics.find(m => m.name === '夏普比率')
                        const maxDrawdown = row.metrics.find(m => m.name === '最大回撤')
                        const calmar = row.metrics.find(m => m.name === '卡玛比率')
                        const winRate = row.metrics.find(m => m.name === '胜率')
                        const trades = row.metrics.find(m => m.name === '交易次数')

                        const strategyReturn = totalReturn?.strategy_value || 0
                        const baselineReturn = totalReturn?.baseline_value || 0
                        const returnBetter = strategyReturn > baselineReturn

                        return (
                          <TableRow key={row.symbol}>
                            <TableCell className="font-medium">
                              <Badge variant="outline">{row.symbol}</Badge>
                            </TableCell>
                            <TableCell className={`text-right font-medium ${returnBetter ? 'text-green-600' : 'text-red-600'}`}>
                              {(strategyReturn * 100).toFixed(2)}%
                              <span className="text-xs text-muted-foreground ml-1">
                                ({(baselineReturn * 100).toFixed(2)}%)
                              </span>
                            </TableCell>
                            <TableCell className="text-right">
                              {(sharpe?.strategy_value || 0).toFixed(2)}
                              <span className="text-xs text-muted-foreground ml-1">
                                ({(sharpe?.baseline_value || 0).toFixed(2)})
                              </span>
                            </TableCell>
                            <TableCell className="text-right text-red-600">
                              {((maxDrawdown?.strategy_value || 0) * 100).toFixed(2)}%
                            </TableCell>
                            <TableCell className="text-right">
                              {(calmar?.strategy_value || 0).toFixed(2)}
                            </TableCell>
                            <TableCell className="text-right">
                              {((winRate?.strategy_value || 0) * 100).toFixed(1)}%
                            </TableCell>
                            <TableCell className="text-right">
                              {trades?.strategy_value || 0}
                            </TableCell>
                          </TableRow>
                        )
                      })}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>

              <div className="grid grid-cols-2 gap-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <TrendingUp className="h-5 w-5" />
                      收益率对比
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart
                        data={allSymbolsData.map(row => {
                          const totalReturn = row.metrics.find(m => m.name === '总收益率')
                          return {
                            symbol: row.symbol,
                            strategy: (totalReturn?.strategy_value || 0) * 100,
                            baseline: (totalReturn?.baseline_value || 0) * 100
                          }
                        })}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="symbol" tick={{ fontSize: 12 }} />
                        <YAxis tick={{ fontSize: 12 }} />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="strategy" name="策略" fill="#2563eb" radius={[4, 4, 0, 0]} />
                        <Bar dataKey="baseline" name="基线" fill="#94a3b8" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Activity className="h-5 w-5" />
                      夏普比率对比
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart
                        data={allSymbolsData.map(row => {
                          const sharpe = row.metrics.find(m => m.name === '夏普比率')
                          return {
                            symbol: row.symbol,
                            strategy: sharpe?.strategy_value || 0,
                            baseline: sharpe?.baseline_value || 0
                          }
                        })}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="symbol" tick={{ fontSize: 12 }} />
                        <YAxis tick={{ fontSize: 12 }} />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="strategy" name="策略" fill="#22c55e" radius={[4, 4, 0, 0]} />
                        <Bar dataKey="baseline" name="基线" fill="#94a3b8" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              </div>
            </>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <LayoutGrid className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium">暂无横向对比数据</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  点击"横向对比"标签页加载数据
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}