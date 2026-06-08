import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { Badge } from '../../components/ui/badge'
import { API_BASE_URL } from '../../config'

interface ReplaySession {
  session_id: string
  symbol: string
  start_time: string
  end_time: string
  status: 'idle' | 'running' | 'paused' | 'completed'
  current_time: string
  speed: number
}

export default function ReplayEngine() {
  const [session, setSession] = useState<ReplaySession | null>(null)
  const [loading, setLoading] = useState(false)
  const [symbol, setSymbol] = useState('RB')
  const [startTime, setStartTime] = useState('')
  const [endTime, setEndTime] = useState('')
  const [speed, setSpeed] = useState(1)

  const handleStartReplay = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/replay-engine/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol,
          start_time: startTime,
          end_time: endTime,
          speed,
        }),
      })
      if (res.ok) {
        const data = await res.json()
        setSession(data)
      } else {
        alert('回放启动失败')
      }
    } catch (error) {
      console.error('Failed to start replay:', error)
      alert('回放启动失败')
    } finally {
      setLoading(false)
    }
  }

  const handlePauseReplay = async () => {
    if (!session) return
    try {
      const res = await fetch(`${API_BASE_URL}/replay-engine/pause/${session.session_id}`, {
        method: 'POST',
      })
      if (res.ok) {
        setSession({ ...session, status: 'paused' })
      }
    } catch (error) {
      console.error('Failed to pause replay:', error)
    }
  }

  const handleResumeReplay = async () => {
    if (!session) return
    try {
      const res = await fetch(`${API_BASE_URL}/replay-engine/resume/${session.session_id}`, {
        method: 'POST',
      })
      if (res.ok) {
        setSession({ ...session, status: 'running' })
      }
    } catch (error) {
      console.error('Failed to resume replay:', error)
    }
  }

  const handleStopReplay = async () => {
    if (!session) return
    try {
      const res = await fetch(`${API_BASE_URL}/replay-engine/stop/${session.session_id}`, {
        method: 'POST',
      })
      if (res.ok) {
        setSession(null)
      }
    } catch (error) {
      console.error('Failed to stop replay:', error)
    }
  }

  const handleSetSpeed = async (newSpeed: number) => {
    if (!session) return
    try {
      const res = await fetch(`${API_BASE_URL}/replay-engine/speed/${session.session_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ speed: newSpeed }),
      })
      if (res.ok) {
        setSession({ ...session, speed: newSpeed })
      }
    } catch (error) {
      console.error('Failed to set speed:', error)
    }
  }

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive'> = {
      idle: 'secondary',
      running: 'default',
      paused: 'secondary',
      completed: 'default',
    }
    const labels: Record<string, string> = {
      idle: '空闲',
      running: '运行中',
      paused: '已暂停',
      completed: '已完成',
    }
    return <Badge variant={variants[status]}>{labels[status]}</Badge>
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">历史回放</h1>

      <Card>
        <CardHeader>
          <CardTitle>回放配置</CardTitle>
          <CardDescription>设置历史数据回放参数</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="text-sm font-medium">品种</label>
              <Select value={symbol} onValueChange={setSymbol}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="RB">RB (螺纹钢</SelectItem>
                  <SelectItem value="MA">MA (甲醇)</SelectItem>
                  <SelectItem value="CU">CU (铜)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium">开始时间</label>
              <Input
                type="datetime-local"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium">结束时间</label>
              <Input
                type="datetime-local"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium">回放速度</label>
              <Select value={speed.toString()} onValueChange={(v) => setSpeed(parseInt(v))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">1x</SelectItem>
                  <SelectItem value="2">2x</SelectItem>
                  <SelectItem value="5">5x</SelectItem>
                  <SelectItem value="10">10x</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <Button className="mt-4" onClick={handleStartReplay} disabled={loading || session !== null}>
            {loading ? '启动中..' : '启动回放'}
          </Button>
        </CardContent>
      </Card>

      {session && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>回放状态</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <div className="text-sm text-muted-foreground">品种</div>
                  <div className="text-lg font-medium">{session.symbol}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">状态</div>
                  {getStatusBadge(session.status)}
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">当前时间</div>
                  <div className="text-lg font-medium">{new Date(session.current_time).toLocaleString()}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">回放速度</div>
                  <div className="text-lg font-medium">{session.speed}x</div>
                </div>
              </div>
              <div className="flex gap-2 mt-4">
                {session.status === 'running' && (
                  <Button onClick={handlePauseReplay} variant="outline">
                    暂停
                  </Button>
                )}
                {session.status === 'paused' && (
                  <Button onClick={handleResumeReplay} variant="outline">
                    继续
                  </Button>
                )}
                <Button onClick={handleStopReplay} variant="destructive">
                  停止
                </Button>
                <Select value={session.speed.toString()} onValueChange={(v) => handleSetSpeed(parseInt(v))}>
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">1x</SelectItem>
                    <SelectItem value="2">2x</SelectItem>
                    <SelectItem value="5">5x</SelectItem>
                    <SelectItem value="10">10x</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>回放进度</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="w-full bg-gray-200 rounded-full h-4">
                <div
                  className="bg-blue-600 h-4 rounded-full transition-all"
                  style={{
                    width: `${((new Date(session.current_time).getTime() - new Date(session.start_time).getTime()) /
                      (new Date(session.end_time).getTime() - new Date(session.start_time).getTime())) * 100}%`
                  }}
                />
              </div>
              <div className="mt-2 text-sm text-muted-foreground">
                {new Date(session.start_time).toLocaleString()} - {new Date(session.end_time).toLocaleString()}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
