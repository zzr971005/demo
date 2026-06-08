import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { API_BASE_URL } from '../../config'

interface OptimizationResult {
  strategies: string[]
  weights: number[]
  expected_return: number
  expected_volatility: number
  sharpe_ratio: number
}

export default function PortfolioOptimization() {
  const [result, setResult] = useState<OptimizationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [method, setMethod] = useState('max_sharpe')
  const [riskFreeRate, setRiskFreeRate] = useState(0.03)

  const handleOptimize = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/portfolio-optimization/optimize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          method,
          risk_free_rate: riskFreeRate,
        }),
      })
      if (res.ok) {
        const data = await res.json()
        setResult(data)
      }
    } catch (error) {
      console.error('Failed to optimize portfolio:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">组合优化</h1>

      <Card>
        <CardHeader>
          <CardTitle>优化参数</CardTitle>
          <CardDescription>设置组合优化参数</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium">优化方法</label>
              <Select value={method} onValueChange={setMethod}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="max_sharpe">最大夏普</SelectItem>
                  <SelectItem value="min_variance">最小方差</SelectItem>
                  <SelectItem value="equal_weight">等权重</SelectItem>
                  <SelectItem value="risk_parity">风险平价</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium">无风险利率</label>
              <Input
                type="number"
                step="0.01"
                value={riskFreeRate}
                onChange={(e) => setRiskFreeRate(parseFloat(e.target.value))}
              />
            </div>
          </div>
          <Button className="mt-4" onClick={handleOptimize} disabled={loading}>
            {loading ? '优化中..' : '执行优化'}
          </Button>
        </CardContent>
      </Card>

      {result && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">预期收益</CardTitle>
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${result.expected_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {(result.expected_return * 100).toFixed(2)}%
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">预期波动</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{(result.expected_volatility * 100).toFixed(2)}%</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">夏普比率</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{result.sharpe_ratio.toFixed(2)}</div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>权重分配</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {(Array.isArray(result.strategies) ? result.strategies : []).map((strategy, idx) => (
                  <div key={idx} className="flex items-center gap-4">
                    <div className="flex-1">{strategy}</div>
                    <div className="w-48">
                      <div className="flex justify-between mb-1">
                        <span className="text-sm">权重</span>
                        <span className="text-sm font-medium">{(result.weights[idx] * 100).toFixed(2)}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full"
                          style={{ width: `${result.weights[idx] * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
