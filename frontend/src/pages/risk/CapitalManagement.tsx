import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { API_BASE_URL } from '../../config'

interface CapitalAllocation {
  strategy: string
  weight: number
}

interface PortfolioMetrics {
  annual_return: number
  annual_volatility: number
  sharpe_ratio: number
  max_drawdown: number
}

export default function CapitalManagement() {
  const [allocation, setAllocation] = useState<CapitalAllocation[]>([])
  const [metrics, setMetrics] = useState<PortfolioMetrics>({
    annual_return: 0,
    annual_volatility: 0,
    sharpe_ratio: 0,
    max_drawdown: 0,
  })
  const [loading, setLoading] = useState(false)
  const [allocationMethod, setAllocationMethod] = useState('risk_parity')

  useEffect(() => {
    fetchAllocation()
    fetchMetrics()
  }, [])

  const fetchAllocation = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/capital-management/allocation`)
      if (res.ok) {
        const data = await res.json()
        setAllocation(Array.isArray(data.allocation) ? data.allocation : [])
      }
    } catch (error) {
      console.error('Failed to fetch allocation:', error)
    }
  }

  const fetchMetrics = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/capital-management/portfolio-metrics`)
      if (res.ok) {
        const data = await res.json()
        setMetrics(data)
      }
    } catch (error) {
      console.error('Failed to fetch metrics:', error)
    }
  }

  const handleUpdateAllocation = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/capital-management/allocation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          strategies: allocation,
          allocation_method: allocationMethod,
        }),
      })
      if (res.ok) {
        alert('资金配置更新成功')
        fetchAllocation()
        fetchMetrics()
      } else {
        alert('资金配置更新失败')
      }
    } catch (error) {
      console.error('Failed to update allocation:', error)
      alert('资金配置更新失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">资金管理</h1>

      {/* 组合指标 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">年化收益率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${metrics.annual_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {(metrics.annual_return * 100).toFixed(2)}%
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">年化波动率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(metrics.annual_volatility * 100).toFixed(2)}%</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">夏普比率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.sharpe_ratio.toFixed(2)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">最大回撤</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{(metrics.max_drawdown * 100).toFixed(2)}%</div>
          </CardContent>
        </Card>
      </div>

      {/* 资金配置 */}
      <Card>
        <CardHeader>
          <CardTitle>资金配置</CardTitle>
          <CardDescription>配置各策略的资金分配</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-4">
            <label className="text-sm font-medium">配置方法</label>
            <Select value={allocationMethod} onValueChange={setAllocationMethod}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="risk_parity">风险平价</SelectItem>
                <SelectItem value="equal_weight">等权重</SelectItem>
                <SelectItem value="max_sharpe">最大夏普</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            {allocation.map((item, idx) => (
              <div key={idx} className="flex items-center gap-4">
                <div className="flex-1">
                  <Input
                    placeholder="策略名称"
                    defaultValue={item.strategy}
                    id={`strategy-${idx}`}
                  />
                </div>
                <div className="w-32">
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    placeholder="权重"
                    defaultValue={item.weight}
                    id={`weight-${idx}`}
                  />
                </div>
              </div>
            ))}
          </div>
          <Button
            className="mt-4"
            onClick={() => {
              const newAllocation = allocation.map((_item, idx) => ({
                strategy: (document.getElementById(`strategy-${idx}`) as HTMLInputElement).value,
                weight: parseFloat((document.getElementById(`weight-${idx}`) as HTMLInputElement).value) || 0,
              }))
              setAllocation(newAllocation)
              handleUpdateAllocation()
            }}
            disabled={loading}
          >
            {loading ? '更新中..' : '更新配置'}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
