import { useState, useEffect } from 'react'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'

import { Button } from '../../components/ui/button'

import { Input } from '../../components/ui/input'

import { Badge } from '../../components/ui/badge'

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'

import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs'

import { API_BASE_URL } from '../../config'



interface CorrelationMatrix {

  symbols: string[]

  matrix: number[][]

  avg_correlation: number

}



interface HighCorrelationPair {

  symbol1: string

  symbol2: string

  correlation: number

}



interface DiversificationSuggestion {

  symbol: string

  current_weight: number

  suggested_weight: number

  reason: string

}



interface StrategyPair {
  a: string
  b: string
  label_a: string
  label_b: string
  correlation?: number
}

interface StrategyCorrelation {
  strategy_ids: string[]
  labels: string[]
  matrix: number[][]
  avg_abs_corr: number
  high_corr_pairs: StrategyPair[]
  identical_pairs: StrategyPair[]
  overlap_points: number
  skipped: { id: string; reason: string }[]
  message?: string
}

interface Top2Selected {
  id: string
  formula: string
  strategy_rank: number
  quality_score: number
  sharpe: number
  calmar: number
  dsr: number
  total_trades: number
}

interface Top2SymbolResult {
  symbol: string
  n_candidates: number
  selected: Top2Selected[]
  top2_correlation: number | null
  warnings: string[]
}

interface PortfolioResult {
  method: string
  strategy_ids?: string[]
  labels: Record<string, string>
  weights: Record<string, number>
  overlap_points?: number
  metrics: {
    annual_return?: number
    annual_volatility?: number
    sharpe_ratio?: number
    max_drawdown?: number
  }
  message?: string
}



export default function CorrelationAnalysis() {

  const [matrix, setMatrix] = useState<CorrelationMatrix | null>(null)

  const [highCorrelations, setHighCorrelations] = useState<HighCorrelationPair[]>([])

  const [suggestions, setSuggestions] = useState<DiversificationSuggestion[]>([])

  const [loading, setLoading] = useState(false)

  const [symbols, setSymbols] = useState<string[]>(['RB', 'MA', 'CU', 'AL'])

  const [stratMatrix, setStratMatrix] = useState<StrategyCorrelation | null>(null)

  const [stratLoading, setStratLoading] = useState(false)

  const [stratScope, setStratScope] = useState<string>('all')

  const [stratSymbols, setStratSymbols] = useState<string>('')

  const [stratThreshold, setStratThreshold] = useState<number>(0.5)

  const [top2Loading, setTop2Loading] = useState(false)

  const [top2Result, setTop2Result] = useState<Top2SymbolResult[] | null>(null)

  const [portfolioMethod, setPortfolioMethod] = useState<string>('hrp')

  const [portfolioLoading, setPortfolioLoading] = useState(false)

  const [portfolio, setPortfolio] = useState<PortfolioResult | null>(null)



  const fetchPortfolio = async () => {

    setPortfolioLoading(true)

    try {

      const syms = stratSymbols.split(',').map((s) => s.trim()).filter(Boolean)

      const body: Record<string, unknown> = { scope: stratScope, method: portfolioMethod }

      if (syms.length > 0) body.symbols = syms

      const res = await fetch(`${API_BASE_URL}/strategy-correlation/portfolio`, {

        method: 'POST',

        headers: { 'Content-Type': 'application/json' },

        body: JSON.stringify(body),

      })

      if (res.ok) {

        setPortfolio(await res.json())

      }

    } catch (error) {

      console.error('Failed to fetch portfolio weights:', error)

    } finally {

      setPortfolioLoading(false)

    }

  }



  const runTop2Selection = async (persist: boolean) => {

    setTop2Loading(true)

    try {

      const syms = stratSymbols.split(',').map((s) => s.trim()).filter(Boolean)

      const body: Record<string, unknown> = { persist, tau_corr: stratThreshold }

      if (syms.length > 0) body.symbols = syms

      const res = await fetch(`${API_BASE_URL}/strategy-correlation/select-top2`, {

        method: 'POST',

        headers: { 'Content-Type': 'application/json' },

        body: JSON.stringify(body),

      })

      if (res.ok) {

        const data = await res.json()

        setTop2Result(Array.isArray(data.results) ? data.results : [])

      }

    } catch (error) {

      console.error('Failed to run top2 selection:', error)

    } finally {

      setTop2Loading(false)

    }

  }



  const fetchStrategyMatrix = async () => {

    setStratLoading(true)

    try {

      const body: Record<string, unknown> = { scope: stratScope, threshold: stratThreshold, limit: 50 }

      const syms = stratSymbols.split(',').map((s) => s.trim()).filter(Boolean)

      if (syms.length > 0) body.symbols = syms

      const res = await fetch(`${API_BASE_URL}/strategy-correlation/matrix`, {

        method: 'POST',

        headers: { 'Content-Type': 'application/json' },

        body: JSON.stringify(body),

      })

      if (res.ok) {

        setStratMatrix(await res.json())

      }

    } catch (error) {

      console.error('Failed to fetch strategy correlation matrix:', error)

    } finally {

      setStratLoading(false)

    }

  }



  const fetchMatrix = async () => {

    setLoading(true)

    try {

      const res = await fetch(`${API_BASE_URL}/correlation-analysis/matrix`, {

        method: 'POST',

        headers: { 'Content-Type': 'application/json' },

        body: JSON.stringify({ symbols, period: '1d' }),

      })

      if (res.ok) {

        const data = await res.json()

        setMatrix(data)

      }

    } catch (error) {

      console.error('Failed to fetch correlation matrix:', error)

    } finally {

      setLoading(false)

    }

  }



  const fetchHighCorrelations = async () => {

    try {

      const res = await fetch(`${API_BASE_URL}/correlation-analysis/highly-correlated`)

      if (res.ok) {

        const data = await res.json()

        setHighCorrelations(Array.isArray(data.pairs) ? data.pairs : [])

      }

    } catch (error) {

      console.error('Failed to fetch high correlations:', error)

    }

  }



  const fetchSuggestions = async () => {

    try {

      const res = await fetch(`${API_BASE_URL}/correlation-analysis/diversify`)

      if (res.ok) {

        const data = await res.json()

        setSuggestions(Array.isArray(data.suggestions) ? data.suggestions : [])

      }

    } catch (error) {

      console.error('Failed to fetch diversification suggestions:', error)

    }

  }



  useEffect(() => {

    fetchMatrix()

    fetchHighCorrelations()

    fetchSuggestions()

  }, [])



  return (

    <div className="p-6 space-y-6">

      <h1 className="text-3xl font-bold">相关性分析</h1>

      <Tabs defaultValue="symbol" className="space-y-6">

        <TabsList>

          <TabsTrigger value="symbol">品种相关度</TabsTrigger>

          <TabsTrigger value="strategy">策略相关度</TabsTrigger>

        </TabsList>

        <TabsContent value="symbol" className="space-y-6">

      <Card>

        <CardHeader>

          <CardTitle>相关性矩阵</CardTitle>

          <CardDescription>分析品种间的相关性</CardDescription>

        </CardHeader>

        <CardContent>

          <div className="mb-4">

            <label className="text-sm font-medium">品种列表（逗号分隔）</label>

            <Input

              placeholder="RB,MA,CU,AL"

              value={symbols.join(',')}

              onChange={(e) => setSymbols(e.target.value.split(',').map(s => s.trim()))}

            />

          </div>

          <Button onClick={fetchMatrix} disabled={loading}>

            {loading ? '计算中..' : '计算相关性'}

          </Button>

        </CardContent>

      </Card>



      {matrix && (

        <>

          <Card>

            <CardHeader>

              <CardTitle>相关性矩阵</CardTitle>

            </CardHeader>

            <CardContent>

              <div className="overflow-x-auto">

                <table className="w-full">

                  <thead>

                    <tr>

                      <th className="p-2"></th>

                      {(matrix.symbols || []).map((s, i) => (

                        <th key={i} className="p-2">{s}</th>

                      ))}

                    </tr>

                  </thead>

                  <tbody>

                    {(matrix.matrix || []).map((row, i) => (

                      <tr key={i}>

                        <td className="p-2 font-medium">{(matrix.symbols || [])[i]}</td>

                        {row.map((val, j) => (

                          <td

                            key={j}

                            className="p-2 text-center"

                            style={{

                              backgroundColor: `rgba(${val > 0 ? '0, 100, 255' : '255, 0, 0'}, ${Math.abs(val)})`,

                              color: Math.abs(val) > 0.5 ? 'white' : 'black',

                            }}

                          >

                            {val.toFixed(2)}

                          </td>

                        ))}

                      </tr>

                    ))}

                  </tbody>

                </table>

              </div>

              <div className="mt-4">

                <span className="text-sm">平均相关性 </span>

                <span className="font-bold">{matrix.avg_correlation.toFixed(3)}</span>

              </div>

            </CardContent>

          </Card>



          <Card>

            <CardHeader>

              <CardTitle>高相关性策略对</CardTitle>

            </CardHeader>

            <CardContent>

              <Table>

                <TableHeader>

                  <TableRow>

                    <TableHead>品种1</TableHead>

                    <TableHead>品种2</TableHead>

                    <TableHead>相关性</TableHead>

                  </TableRow>

                </TableHeader>

                <TableBody>

                  {highCorrelations.length === 0 ? (

                    <TableRow>

                      <TableCell colSpan={3} className="text-center text-muted-foreground">

                        暂无高相关性策略对

                      </TableCell>

                    </TableRow>

                  ) : (

                    highCorrelations.map((pair, idx) => (

                      <TableRow key={idx}>

                        <TableCell>{pair.symbol1}</TableCell>

                        <TableCell>{pair.symbol2}</TableCell>

                        <TableCell>

                          <Badge variant={pair.correlation > 0.8 ? 'destructive' : 'default'}>

                            {pair.correlation.toFixed(3)}

                          </Badge>

                        </TableCell>

                      </TableRow>

                    ))

                  )}

                </TableBody>

              </Table>

            </CardContent>

          </Card>



          <Card>

            <CardHeader>

              <CardTitle>分散化建议</CardTitle>

            </CardHeader>

            <CardContent>

              <Table>

                <TableHeader>

                  <TableRow>

                    <TableHead>品种</TableHead>

                    <TableHead>当前权重</TableHead>

                    <TableHead>建议权重</TableHead>

                    <TableHead>原因</TableHead>

                  </TableRow>

                </TableHeader>

                <TableBody>

                  {suggestions.length === 0 ? (

                    <TableRow>

                      <TableCell colSpan={4} className="text-center text-muted-foreground">

                        暂无建议

                      </TableCell>

                    </TableRow>

                  ) : (

                    suggestions.map((sug, idx) => (

                      <TableRow key={idx}>

                        <TableCell>{sug.symbol}</TableCell>

                        <TableCell>{(sug.current_weight * 100).toFixed(1)}%</TableCell>

                        <TableCell>{(sug.suggested_weight * 100).toFixed(1)}%</TableCell>

                        <TableCell>{sug.reason}</TableCell>

                      </TableRow>

                    ))

                  )}

                </TableBody>

              </Table>

            </CardContent>

          </Card>

        </>

      )}

        </TabsContent>

        <TabsContent value="strategy" className="space-y-6">

          <Card>

            <CardHeader>

              <CardTitle>策略相关度矩阵</CardTitle>

              <CardDescription>基于最新多因子策略在真实行情上重建的收益序列实时构建（策略×策略）</CardDescription>

            </CardHeader>

            <CardContent className="space-y-4">

              <div className="flex flex-wrap items-end gap-3">

                <div>

                  <label className="text-sm font-medium">策略范围</label>

                  <select

                    className="block h-9 rounded-md border border-input bg-background px-3 text-sm"

                    value={stratScope}

                    onChange={(e) => setStratScope(e.target.value)}

                  >

                    <option value="all">全部候选</option>

                    <option value="selected">已选策略</option>

                    <option value="deployed">已部署</option>

                  </select>

                </div>

                <div>

                  <label className="text-sm font-medium">品种过滤（可选，逗号分隔）</label>

                  <Input placeholder="RB,MA" value={stratSymbols} onChange={(e) => setStratSymbols(e.target.value)} />

                </div>

                <div>

                  <label className="text-sm font-medium">高相关阈值</label>

                  <Input

                    type="number"

                    step="0.05"

                    value={stratThreshold}

                    onChange={(e) => setStratThreshold(parseFloat(e.target.value) || 0.5)}

                  />

                </div>

                <Button onClick={fetchStrategyMatrix} disabled={stratLoading}>

                  {stratLoading ? '计算中..' : '构建策略相关度'}

                </Button>

                <Button variant="outline" onClick={() => runTop2Selection(false)} disabled={top2Loading}>

                  {top2Loading ? '计算中..' : '每品种 Top2（预览）'}

                </Button>

                <Button variant="outline" onClick={() => runTop2Selection(true)} disabled={top2Loading}>

                  每品种 Top2（落库）

                </Button>

              </div>

            </CardContent>

          </Card>

          {top2Result && (

            <Card>

              <CardHeader>

                <CardTitle>每品种 Top2 低相关多因子策略</CardTitle>

                <CardDescription>质量分（夏普/Calmar/IC_IR）+ DSR&gt;0 硬门槛 + top2 间低相关（|ρ| &lt; 阈值）</CardDescription>

              </CardHeader>

              <CardContent className="space-y-4">

                {top2Result.length === 0 && (

                  <div className="text-sm text-muted-foreground">暂无可选策略</div>

                )}

                {top2Result.map((r) => (

                  <div key={r.symbol} className="border rounded-md p-3">

                    <div className="font-medium mb-2">

                      {r.symbol}（候选 {r.n_candidates}{r.top2_correlation != null ? ` · top2 相关性 ${r.top2_correlation.toFixed(3)}` : ''}）

                    </div>

                    {r.selected.length === 0 ? (

                      <div className="text-sm text-muted-foreground">无满足条件的策略</div>

                    ) : (

                      <Table>

                        <TableHeader>

                          <TableRow>

                            <TableHead>排名</TableHead>

                            <TableHead>公式</TableHead>

                            <TableHead>质量分</TableHead>

                            <TableHead>夏普</TableHead>

                            <TableHead>DSR</TableHead>

                            <TableHead>交易数</TableHead>

                          </TableRow>

                        </TableHeader>

                        <TableBody>

                          {r.selected.map((s) => (

                            <TableRow key={s.id}>

                              <TableCell><Badge>#{s.strategy_rank}</Badge></TableCell>

                              <TableCell className="font-mono text-xs">{s.formula}</TableCell>

                              <TableCell>{s.quality_score.toFixed(3)}</TableCell>

                              <TableCell>{s.sharpe.toFixed(3)}</TableCell>

                              <TableCell>{s.dsr.toFixed(3)}</TableCell>

                              <TableCell>{s.total_trades}</TableCell>

                            </TableRow>

                          ))}

                        </TableBody>

                      </Table>

                    )}

                    {r.warnings.length > 0 && (

                      <div className="mt-2 text-xs text-amber-600">{r.warnings.join('；')}</div>

                    )}

                  </div>

                ))}

              </CardContent>

            </Card>

          )}

          <Card>

            <CardHeader>

              <CardTitle>组合权重优化</CardTitle>

              <CardDescription>对当前范围内策略按真实收益序列做组合权重分配（HRP / IC_IR / 风险平价）</CardDescription>

            </CardHeader>

            <CardContent className="space-y-4">

              <div className="flex flex-wrap items-end gap-3">

                <div>

                  <label className="text-sm font-medium">方法</label>

                  <select

                    className="block h-9 rounded-md border border-input bg-background px-3 text-sm"

                    value={portfolioMethod}

                    onChange={(e) => setPortfolioMethod(e.target.value)}

                  >

                    <option value="hrp">HRP 层次风险平价</option>

                    <option value="ic_ir">IC_IR 加权</option>

                    <option value="risk_parity">风险平价</option>

                    <option value="sharpe">最大夏普</option>

                    <option value="equal">等权重</option>

                  </select>

                </div>

                <Button onClick={fetchPortfolio} disabled={portfolioLoading}>

                  {portfolioLoading ? '计算中..' : '计算组合权重'}

                </Button>

              </div>

              {portfolio && portfolio.message && (

                <div className="text-sm text-muted-foreground">{portfolio.message}</div>

              )}

              {portfolio && !portfolio.message && (

                <>

                  <div className="text-sm text-muted-foreground">

                    年化收益 {(portfolio.metrics.annual_return ?? 0).toFixed(3)} · 年化波动 {(portfolio.metrics.annual_volatility ?? 0).toFixed(3)} · 夏普 {(portfolio.metrics.sharpe_ratio ?? 0).toFixed(3)} · 最大回撤 {(portfolio.metrics.max_drawdown ?? 0).toFixed(3)}

                  </div>

                  <Table>

                    <TableHeader>

                      <TableRow>

                        <TableHead>策略</TableHead>

                        <TableHead>权重</TableHead>

                      </TableRow>

                    </TableHeader>

                    <TableBody>

                      {Object.entries(portfolio.weights).map(([id, w]) => (

                        <TableRow key={id}>

                          <TableCell>{portfolio.labels[id] || id}</TableCell>

                          <TableCell>{(w * 100).toFixed(1)}%</TableCell>

                        </TableRow>

                      ))}

                    </TableBody>

                  </Table>

                </>

              )}

            </CardContent>

          </Card>

          {stratMatrix && stratMatrix.strategy_ids.length >= 2 && (

            <>

              <Card>

                <CardHeader>

                  <CardTitle>策略相关度矩阵</CardTitle>

                  <CardDescription>

                    重叠样本点 {stratMatrix.overlap_points} · 平均|相关性| {stratMatrix.avg_abs_corr.toFixed(3)}

                  </CardDescription>

                </CardHeader>

                <CardContent>

                  <div className="overflow-x-auto">

                    <table className="w-full text-xs">

                      <thead>

                        <tr>

                          <th className="p-2"></th>

                          {stratMatrix.strategy_ids.map((_, i) => (

                            <th key={i} className="p-2">S{i + 1}</th>

                          ))}

                        </tr>

                      </thead>

                      <tbody>

                        {stratMatrix.matrix.map((row, i) => (

                          <tr key={i}>

                            <td className="p-2 font-medium whitespace-nowrap">S{i + 1} · {stratMatrix.labels[i]}</td>

                            {row.map((val, j) => (

                              <td

                                key={j}

                                className="p-2 text-center"

                                style={{

                                  backgroundColor: `rgba(${val > 0 ? '0, 100, 255' : '255, 0, 0'}, ${Math.abs(val)})`,

                                  color: Math.abs(val) > 0.5 ? 'white' : 'black',

                                }}

                              >

                                {val.toFixed(2)}

                              </td>

                            ))}

                          </tr>

                        ))}

                      </tbody>

                    </table>

                  </div>

                </CardContent>

              </Card>

              {stratMatrix.identical_pairs.length > 0 && (

                <Card>

                  <CardHeader>

                    <CardTitle className="text-red-600">⚠ 异常：不同策略收益完全相同</CardTitle>

                    <CardDescription>表达式不同但收益序列一致，通常意味着信号等价或存在 bug</CardDescription>

                  </CardHeader>

                  <CardContent>

                    {stratMatrix.identical_pairs.map((p, idx) => (

                      <div key={idx} className="text-sm">{p.label_a} ≡ {p.label_b}</div>

                    ))}

                  </CardContent>

                </Card>

              )}

              <Card>

                <CardHeader>

                  <CardTitle>高相关策略对</CardTitle>

                </CardHeader>

                <CardContent>

                  <Table>

                    <TableHeader>

                      <TableRow>

                        <TableHead>策略A</TableHead>

                        <TableHead>策略B</TableHead>

                        <TableHead>相关性</TableHead>

                      </TableRow>

                    </TableHeader>

                    <TableBody>

                      {stratMatrix.high_corr_pairs.length === 0 ? (

                        <TableRow>

                          <TableCell colSpan={3} className="text-center text-muted-foreground">暂无高相关策略对</TableCell>

                        </TableRow>

                      ) : (

                        stratMatrix.high_corr_pairs.map((pair, idx) => (

                          <TableRow key={idx}>

                            <TableCell>{pair.label_a}</TableCell>

                            <TableCell>{pair.label_b}</TableCell>

                            <TableCell>

                              <Badge variant={Math.abs(pair.correlation || 0) > 0.8 ? 'destructive' : 'default'}>

                                {(pair.correlation || 0).toFixed(3)}

                              </Badge>

                            </TableCell>

                          </TableRow>

                        ))

                      )}

                    </TableBody>

                  </Table>

                </CardContent>

              </Card>

            </>

          )}

          {stratMatrix && stratMatrix.strategy_ids.length < 2 && (

            <Card>

              <CardContent className="py-6 text-center text-muted-foreground">

                {stratMatrix.message || '可用策略不足 2 个，无法构建相关度矩阵'}

              </CardContent>

            </Card>

          )}

        </TabsContent>

      </Tabs>

    </div>

  )

}

