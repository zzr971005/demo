import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Badge } from '../../components/ui/badge'
import { API_BASE_URL } from '../../config'

interface LiquidityAnalysis {
  symbol: string
  liquidity_score: number
  market_depth: number
  price_impact: number
  volume_profile: number
  risk_level: 'low' | 'medium' | 'high'
}

export default function LiquidityRisk() {
  const [analysis, setAnalysis] = useState<LiquidityAnalysis | null>(null)
  const [loading, setLoading] = useState(false)
  const [symbol, setSymbol] = useState('RB')
  const [orderVolume, setOrderVolume] = useState(10)

  const fetchAnalysis = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/liquidity-risk/analysis/${symbol}`)
      if (res.ok) {
        const data = await res.json()
        setAnalysis(data)
      }
    } catch (error) {
      console.error('Failed to fetch liquidity analysis:', error)
    } finally {
      setLoading(false)
    }
  }

  const checkOrderLiquidity = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/liquidity-risk/check-order`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, volume: orderVolume }),
      })
      if (res.ok) {
        const data = await res.json()
        setAnalysis(data)
      }
    } catch (error) {
      console.error('Failed to check order liquidity:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAnalysis()
  }, [symbol])

  const getRiskBadge = (level: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive'> = {
      low: 'default',
      medium: 'secondary',
      high: 'destructive',
    }
    const labels: Record<string, string> = {
      low: '低',
      medium: '中',
      high: '高',
    }
    return <Badge variant={variants[level]}>{labels[level]}</Badge>
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">流动性风险管理</h1>

      <Card>
        <CardHeader>
          <CardTitle>订单流动性检查</CardTitle>
          <CardDescription>检查订单的流动性风险</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium">品种</label>
              <Input
                placeholder="品种代码"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium">订单数量</label>
              <Input
                type="number"
                value={orderVolume}
                onChange={(e) => setOrderVolume(parseInt(e.target.value))}
              />
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <Button onClick={fetchAnalysis} disabled={loading}>
              {loading ? '分析中..' : '分析流动性'}
            </Button>
            <Button onClick={checkOrderLiquidity} disabled={loading} variant="outline">
              {loading ? '检查中...' : '检查订单'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {analysis && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">流动性评分</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{analysis.liquidity_score.toFixed(2)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">市场深度</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{analysis.market_depth.toFixed(2)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">价格冲击</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-600">{(analysis.price_impact * 100).toFixed(2)}%</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">成交量分析</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{analysis.volume_profile.toFixed(2)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">风险等级</CardTitle>
              </CardHeader>
              <CardContent>
                {getRiskBadge(analysis.risk_level)}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>综合评估</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-sm">流动性评分</span>
                    <span className="text-sm font-medium">{analysis.liquidity_score.toFixed(2)}/100</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full"
                      style={{ width: `${analysis.liquidity_score}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-sm">价格冲击</span>
                    <span className="text-sm font-medium">{(analysis.price_impact * 100).toFixed(2)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-red-600 h-2 rounded-full"
                      style={{ width: `${Math.min(analysis.price_impact * 1000, 100)}%` }}
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
