import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { Badge } from '../../components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { API_BASE_URL } from '../../config'

interface OrderType {
  type_id: string
  name: string
  description: string
  enabled: boolean
}

interface Order {
  order_id: string
  symbol: string
  order_type: string
  direction: 'long' | 'short'
  volume: number
  price: number
  status: 'pending' | 'filled' | 'cancelled'
  created_at: string
}

export default function OrderTypes() {
  const [orderTypes, setOrderTypes] = useState<OrderType[]>([])
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(false)

  const [orderForm, setOrderForm] = useState({
    symbol: 'RB',
    order_type: 'market',
    direction: 'long' as 'long' | 'short',
    volume: 1,
    price: 0,
  })

  useEffect(() => {
    fetchOrderTypes()
    fetchOrders()
  }, [])

  const fetchOrderTypes = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/order-types/types`)
      if (res.ok) {
        const data = await res.json()
        setOrderTypes(Array.isArray(data.types) ? data.types : [])
      }
    } catch (error) {
      console.error('Failed to fetch order types:', error)
    }
  }

  const fetchOrders = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/order-types/orders`)
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
      const res = await fetch(`${API_BASE_URL}/order-types/order`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(orderForm),
      })
      if (res.ok) {
        alert('订单提交成功')
        fetchOrders()
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

  const handleToggleType = async (typeId: string, enabled: boolean) => {
    try {
      const res = await fetch(`${API_BASE_URL}/order-types/types/${typeId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      })
      if (res.ok) {
        fetchOrderTypes()
      }
    } catch (error) {
      console.error('Failed to toggle order type:', error)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">订单类型管理</h1>

      {/* 订单类型配置 */}
      <Card>
        <CardHeader>
          <CardTitle>订单类型</CardTitle>
          <CardDescription>启用或禁用不同的订单类型</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>类型ID</TableHead>
                <TableHead>名称</TableHead>
                <TableHead>描述</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {orderTypes.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground">
                    暂无订单类型
                  </TableCell>
                </TableRow>
              ) : (
                orderTypes.map((type) => (
                  <TableRow key={type.type_id}>
                    <TableCell>{type.type_id}</TableCell>
                    <TableCell>{type.name}</TableCell>
                    <TableCell>{type.description}</TableCell>
                    <TableCell>
                      <Badge variant={type.enabled ? 'default' : 'secondary'}>
                        {type.enabled ? '已启用' : '已禁用'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleToggleType(type.type_id, !type.enabled)}
                      >
                        {type.enabled ? '禁用' : '启用'}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 订单提交 */}
      <Card>
        <CardHeader>
          <CardTitle>提交订单</CardTitle>
          <CardDescription>使用不同订单类型提交交易</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div>
              <label className="text-sm font-medium">品种</label>
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
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium">订单类型</label>
              <Select
                value={orderForm.order_type}
                onValueChange={(value) => setOrderForm({ ...orderForm, order_type: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="market">市价单</SelectItem>
                  <SelectItem value="limit">限价单</SelectItem>
                  <SelectItem value="stop">止损单</SelectItem>
                  <SelectItem value="iceberg">冰山单</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium">方向</label>
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
              <label className="text-sm font-medium">数量</label>
              <Input
                type="number"
                value={orderForm.volume}
                onChange={(e) => setOrderForm({ ...orderForm, volume: parseInt(e.target.value) })}
              />
            </div>
            <div>
              <label className="text-sm font-medium">价格</label>
              <Input
                type="number"
                step="0.01"
                value={orderForm.price || ''}
                onChange={(e) => setOrderForm({ ...orderForm, price: parseFloat(e.target.value) })}
              />
            </div>
          </div>
          <Button className="mt-4" onClick={handleSubmitOrder} disabled={loading}>
            {loading ? '提交中..' : '提交订单'}
          </Button>
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
                <TableHead>类型</TableHead>
                <TableHead>方向</TableHead>
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
                    <TableCell>{order.order_type}</TableCell>
                    <TableCell>
                      <Badge variant={order.direction === 'long' ? 'default' : 'destructive'}>
                        {order.direction === 'long' ? '做多' : '做空'}
                      </Badge>
                    </TableCell>
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
