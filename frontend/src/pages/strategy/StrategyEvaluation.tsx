import { useState, useEffect } from 'react'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  BarChart3,
  TrendingUp,
  Target,
  Network,
  Sparkles,
  Shield,
  Award,
  Info,
  PieChart,
  Calculator,
} from 'lucide-react'
import api from '@/lib/api'

interface StrategyScoreDetail {
  id: string
  symbol: string
  formula: string
  sharpe_test: number
  calmar: number
  max_drawdown: number
  win_rate: number
  total_trades: number
  score_components: {
    name: string
    weight: number
    value: number
    contribution: number
  }[]
  total_score: number
  rank: number
}

interface ScoringRule {
  name: string
  weight: number
  description: string
  is_better_higher: boolean
  formula: string
}

const SCORING_RULES: ScoringRule[] = [
  {
    name: '夏普比率(测试集)',
    weight: 0.40,
    description: '衡量风险调整后收益，越高越好',
    is_better_higher: true,
    formula: 'sharpe_test',
  },
  {
    name: '卡玛比率',
    weight: 0.20,
    description: '收益/最大回撤，衡量回报风险比',
    is_better_higher: true,
    formula: 'calmar',
  },
  {
    name: '最大回撤',
    weight: 0.20,
    description: '控制下行风险，越小越好',
    is_better_higher: false,
    formula: '1 - |max_drawdown|',
  },
  {
    name: '胜率',
    weight: 0.10,
    description: '盈利交易占比，越高越好',
    is_better_higher: true,
    formula: 'win_rate',
  },
  {
    name: '样本充足度',
    weight: 0.10,
    description: '交易次数充足性，≥30次为满分',
    is_better_higher: true,
    formula: 'min(total_trades/30, 1)',
  },
]

const ALL_SYMBOLS = [
  'RB', 'I', 'J', 'JM',
  'MA', 'TA', 'FG', 'SR', 'PP', 'L',
  'IF', 'IC', 'IH', 'IM'
]

function ScoreBar({ value, maxValue, color, label }: { value: number; maxValue: number; color: string; label: string }) {
  const percentage = (value / maxValue) * 100
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">{value.toFixed(4)}</span>
      </div>
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${Math.min(percentage, 100)}%`, backgroundColor: color }}
        />
      </div>
    </div>
  )
}

function ScorePieChart({ components }: { components: { name: string; contribution: number; color: string }[] }) {
  const total = components.reduce((sum, c) => sum + c.contribution, 0) || 1
  
  let currentAngle = 0
  const paths = components.map((comp, index) => {
    const angle = (comp.contribution / total) * 360
    const startAngle = currentAngle
    currentAngle += angle
    
    const startRad = (startAngle - 90) * (Math.PI / 180)
    const endRad = (currentAngle - 90) * (Math.PI / 180)
    
    const x1 = 50 + 40 * Math.cos(startRad)
    const y1 = 50 + 40 * Math.sin(startRad)
    const x2 = 50 + 40 * Math.cos(endRad)
    const y2 = 50 + 40 * Math.sin(endRad)
    
    const largeArcFlag = angle > 180 ? 1 : 0
    
    const pathData = `M 50 50 L ${x1} ${y1} A 40 40 0 ${largeArcFlag} 1 ${x2} ${y2} Z`
    
    return { ...comp, pathData, index }
  })

  return (
    <div className="flex flex-col items-center">
      <svg width="120" height="120" viewBox="0 0 100 100" className="mb-3">
        {paths.map(p => (
          <path
            key={p.index}
            d={p.pathData}
            fill={p.color}
            className="transition-all duration-300 hover:opacity-80"
          />
        ))}
        <circle cx="50" cy="50" r="25" fill="white" />
        <text x="50" y="48" textAnchor="middle" className="text-xs font-bold fill-gray-800">
          {total.toFixed(2)}
        </text>
        <text x="50" y="58" textAnchor="middle" className="text-[8px] fill-gray-500">
          综合得分
        </text>
      </svg>
    </div>
  )
}

export default function StrategyEvaluationPage() {
  const [selectedSymbol, setSelectedSymbol] = useState('RB')
  const [strategyScores, setStrategyScores] = useState<StrategyScoreDetail[]>([])
  const [selectedStrategy, setSelectedStrategy] = useState<StrategyScoreDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [correlationMatrix, setCorrelationMatrix] = useState<any>(null)
  const [generatedStrategies, setGeneratedStrategies] = useState<any>(null)

  useEffect(() => {
    fetchStrategyScores()
  }, [selectedSymbol])

  const fetchStrategyScores = async () => {
    setLoading(true)
    try {
      const response = await api.get(`/strategy/evaluation/${selectedSymbol}`)
      setStrategyScores(response.data)
      if (response.data.length > 0) {
        setSelectedStrategy(response.data[0])
      }
    } catch (error) {
      console.error('Failed to fetch strategy scores:', error)
      setStrategyScores([])
    } finally {
      setLoading(false)
    }
  }

  const fetchCorrelationMatrix = async () => {
    try {
      const response = await api.get(`/strategy/correlation-matrix?symbol=${selectedSymbol}`)
      setCorrelationMatrix(response.data)
    } catch (error) {
      console.error('Failed to fetch correlation matrix:', error)
    }
  }

  const generateStrategies = async () => {
    try {
      const response = await api.post(`/strategy/generate-strategies?symbol=${selectedSymbol}`)
      setGeneratedStrategies(response.data)
    } catch (error) {
      console.error('Failed to generate strategies:', error)
    }
  }

  const COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6']

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
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Award className="h-6 w-6" />
            策略评选机制
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            展示策略评分计算过程，让评选透明可见
          </p>
        </div>
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
      </div>

      <Tabs defaultValue="methodology" className="space-y-4">
        <TabsList>
          <TabsTrigger value="methodology" className="flex items-center gap-2">
            <Calculator className="h-4 w-4" />
            评选方法论
          </TabsTrigger>
          <TabsTrigger value="rankings" className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            策略排名
          </TabsTrigger>
          <TabsTrigger value="details" className="flex items-center gap-2">
            <PieChart className="h-4 w-4" />
            得分详情
          </TabsTrigger>
          <TabsTrigger value="correlation" className="flex items-center gap-2">
            <Network className="h-4 w-4" />
            相关性验证
          </TabsTrigger>
          <TabsTrigger value="strategy-generation" className="flex items-center gap-2">
            <Sparkles className="h-4 w-4" />
            策略生成
          </TabsTrigger>
        </TabsList>

        <TabsContent value="methodology" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Info className="h-5 w-5" />
                综合评分公式
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-6 mb-6">
                <div className="text-center">
                  <div className="text-lg font-mono bg-white px-4 py-2 rounded-lg inline-block shadow-sm">
                    <span className="text-primary font-bold">Score</span> =
                    <span className="text-blue-600"> 0.40×</span>sharpe_test +
                    <span className="text-green-600"> 0.20×</span>calmar +
                    <span className="text-amber-600"> 0.20×</span>(1-|max_drawdown|) +
                    <span className="text-red-600"> 0.10×</span>win_rate +
                    <span className="text-purple-600"> 0.10×</span>sample_score
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {SCORING_RULES.map((rule, index) => (
                  <Card key={rule.name} className="border-l-4" style={{ borderLeftColor: COLORS[index] }}>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium flex items-center justify-between">
                        <span>{rule.name}</span>
                        <Badge variant="secondary">{(rule.weight * 100).toFixed(0)}%</Badge>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm text-muted-foreground mb-2">{rule.description}</p>
                      <div className="text-xs font-mono bg-gray-50 px-2 py-1 rounded">
                        {rule.formula}
                      </div>
                      <div className="mt-2 flex items-center gap-2 text-xs">
                        {rule.is_better_higher ? (
                          <span className="flex items-center gap-1 text-green-600">
                            <TrendingUp className="h-3 w-3" /> 越高越好
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-red-600">
                            <TrendingUp className="h-3 w-3" /> 越低越好
                          </span>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>

              <Card className="mt-4">
                <CardHeader>
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Target className="h-4 w-4" />
                    评分规则说明
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <p>
                    <span className="font-medium">夏普比率(测试集)</span>: 使用测试集数据计算，避免过拟合影响，权重最高(40%)。
                  </p>
                  <p>
                    <span className="font-medium">卡玛比率</span>: 年化收益除以最大回撤，衡量策略的风险调整后回报能力(20%)。
                  </p>
                  <p>
                    <span className="font-medium">最大回撤</span>: 使用(1-回撤值)转换，控制下行风险(20%)。
                  </p>
                  <p>
                    <span className="font-medium">胜率</span>: 盈利交易占总交易的比例，反映策略稳定性(10%)。
                  </p>
                  <p>
                    <span className="font-medium">样本充足度</span>: 交易次数不足30次时评分打折，确保统计显著性(10%)。
                  </p>
                </CardContent>
              </Card>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="rankings" className="space-y-4">
          {strategyScores.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  {selectedSymbol} 策略排名
                  <Badge variant="outline">共 {strategyScores.length} 个策略</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {strategyScores.map((strategy, index) => (
                    <Card
                      key={strategy.id}
                      className={`cursor-pointer transition-all ${
                        selectedStrategy?.id === strategy.id
                          ? 'ring-2 ring-primary'
                          : 'hover:shadow-md'
                      }`}
                      onClick={() => setSelectedStrategy(strategy)}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-4">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
                              index === 0 ? 'bg-yellow-100 text-yellow-600' :
                              index === 1 ? 'bg-gray-100 text-gray-600' :
                              index === 2 ? 'bg-amber-100 text-amber-600' :
                              'bg-gray-50 text-gray-500'
                            }`}>
                              {index + 1}
                            </div>
                            <div>
                              <div className="font-medium text-sm">{strategy.formula}</div>
                              <div className="text-xs text-muted-foreground">
                                夏普: {strategy.sharpe_test.toFixed(2)} | 回撤: {(strategy.max_drawdown * 100).toFixed(1)}% | 交易: {strategy.total_trades}次
                              </div>
                            </div>
                          </div>
                          <div className="text-right">
                            <div className={`text-xl font-bold ${
                              index === 0 ? 'text-yellow-600' :
                              index === 1 ? 'text-gray-600' :
                              index === 2 ? 'text-amber-600' :
                              'text-gray-800'
                            }`}>
                              {strategy.total_score.toFixed(4)}
                            </div>
                            <div className="text-xs text-muted-foreground">综合得分</div>
                          </div>
                        </div>
                        <div className="mt-3 flex gap-2">
                          {(Array.isArray(strategy.score_components) ? strategy.score_components : []).map((comp, idx) => (
                            <div key={comp.name} className="flex items-center gap-1 text-xs">
                              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[idx] }} />
                              <span className="text-muted-foreground">{comp.name}</span>
                              <span className="font-medium">{comp.contribution.toFixed(3)}</span>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Award className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium">暂无策略数据</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  {selectedSymbol} 品种尚未完成进化或暂无候选策略
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="details" className="space-y-4">
          {selectedStrategy ? (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <Card className="lg:col-span-2">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <PieChart className="h-5 w-5" />
                    策略得分详情
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                    <div className="text-sm text-muted-foreground mb-1">策略表达式</div>
                    <div className="font-mono text-base">{selectedStrategy.formula}</div>
                  </div>

                  <div className="space-y-4">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">夏普比率(测试集)</span>
                      <span className="font-medium">{selectedStrategy.sharpe_test.toFixed(4)}</span>
                    </div>
                    <ScoreBar
                      value={selectedStrategy.sharpe_test}
                      maxValue={3}
                      color="#3b82f6"
                      label="夏普比率得分"
                    />

                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">卡玛比率</span>
                      <span className="font-medium">{selectedStrategy.calmar.toFixed(4)}</span>
                    </div>
                    <ScoreBar
                      value={selectedStrategy.calmar}
                      maxValue={3}
                      color="#22c55e"
                      label="卡玛比率得分"
                    />

                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">最大回撤</span>
                      <span className="font-medium text-red-600">{(selectedStrategy.max_drawdown * 100).toFixed(2)}%</span>
                    </div>
                    <ScoreBar
                      value={1 - Math.abs(selectedStrategy.max_drawdown)}
                      maxValue={1}
                      color="#f59e0b"
                      label="回撤调整得分"
                    />

                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">胜率</span>
                      <span className="font-medium">{(selectedStrategy.win_rate * 100).toFixed(1)}%</span>
                    </div>
                    <ScoreBar
                      value={selectedStrategy.win_rate}
                      maxValue={1}
                      color="#ef4444"
                      label="胜率得分"
                    />

                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">交易次数</span>
                      <span className="font-medium">{selectedStrategy.total_trades} 次</span>
                    </div>
                    <ScoreBar
                      value={Math.min(selectedStrategy.total_trades / 30, 1)}
                      maxValue={1}
                      color="#8b5cf6"
                      label="样本充足度得分"
                    />

                    <div className="pt-4 border-t border-gray-200">
                      <div className="flex items-center justify-between">
                        <span className="text-lg font-medium">综合得分</span>
                        <span className="text-2xl font-bold text-primary">
                          {selectedStrategy.total_score.toFixed(4)}
                        </span>
                      </div>
                      <div className="mt-2 h-3 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-1000"
                          style={{ width: `${Math.min(selectedStrategy.total_score * 25, 100)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">得分构成</CardTitle>
                </CardHeader>
                <CardContent>
                  <ScorePieChart
                    components={(Array.isArray(selectedStrategy.score_components) ? selectedStrategy.score_components : []).map((comp, idx) => ({
                      name: comp.name,
                      contribution: comp.contribution,
                      color: COLORS[idx],
                    }))}
                  />
                  <div className="space-y-2">
                    {(Array.isArray(selectedStrategy.score_components) ? selectedStrategy.score_components : []).map((comp, idx) => (
                      <div key={comp.name} className="flex items-center justify-between text-sm">
                        <div className="flex items-center gap-2">
                          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[idx] }} />
                          <span className="text-muted-foreground">{comp.name}</span>
                        </div>
                        <span className="font-medium">{comp.contribution.toFixed(4)}</span>
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-2 text-sm">
                      <Shield className="h-4 w-4 text-green-600" />
                      <span className="text-green-600 font-medium">排名 #{selectedStrategy.rank}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <PieChart className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium">请选择一个策略</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  在"策略排名"标签页中点击策略查看详细得分构成
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="correlation" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Network className="h-5 w-5" />
                因子相关性验证
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  计算IC筛选的前50个因子之间的相关性矩阵
                </p>
                <Button onClick={fetchCorrelationMatrix} size="sm">
                  <Network className="h-4 w-4 mr-1" />
                  计算相关性
                </Button>
              </div>

              {correlationMatrix && correlationMatrix.factors.length > 0 ? (
                <div className="space-y-2">
                  <div className="text-sm font-medium">
                    共 {correlationMatrix.factors.length} 个因子
                  </div>
                  <div className="max-h-96 overflow-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b">
                          <th className="p-2 text-left">因子</th>
                          {correlationMatrix.factors.slice(0, 10).map((f: { id: string; formula: string }) => (
                            <th key={f.id} className="p-2 text-xs">
                              {f.formula.substring(0, 10)}...
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {correlationMatrix.factors.slice(0, 10).map((f1: { id: string; formula: string }, i: number) => (
                          <tr key={f1.id} className="border-b">
                            <td className="p-2 font-mono text-xs">
                              {f1.formula.substring(0, 15)}...
                            </td>
                            {correlationMatrix.factors.slice(0, 10).map((f2: { id: string }, j: number) => {
                              const corr = correlationMatrix.matrix[i]?.[j] || 0
                              const bgColor = corr > 0.7 ? 'bg-red-100' : corr < -0.7 ? 'bg-blue-100' : 'bg-gray-50'
                              return (
                                <td key={f2.id} className={`p-2 text-center ${bgColor}`}>
                                  {corr.toFixed(2)}
                                </td>
                              )
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  点击"计算相关性"按钮开始计算
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="strategy-generation" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5" />
                策略生成
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  从前50个IC筛选因子中选择5个策略，考虑相关性
                </p>
                <Button onClick={generateStrategies} size="sm">
                  <Sparkles className="h-4 w-4 mr-1" />
                  生成策略
                </Button>
              </div>

              {generatedStrategies && generatedStrategies.strategies.length > 0 ? (
                <div className="space-y-2">
                  <div className="text-sm font-medium">
                    从 {generatedStrategies.total_factors} 个因子中选择了 {generatedStrategies.selected_count} 个策略
                  </div>
                  {(Array.isArray(generatedStrategies.strategies) ? generatedStrategies.strategies : []).map((strategy: { id: string; formula: string; sharpe: number; ic_mean_24h: number; sharpe_train: number; total_score: number }) => (
                    <Card key={strategy.id}>
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <code className="block text-sm font-mono bg-muted p-2 rounded mb-2">
                              {strategy.formula}
                            </code>
                            <div className="grid grid-cols-3 gap-4 text-sm">
                              <div>
                                <div className="text-muted-foreground">IC 24h</div>
                                <div className="font-semibold">{strategy.ic_mean_24h?.toFixed(3)}</div>
                              </div>
                              <div>
                                <div className="text-muted-foreground">Sharpe</div>
                                <div className="font-semibold">{strategy.sharpe_train?.toFixed(2)}</div>
                              </div>
                              <div>
                                <div className="text-muted-foreground">综合得分</div>
                                <div className="font-semibold">{strategy.total_score?.toFixed(4)}</div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  点击"生成策略"按钮开始生成
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}