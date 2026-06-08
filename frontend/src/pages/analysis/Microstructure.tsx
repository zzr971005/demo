import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Input } from '../../components/ui/input'
import { Button } from '../../components/ui/button'
import { API_BASE_URL } from '../../config'

interface MicrostructureData {
  symbol: string
  bid_ask_spread: number
  order_flow: number
  liquidity_score: number
  slippage: number
  impact_cost: number
}

export default function Microstructure() {
  const [data, setData] = useState<MicrostructureData | null>(null)
  const [symbol, setSymbol] = useState('RB')
  const [loading, setLoading] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/microstructure/analysis/${symbol}`)
      if (res.ok) {
        const result = await res.json()
        setData(result)
      }
    } catch (error) {
      console.error('Failed to fetch microstructure data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [symbol])

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">市场微观结构</h1>
        <div className="flex gap-2">
          <Input
            placeholder="品种代码"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="w-32"
          />
          <Button onClick={fetchData} disabled={loading}>
            {loading ? '查询中..' : '查询'}
          </Button>
        </div>
      </div>

      {data && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">买卖价差</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{data.bid_ask_spread.toFixed(4)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">订单簿</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{data.order_flow.toFixed(2)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">流动性评分</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{data.liquidity_score.toFixed(2)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">滑点</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-600">{(data.slippage * 100).toFixed(2)}%</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">冲击成本</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-600">{(data.impact_cost * 100).toFixed(2)}%</div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>综合分析</CardTitle>
              <CardDescription>市场微观结构综合指标</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-sm">流动性评分</span>
                    <span className="text-sm font-medium">{data.liquidity_score.toFixed(2)}/100</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full"
                      style={{ width: `${data.liquidity_score}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-sm">滑点水平</span>
                    <span className="text-sm font-medium">{(data.slippage * 100).toFixed(2)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-red-600 h-2 rounded-full"
                      style={{ width: `${Math.min(data.slippage * 1000, 100)}%` }}
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
