import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Label } from '../../components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { Badge } from '../../components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { API_BASE_URL } from '../../config'

interface SimulationStatus {
  is_running: boolean
  total_pnl: number
  total_trades: number
  win_rate: number
  sharpe_ratio: number
  max_drawdown: number
}

interface Position {
  symbol: string
  direction: 'long' | 'short'
  volume: number
  entry_price: number
  current_price: number
  pnl: number
}

interface Order {
  order_id: string
  symbol: string
  direction: 'long' | 'short'
  offset: 'open' | 'close'
  volume: number
  price: number
  status: 'pending' | 'filled' | 'cancelled'
  created_at: string
}

export default function Simulation() {
  const [status, setStatus] = useState<SimulationStatus>({
    is_running: false,
    total_pnl: 0,
    total_trades: 0,
    win_rate: 0,
    sharpe_ratio: 0,
    max_drawdown: 0,
  })
  const [positions, setPositions] = useState<Position[]>([])
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(false)

  const [orderForm, setOrderForm] = useState({
    symbol: 'RB',
    direction: 'long' as 'long' | 'short',
    offset: 'open' as 'open' | 'close',
    volume: 1,
    price: 0,
  })

  useEffect(() => {
    fetchStatus()
    fetchPositions()
    fetchOrders()
  }, [])

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/simulation/status`)
      if (res.ok) {
        const data = await res.json()
        setStatus((prev) => ({
          is_running: data.is_running ?? prev.is_running,
          total_pnl: data.total_pnl ?? prev.total_pnl,
          total_trades: data.total_trades ?? prev.total_trades,
          win_rate: data.win_rate ?? prev.win_rate,
          sharpe_ratio: data.sharpe_ratio ?? prev.sharpe_ratio,
          max_drawdown: data.max_drawdown ?? prev.max_drawdown,
        }))
      }
    } catch (error) {
      console.error('Failed to fetch simulation status:', error)
    }
  }

  const fetchPositions = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/simulation/positions`)
      if (res.ok) {
        const data = await res.json()
        setPositions(Array.isArray(data.positions) ? data.positions : [])
      }
    } catch (error) {
      console.error('Failed to fetch positions:', error)
    }
  }

  const fetchOrders = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/simulation/orders`)
      if (res.ok) {
        const data = await res.json()
        setOrders(Array.isArray(data.orders) ? data.orders : [])
      }
    } catch (error) {
      console.error('Failed to fetch orders:', error)
    }
  }

  const handleSubmitOrder = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/simulation/order`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(orderForm),
      })
      if (res.ok) {
        const data = await res.json()
        alert(`订单提交成功: ${data.order_id}`)
        fetchOrders()
        fetchPositions()
        fetchStatus()
      } else {
        alert('订单提交失败')
      }
    } catch (error) {
      console.error('Failed to submit order:', error)
      alert('订单提交失败')
    } finally {
      setLoading(false)
    }
  }

  const handleStartStop = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/simulation/start`, {
        method: 'POST',
      })
      if (res.ok) {
        fetchStatus()
      }
    } catch (error) {
      console.error('Failed to start/stop simulation:', error)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">模拟交易</h1>
        <Button
          onClick={handleStartStop}
          variant={status.is_running ? 'destructive' : 'default'}
        >
          {status.is_running ? '停止模拟' : '启动模拟'}
        </Button>
      </div>

      {/* 状态卡片*/}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">总盈亏</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${status.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {status.total_pnl.toFixed(2)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">交易次数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{status.total_trades}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">胜率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(status.win_rate * 100).toFixed(1)}%</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">夏普比率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{status.sharpe_ratio.toFixed(2)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">最大回撤</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{(status.max_drawdown * 100).toFixed(2)}%</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">状态</CardTitle>
          </CardHeader>
          <CardContent>
            <Badge variant={status.is_running ? 'default' : 'secondary'}>
              {status.is_running ? '运行中' : '已停止'}
            </Badge>
          </CardContent>
        </Card>
      </div>

      {/* 订单提交表单 */}
      <Card>
        <CardHeader>
          <CardTitle>提交模拟订单</CardTitle>
          <CardDescription>在模拟环境中测试交易策略</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div>
              <Label htmlFor="symbol">品种</Label>
              <Select
                value={orderForm.symbol}
                onValueChange={(value) => setOrderForm({ ...orderForm, symbol: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="RB">RB (螺纹钢</SelectItem>
                  <SelectItem value="MA">MA (甲醇)</SelectItem>
                  <SelectItem value="CU">CU (铜)</SelectItem>
                  <SelectItem value="AL">AL (铝)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="direction">方向</Label>
              <Select
                value={orderForm.direction}
                onValueChange={(value: 'long' | 'short') => setOrderForm({ ...orderForm, direction: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="long">做多</SelectItem>
                  <SelectItem value="short">做空</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="offset">开仓</Label>
              <Select
                value={orderForm.offset}
                onValueChange={(value: 'open' | 'close') => setOrderForm({ ...orderForm, offset: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="open">开仓</SelectItem>
                  <SelectItem value="close">平仓</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="volume">数量</Label>
              <Input
                id="volume"
                type="number"
                value={orderForm.volume}
                onChange={(e) => setOrderForm({ ...orderForm, volume: parseInt(e.target.value) })}
              />
            </div>
            <div>
              <Label htmlFor="price">价格</Label>
              <Input
                id="price"
                type="number"
                step="0.01"
                value={orderForm.price || ''}
                onChange={(e) => setOrderForm({ ...orderForm, price: parseFloat(e.target.value) })}
              />
            </div>
          </div>
          <Button
            className="mt-4"
            onClick={handleSubmitOrder}
            disabled={loading}
          >
            {loading ? '提交中..' : '提交订单'}
          </Button>
        </CardContent>
      </Card>

      {/* 持仓列表 */}
      <Card>
        <CardHeader>
          <CardTitle>模拟持仓</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>品种</TableHead>
                <TableHead>方向</TableHead>
                <TableHead>数量</TableHead>
                <TableHead>开仓价</TableHead>
                <TableHead>当前值</TableHead>
                <TableHead>盈亏</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {positions.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground">
                    暂无持仓
                  </TableCell>
                </TableRow>
              ) : (
                positions.map((pos, idx) => (
                  <TableRow key={idx}>
                    <TableCell>{pos.symbol}</TableCell>
                    <TableCell>
                      <Badge variant={pos.direction === 'long' ? 'default' : 'destructive'}>
                        {pos.direction === 'long' ? '做多' : '做空'}
                      </Badge>
                    </TableCell>
                    <TableCell>{pos.volume}</TableCell>
                    <TableCell>{pos.entry_price.toFixed(2)}</TableCell>
                    <TableCell>{pos.current_price.toFixed(2)}</TableCell>
                    <TableCell className={pos.pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                      {pos.pnl.toFixed(2)}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 订单记录 */}
      <Card>
        <CardHeader>
          <CardTitle>订单记录</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>订单ID</TableHead>
                <TableHead>品种</TableHead>
                <TableHead>方向</TableHead>
                <TableHead>开仓</TableHead>
                <TableHead>数量</TableHead>
                <TableHead>价格</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>时间</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {orders.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-muted-foreground">
                    暂无订单
                  </TableCell>
                </TableRow>
              ) : (
                orders.map((order) => (
                  <TableRow key={order.order_id}>
                    <TableCell>{order.order_id}</TableCell>
                    <TableCell>{order.symbol}</TableCell>
                    <TableCell>
                      <Badge variant={order.direction === 'long' ? 'default' : 'destructive'}>
                        {order.direction === 'long' ? '做多' : '做空'}
                      </Badge>
                    </TableCell>
                    <TableCell>{order.offset === 'open' ? '开仓' : '平仓'}</TableCell>
                    <TableCell>{order.volume}</TableCell>
                    <TableCell>{order.price.toFixed(2)}</TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          order.status === 'filled'
                            ? 'default'
                            : order.status === 'pending'
                            ? 'secondary'
                            : 'destructive'
                        }
                      >
                        {order.status === 'filled' ? '已成交' : order.status === 'pending' ? '待成交' : '已取消'}
                      </Badge>
                    </TableCell>
                    <TableCell>{new Date(order.created_at).toLocaleString()}</TableCell>
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
