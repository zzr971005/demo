import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { Badge } from '../../components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { API_BASE_URL } from '../../config'
import { SYMBOLS } from '@/constants/symbols'

interface ComparisonResult {
  symbol: string
  backtest_return: number
  live_return: number
  backtest_sharpe: number
  live_sharpe: number
  backtest_drawdown: number
  live_drawdown: number
  correlation: number
  divergence_score: number
}

export default function BacktestLiveComparison() {
  const [results, setResults] = useState<ComparisonResult[]>([])
  const [loading, setLoading] = useState(false)
  const [symbol, setSymbol] = useState('RB')
  const [period, setPeriod] = useState('1m')

  const fetchComparison = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/backtest-live-comparison/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, period }),
      })
      if (res.ok) {
        const data = await res.json()
        setResults([data])
      }
    } catch (error) {
      console.error('Failed to fetch comparison:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchComparison()
  }, [symbol, period])

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">回测实盘对比</h1>

      <Card>
        <CardHeader>
          <CardTitle>对比参数</CardTitle>
          <CardDescription>设置回测与实盘对比参数</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium">品种</label>
              <Select value={symbol} onValueChange={setSymbol}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SYMBOLS.map((s) => (
                    <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium">对比周期</label>
              <Select value={period} onValueChange={setPeriod}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1d">1天</SelectItem>
                  <SelectItem value="1w">1天</SelectItem>
                  <SelectItem value="1m">1天</SelectItem>
                  <SelectItem value="3m">3月</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <Button className="mt-4" onClick={fetchComparison} disabled={loading}>
            {loading ? '对比中..' : '执行对比'}
          </Button>
        </CardContent>
      </Card>

      {results.length > 0 && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">回测收益率</CardTitle>
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${results[0].backtest_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {(results[0].backtest_return * 100).toFixed(2)}%
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">实盘收益率</CardTitle>
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${results[0].live_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {(results[0].live_return * 100).toFixed(2)}%
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">相关性</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{results[0].correlation.toFixed(3)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">偏离度</CardTitle>
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${results[0].divergence_score > 0.2 ? 'text-red-600' : 'text-green-600'}`}>
                  {(results[0].divergence_score * 100).toFixed(2)}%
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>详细对比</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>指标</TableHead>
                    <TableHead>回测</TableHead>
                    <TableHead>实盘</TableHead>
                    <TableHead>差异</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow>
                    <TableCell>收益率</TableCell>
                    <TableCell>{(results[0].backtest_return * 100).toFixed(2)}%</TableCell>
                    <TableCell>{(results[0].live_return * 100).toFixed(2)}%</TableCell>
                    <TableCell>
                      <Badge variant={Math.abs(results[0].backtest_return - results[0].live_return) < 0.05 ? 'default' : 'destructive'}>
                        {((results[0].backtest_return - results[0].live_return) * 100).toFixed(2)}%
                      </Badge>
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>夏普比率</TableCell>
                    <TableCell>{results[0].backtest_sharpe.toFixed(2)}</TableCell>
                    <TableCell>{results[0].live_sharpe.toFixed(2)}</TableCell>
                    <TableCell>
                      <Badge variant={Math.abs(results[0].backtest_sharpe - results[0].live_sharpe) < 0.5 ? 'default' : 'destructive'}>
                        {(results[0].backtest_sharpe - results[0].live_sharpe).toFixed(2)}
                      </Badge>
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>最大回撤</TableCell>
                    <TableCell>{(results[0].backtest_drawdown * 100).toFixed(2)}%</TableCell>
                    <TableCell>{(results[0].live_drawdown * 100).toFixed(2)}%</TableCell>
                    <TableCell>
                      <Badge variant={Math.abs(results[0].backtest_drawdown - results[0].live_drawdown) < 0.05 ? 'default' : 'destructive'}>
                        {((results[0].backtest_drawdown - results[0].live_drawdown) * 100).toFixed(2)}%
                      </Badge>
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
