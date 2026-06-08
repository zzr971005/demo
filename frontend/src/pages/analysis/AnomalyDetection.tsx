import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Badge } from '../../components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { API_BASE_URL } from '../../config'

interface Anomaly {
  anomaly_id: string
  symbol: string
  anomaly_type: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  description: string
  detected_at: string
  resolved: boolean
}

interface AnomalyConfig {
  threshold_price_change: number
  threshold_volume_spike: number
  enabled: boolean
}

export default function AnomalyDetection() {
  const [anomalies, setAnomalies] = useState<Anomaly[]>([])
  const [config, setConfig] = useState<AnomalyConfig>({
    threshold_price_change: 5.0,
    threshold_volume_spike: 3.0,
    enabled: true,
  })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchAnomalies()
  }, [])

  const fetchAnomalies = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/anomaly-detection/anomalies`)
      if (res.ok) {
        const data = await res.json()
        setAnomalies(Array.isArray(data.anomalies) ? data.anomalies : [])
      }
    } catch (error) {
      console.error('Failed to fetch anomalies:', error)
    }
  }

  const handleResolve = async (anomalyId: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/anomaly-detection/anomalies/${anomalyId}/recover`, {
        method: 'POST',
      })
      if (res.ok) {
        fetchAnomalies()
      }
    } catch (error) {
      console.error('Failed to resolve anomaly:', error)
    }
  }

  const handleUpdateConfig = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/anomaly-detection/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })
      if (res.ok) {
        alert('配置更新成功')
      } else {
        alert('配置更新失败')
      }
    } catch (error) {
      console.error('Failed to update config:', error)
      alert('配置更新失败')
    } finally {
      setLoading(false)
    }
  }

  const getSeverityBadge = (severity: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive'> = {
      low: 'secondary',
      medium: 'default',
      high: 'destructive',
      critical: 'destructive',
    }
    const labels: Record<string, string> = {
      low: '低',
      medium: '中',
      high: '高',
      critical: '严重',
    }
    return <Badge variant={variants[severity]}>{labels[severity]}</Badge>
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">异常监控</h1>

      <Card>
        <CardHeader>
          <CardTitle>异常检测配置</CardTitle>
          <CardDescription>设置异常检测阈值</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-sm font-medium">价格变化阈值%)</label>
              <Input
                type="number"
                step="0.1"
                value={config.threshold_price_change}
                onChange={(e) => setConfig({ ...config, threshold_price_change: parseFloat(e.target.value) })}
              />
            </div>
            <div>
              <label className="text-sm font-medium">成交量激增阈值(%)</label>
              <Input
                type="number"
                step="0.1"
                value={config.threshold_volume_spike}
                onChange={(e) => setConfig({ ...config, threshold_volume_spike: parseFloat(e.target.value) })}
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="enabled"
                checked={config.enabled}
                onChange={(e) => setConfig({ ...config, enabled: e.target.checked })}
              />
              <label htmlFor="enabled">启用异常检测</label>
            </div>
          </div>
          <Button className="mt-4" onClick={handleUpdateConfig} disabled={loading}>
            {loading ? '更新中..' : '更新配置'}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>异常列表</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>异常ID</TableHead>
                <TableHead>品种</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>严重程度</TableHead>
                <TableHead>描述</TableHead>
                <TableHead>检测时间</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {anomalies.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-muted-foreground">
                    暂无异常
                  </TableCell>
                </TableRow>
              ) : (
                anomalies.map((anomaly) => (
                  <TableRow key={anomaly.anomaly_id}>
                    <TableCell>{anomaly.anomaly_id}</TableCell>
                    <TableCell>{anomaly.symbol}</TableCell>
                    <TableCell>{anomaly.anomaly_type}</TableCell>
                    <TableCell>{getSeverityBadge(anomaly.severity)}</TableCell>
                    <TableCell>{anomaly.description}</TableCell>
                    <TableCell>{new Date(anomaly.detected_at).toLocaleString()}</TableCell>
                    <TableCell>
                      <Badge variant={anomaly.resolved ? 'default' : 'destructive'}>
                        {anomaly.resolved ? '已解决' : '未解决'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {!anomaly.resolved && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleResolve(anomaly.anomaly_id)}
                        >
                          解决
                        </Button>
                      )}
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
