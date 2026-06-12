import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { API_BASE_URL } from '../../config'
import { SYMBOLS } from '@/constants/symbols'

interface CostAnalysis {
  symbol: string
  commission: number
  slippage: number
  market_impact: number
  total_cost: number
  cost_per_trade: number
}

interface CostBreakdown {
  cost_type: string
  amount: number
  percentage: number
}

export default function TransactionCost() {
  const [analysis, setAnalysis] = useState<CostAnalysis | null>(null)
  const [breakdown, setBreakdown] = useState<CostBreakdown[]>([])
  const [loading, setLoading] = useState(false)
  const [symbol, setSymbol] = useState('RB')
  const [volume, setVolume] = useState(10)

  const fetchAnalysis = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/transaction-cost/analysis/${symbol}`)
      if (res.ok) {
        const data = await res.json()
        setAnalysis(data)
      }
    } catch (error) {
      console.error('Failed to fetch cost analysis:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchBreakdown = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/transaction-cost/breakdown/${symbol}`)
      if (res.ok) {
        const data = await res.json()
        setBreakdown(Array.isArray(data.breakdown) ? data.breakdown : [])
      }
    } catch (error) {
      console.error('Failed to fetch cost breakdown:', error)
    }
  }

  useEffect(() => {
    fetchAnalysis()
    fetchBreakdown()
  }, [symbol])

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">交易成本分析</h1>

      <Card>
        <CardHeader>
          <CardTitle>成本分析参数</CardTitle>
          <CardDescription>设置分析参数</CardDescription>
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
              <label className="text-sm font-medium">交易数量</label>
              <Input
                type="number"
                value={volume}
                onChange={(e) => setVolume(parseInt(e.target.value))}
              />
            </div>
          </div>
          <Button className="mt-4" onClick={fetchAnalysis} disabled={loading}>
            {loading ? '分析中..' : '分析成本'}
          </Button>
        </CardContent>
      </Card>

      {analysis && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">手续费</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{analysis.commission.toFixed(2)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">滑点</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-600">{analysis.slippage.toFixed(2)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">市场冲击</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-600">{analysis.market_impact.toFixed(2)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">总成本</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-600">{analysis.total_cost.toFixed(2)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">单笔成本</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{analysis.cost_per_trade.toFixed(2)}</div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>成本明细</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>成本类型</TableHead>
                    <TableHead>金额</TableHead>
                    <TableHead>占比</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {breakdown.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={3} className="text-center text-muted-foreground">
                        暂无明细
                      </TableCell>
                    </TableRow>
                  ) : (
                    breakdown.map((item, idx) => (
                      <TableRow key={idx}>
                        <TableCell>{item.cost_type}</TableCell>
                        <TableCell>{item.amount.toFixed(2)}</TableCell>
                        <TableCell>{(item.percentage * 100).toFixed(2)}%</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
