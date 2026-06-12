import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Badge } from '../../components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { API_BASE_URL } from '../../config'

interface Alert {
  alert_id: number
  symbol: string
  alert_type: string
  level: 'info' | 'warning' | 'error' | 'critical'
  message: string
  acknowledged: boolean
  created_at: string
}

interface AlertConfig {
  email_enabled: boolean
  sms_enabled: boolean
  webhook_url: string
}

export default function AlertSystem() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [config, setConfig] = useState<AlertConfig>({
    email_enabled: false,
    sms_enabled: false,
    webhook_url: '',
  })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchAlerts()
    fetchConfig()
  }, [])

  const fetchAlerts = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/alert-system/history`)
      if (res.ok) {
        const data = await res.json()
        setAlerts(Array.isArray(data.alerts) ? data.alerts : [])
      }
    } catch (error) {
      console.error('Failed to fetch alerts:', error)
    }
  }

  const fetchConfig = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/alert-system/config`)
      if (res.ok) {
        const data = await res.json()
        setConfig(data)
      }
    } catch (error) {
      console.error('Failed to fetch config:', error)
    }
  }

  const handleAcknowledge = async (alertId: number) => {
    try {
      const res = await fetch(`${API_BASE_URL}/alert-system/alerts/${alertId}/acknowledge`, {
        method: 'POST',
      })
      if (res.ok) {
        fetchAlerts()
      }
    } catch (error) {
      console.error('Failed to acknowledge alert:', error)
    }
  }

  const handleUpdateConfig = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/alert-system/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })
      if (res.ok) {
        alert('告警配置更新成功')
      } else {
        alert('告警配置更新失败')
      }
    } catch (error) {
      console.error('Failed to update config:', error)
      alert('告警配置更新失败')
    } finally {
      setLoading(false)
    }
  }

  const getLevelBadge = (level: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive'> = {
      info: 'secondary',
      warning: 'default',
      error: 'destructive',
      critical: 'destructive',
    }
    const labels: Record<string, string> = {
      info: '信息',
      warning: '警告',
      error: '错误',
      critical: '严重',
    }
    return <Badge variant={variants[level]}>{labels[level]}</Badge>
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">告警管理</h1>

      {/* 告警配置 */}
      <Card>
        <CardHeader>
          <CardTitle>告警配置</CardTitle>
          <CardDescription>配置告警通知方式</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="email-enabled"
                checked={config.email_enabled}
                onChange={(e) => setConfig({ ...config, email_enabled: e.target.checked })}
              />
              <label htmlFor="email-enabled">启用邮件通知</label>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="sms-enabled"
                checked={config.sms_enabled}
                onChange={(e) => setConfig({ ...config, sms_enabled: e.target.checked })}
              />
              <label htmlFor="sms-enabled">启用短信通知</label>
            </div>
            <div>
              <Input
                placeholder="Webhook URL"
                value={config.webhook_url}
                onChange={(e) => setConfig({ ...config, webhook_url: e.target.value })}
              />
            </div>
          </div>
          <Button className="mt-4" onClick={handleUpdateConfig} disabled={loading}>
            {loading ? '更新中..' : '更新配置'}
          </Button>
        </CardContent>
      </Card>

      {/* 告警列表 */}
      <Card>
        <CardHeader>
          <CardTitle>告警列表</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>告警ID</TableHead>
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
              {alerts.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-muted-foreground">
                    暂无告警
                  </TableCell>
                </TableRow>
              ) : (
                alerts.map((alert) => (
                  <TableRow key={alert.alert_id}>
                    <TableCell>{alert.alert_id}</TableCell>
                    <TableCell>{alert.symbol}</TableCell>
                    <TableCell>{alert.alert_type}</TableCell>
                    <TableCell>{getLevelBadge(alert.level)}</TableCell>
                    <TableCell>{alert.message}</TableCell>
                    <TableCell>
                      <Badge variant={alert.acknowledged ? 'default' : 'destructive'}>
                        {alert.acknowledged ? '已确认' : '未确认'}
                      </Badge>
                    </TableCell>
                    <TableCell>{new Date(alert.created_at).toLocaleString()}</TableCell>
                    <TableCell>
                      {!alert.acknowledged && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleAcknowledge(alert.alert_id)}
                        >
                          确认
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
