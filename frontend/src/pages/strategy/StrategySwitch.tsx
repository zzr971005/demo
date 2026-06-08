import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Badge } from '../../components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { API_BASE_URL } from '../../config'

interface StrategyWeight {
  factor_id: string
  symbol: string
  weight: number
}

interface RotationHistory {
  rotation_id: string
  symbol: string
  from_strategies: string[]
  to_strategies: string[]
  rotation_time: string
}

export default function StrategySwitch() {
  const [weights, setWeights] = useState<StrategyWeight[]>([])
  const [history, setHistory] = useState<RotationHistory[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchWeights()
    fetchHistory()
  }, [])

  const fetchWeights = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/strategy-switch/weights`)
      if (res.ok) {
        const data = await res.json()
        setWeights(Array.isArray(data.weights) ? data.weights : [])
      }
    } catch (error) {
      console.error('Failed to fetch weights:', error)
    }
  }

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/strategy-switch/history`)
      if (res.ok) {
        const data = await res.json()
        setHistory(Array.isArray(data.history) ? data.history : [])
      }
    } catch (error) {
      console.error('Failed to fetch history:', error)
    }
  }

  const handleUpdateWeight = async (factorId: string, weight: number) => {
    const item = weights.find(w => w.factor_id === factorId)
    const symbol = item?.symbol || 'default'
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/strategy-switch/weights/${symbol}/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ factor_id: factorId, weight }),
      })
      if (res.ok) {
        alert('权重更新成功')
        fetchWeights()
      } else {
        alert('权重更新失败')
      }
    } catch (error) {
      console.error('Failed to update weight:', error)
      alert('权重更新失败')
    } finally {
      setLoading(false)
    }
  }

  const handleTriggerSwitch = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/strategy-switch/switch`, {
        method: 'POST',
      })
      if (res.ok) {
        alert('策略切换已触发')
        fetchHistory()
      } else {
        alert('策略切换失败')
      }
    } catch (error) {
      console.error('Failed to trigger switch:', error)
      alert('策略切换失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">策略切换</h1>
        <Button onClick={handleTriggerSwitch} disabled={loading}>
          {loading ? '切换中..' : '触发切换'}
        </Button>
      </div>

      {/* 策略权重 */}
      <Card>
        <CardHeader>
          <CardTitle>当前策略权重</CardTitle>
          <CardDescription>调整各策略的权重配置</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>因子ID</TableHead>
                <TableHead>品种</TableHead>
                <TableHead>权重</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {weights.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-muted-foreground">
                    暂无策略权重配置
                  </TableCell>
                </TableRow>
              ) : (
                weights.map((w, idx) => (
                  <TableRow key={idx}>
                    <TableCell>{w.factor_id}</TableCell>
                    <TableCell>{w.symbol}</TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        step="0.01"
                        min="0"
                        max="1"
                        defaultValue={w.weight}
                        className="w-20"
                        id={`weight-${idx}`}
                      />
                    </TableCell>
                    <TableCell>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          const weight = parseFloat((document.getElementById(`weight-${idx}`) as HTMLInputElement).value)
                          handleUpdateWeight(w.factor_id, weight)
                        }}
                        disabled={loading}
                      >
                        更新
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 切换历史 */}
      <Card>
        <CardHeader>
          <CardTitle>切换历史</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>切换ID</TableHead>
                <TableHead>品种</TableHead>
                <TableHead>原策略</TableHead>
                <TableHead>新策略</TableHead>
                <TableHead>切换时间</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {history.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground">
                    暂无切换历史
                  </TableCell>
                </TableRow>
              ) : (
                history.map((h, idx) => (
                  <TableRow key={idx}>
                    <TableCell>{h.rotation_id}</TableCell>
                    <TableCell>{h.symbol}</TableCell>
                    <TableCell>
                      {(Array.isArray(h.from_strategies) ? h.from_strategies : []).map((s, i) => (
                        <Badge key={i} variant="secondary" className="mr-1">
                          {s}
                        </Badge>
                      ))}
                    </TableCell>
                    <TableCell>
                      {(Array.isArray(h.to_strategies) ? h.to_strategies : []).map((s, i) => (
                        <Badge key={i} variant="default" className="mr-1">
                          {s}
                        </Badge>
                      ))}
                    </TableCell>
                    <TableCell>{new Date(h.rotation_time).toLocaleString()}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
