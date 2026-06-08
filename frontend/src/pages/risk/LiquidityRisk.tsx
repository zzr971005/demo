import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Badge } from '../../components/ui/badge'
import { API_BASE_URL } from '../../config'

interface LiquidityAnalysis {
  symbol: string
  liquidity_ratio?: number
  amihud_illiquidity?: number
  risk_score?: number
  // check-order 响应字段
  passes?: boolean
  message?: string
  volume_ratio?: number
}

const fmt = (v: number | null | undefined, digits: number): string =>
  typeof v === 'number' && isFinite(v) ? v.toFixed(digits) : '—'

const riskLevelFromScore = (score: number | undefined): 'low' | 'medium' | 'high' => {
  const s = score ?? 0
  if (s > 0.7) return 'high'
  if (s > 0.4) return 'medium'
  return 'low'
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
          {analysis.message && (
            <Card>
              <CardContent className="py-4">
                <Badge variant={analysis.passes ? 'default' : 'destructive'}>
                  {analysis.passes ? '通过' : '未通过'}
                </Badge>
                <span className="ml-3 text-sm">{analysis.message}</span>
              </CardContent>
            </Card>
          )}

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">流动性比率</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{fmt(analysis.liquidity_ratio, 2)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Amihud 非流动性</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{fmt(analysis.amihud_illiquidity, 4)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">风险评分</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-600">{fmt(analysis.risk_score, 2)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">风险等级</CardTitle>
              </CardHeader>
              <CardContent>
                {getRiskBadge(riskLevelFromScore(analysis.risk_score))}
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
                    <span className="text-sm">风险评分</span>
                    <span className="text-sm font-medium">{fmt(analysis.risk_score, 2)}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-red-600 h-2 rounded-full"
                      style={{ width: `${Math.min((analysis.risk_score ?? 0) * 100, 100)}%` }}
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
