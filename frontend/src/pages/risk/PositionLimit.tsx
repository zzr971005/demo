import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { API_BASE_URL } from '../../config'

interface PositionLimit {
  symbol: string
  max_volume: number
  max_margin_ratio: number
  current_volume: number
  current_margin_ratio: number
}

export default function PositionLimit() {
  const [limits, setLimits] = useState<PositionLimit[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchLimits()
  }, [])

  const fetchLimits = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/position-limit/config`)
      if (res.ok) {
        const data = await res.json()
        setLimits(Array.isArray(data.limits) ? data.limits : [])
      }
    } catch (error) {
      console.error('Failed to fetch position limits:', error)
    }
  }

  const handleUpdateLimit = async (symbol: string, maxVolume: number, maxMarginRatio: number) => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/position-limit/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, max_volume: maxVolume, max_margin_ratio: maxMarginRatio }),
      })
      if (res.ok) {
        alert('仓位配置更新成功')
        fetchLimits()
      } else {
        alert('仓位配置更新失败')
      }
    } catch (error) {
      console.error('Failed to update limit:', error)
      alert('仓位配置更新失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">仓位配置</h1>

      <Card>
        <CardHeader>
          <CardTitle>品种仓位限制</CardTitle>
          <CardDescription>设置各品种的最大持仓量和保证金比例</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>品种</TableHead>
                <TableHead>最大持仓量</TableHead>
                <TableHead>最大保证金比例</TableHead>
                <TableHead>当前持仓量</TableHead>
                <TableHead>当前保证金比例</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {limits.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground">
                    暂无配置
                  </TableCell>
                </TableRow>
              ) : (
                limits.map((limit, idx) => (
                  <TableRow key={idx}>
                    <TableCell>{limit.symbol}</TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        defaultValue={limit.max_volume}
                        className="w-20"
                        id={`max-volume-${idx}`}
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        step="0.01"
                        defaultValue={limit.max_margin_ratio}
                        className="w-20"
                        id={`max-margin-${idx}`}
                      />
                    </TableCell>
                    <TableCell>{limit.current_volume}</TableCell>
                    <TableCell>{(limit.current_margin_ratio * 100).toFixed(1)}%</TableCell>
                    <TableCell>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          const maxVolume = parseFloat((document.getElementById(`max-volume-${idx}`) as HTMLInputElement).value)
                          const maxMarginRatio = parseFloat((document.getElementById(`max-margin-${idx}`) as HTMLInputElement).value)
                          handleUpdateLimit(limit.symbol, maxVolume, maxMarginRatio)
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
    </div>
  )
}
