import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Input } from '../../components/ui/input'
import { Button } from '../../components/ui/button'
import { API_BASE_URL } from '../../config'

interface MicrostructureData {
  symbol: string
  bid_ask_spread: number | null
  order_flow: number | null
  depth_imbalance: number | null
  volume: number | null
  vwap: number | null
  has_data: boolean
}

const fmt = (v: number | null | undefined, digits: number): string =>
  typeof v === 'number' && isFinite(v) ? v.toFixed(digits) : '—'

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

      {data && data.has_data === false && (
        <Card>
          <CardContent className="py-10 text-center text-muted-foreground">
            暂无 {data.symbol} 的微观结构数据（需接入盘口/成交明细数据后生成）
          </CardContent>
        </Card>
      )}

      {data && data.has_data !== false && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">买卖价差</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{fmt(data.bid_ask_spread, 4)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">订单流</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{fmt(data.order_flow, 2)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">深度失衡</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{fmt(data.depth_imbalance, 2)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">成交量</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{fmt(data.volume, 0)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">VWAP</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{fmt(data.vwap, 2)}</div>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  )
}
