import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Label } from '../../components/ui/label'
import { Badge } from '../../components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { API_BASE_URL } from '../../config'

interface RiskEvent {
  event_id: number
  symbol: string
  event_type: string
  level: 'low' | 'medium' | 'high' | 'critical'
  message: string
  resolved: boolean
  created_at: string
}

interface RiskConfig {
  max_total_margin_ratio: number
  daily_max_loss_ratio: number
  max_drawdown_ratio: number
}

interface RiskSummary {
  total_events: number
  unresolved_events: number
  critical_events: number
}

export default function RiskManagement() {
  const [events, setEvents] = useState<RiskEvent[]>([])
  const [summary, setSummary] = useState<RiskSummary>({
    total_events: 0,
    unresolved_events: 0,
    critical_events: 0,
  })
  const [config, setConfig] = useState<RiskConfig>({
    max_total_margin_ratio: 0.8,
    daily_max_loss_ratio: 0.05,
    max_drawdown_ratio: 0.2,
  })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchEvents()
    fetchSummary()
  }, [])

  const fetchEvents = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/risk-management/events`)
      if (res.ok) {
        const data = await res.json()
        setEvents(Array.isArray(data.events) ? data.events : [])
      }
    } catch (error) {
      console.error('Failed to fetch risk events:', error)
    }
  }

  const fetchSummary = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/risk-management/summary`)
      if (res.ok) {
        const data = await res.json()
        setSummary(data)
      }
    } catch (error) {
      console.error('Failed to fetch risk summary:', error)
    }
  }

  const handleUpdateConfig = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/risk-management/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })
      if (res.ok) {
        alert('风控配置更新成功')
      } else {
        alert('风控配置更新失败')
      }
    } catch (error) {
      console.error('Failed to update config:', error)
      alert('风控配置更新失败')
    } finally {
      setLoading(false)
    }
  }

  const handleResolveEvent = async (eventId: number) => {
    try {
      const res = await fetch(`${API_BASE_URL}/risk-management/events/${eventId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ handler: 'user', action: 'resolve' }),
      })
      if (res.ok) {
        fetchEvents()
        fetchSummary()
      }
    } catch (error) {
      console.error('Failed to resolve event:', error)
    }
  }

  const getLevelBadge = (level: string) => {
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
    return <Badge variant={variants[level]}>{labels[level]}</Badge>
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">风控管理</h1>

      {/* 风控摘要 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">总事件数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary.total_events}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">未解决事件</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{summary.unresolved_events}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">严重事件</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{summary.critical_events}</div>
          </CardContent>
        </Card>
      </div>

      {/* 风控配置 */}
      <Card>
        <CardHeader>
          <CardTitle>风控配置</CardTitle>
          <CardDescription>设置风控参数</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <Label htmlFor="max_margin">最大保证金比例</Label>
              <Input
                id="max_margin"
                type="number"
                step="0.01"
                value={config.max_total_margin_ratio}
                onChange={(e) => setConfig({ ...config, max_total_margin_ratio: parseFloat(e.target.value) })}
              />
            </div>
            <div>
              <Label htmlFor="daily_loss">日最大亏损比例</Label>
              <Input
                id="daily_loss"
                type="number"
                step="0.01"
                value={config.daily_max_loss_ratio}
                onChange={(e) => setConfig({ ...config, daily_max_loss_ratio: parseFloat(e.target.value) })}
              />
            </div>
            <div>
              <Label htmlFor="max_drawdown">最大回撤比例</Label>
              <Input
                id="max_drawdown"
                type="number"
                step="0.01"
                value={config.max_drawdown_ratio}
                onChange={(e) => setConfig({ ...config, max_drawdown_ratio: parseFloat(e.target.value) })}
              />
            </div>
          </div>
          <Button className="mt-4" onClick={handleUpdateConfig} disabled={loading}>
            {loading ? '更新中..' : '更新配置'}
          </Button>
        </CardContent>
      </Card>

      {/* 风控事件列表 */}
      <Card>
        <CardHeader>
          <CardTitle>风控事件</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>事件ID</TableHead>
                <TableHead>品种</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>级别</TableHead>
                <TableHead>消息</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {events.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-muted-foreground">
                    暂无风控事件
                  </TableCell>
                </TableRow>
              ) : (
                events.map((event) => (
                  <TableRow key={event.event_id}>
                    <TableCell>{event.event_id}</TableCell>
                    <TableCell>{event.symbol}</TableCell>
                    <TableCell>{event.event_type}</TableCell>
                    <TableCell>{getLevelBadge(event.level)}</TableCell>
                    <TableCell>{event.message}</TableCell>
                    <TableCell>
                      <Badge variant={event.resolved ? 'default' : 'destructive'}>
                        {event.resolved ? '已解决' : '未解决'}
                      </Badge>
                    </TableCell>
                    <TableCell>{new Date(event.created_at).toLocaleString()}</TableCell>
                    <TableCell>
                      {!event.resolved && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleResolveEvent(event.event_id)}
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
