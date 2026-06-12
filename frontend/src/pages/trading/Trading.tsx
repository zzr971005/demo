import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { API_BASE_URL } from '@/config';
import { 
  Play, 
  Square, 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle, 
  CheckCircle, 
  XCircle,
  Wallet,
  BarChart3,
  Activity,
  Shield
} from 'lucide-react';
import { SYMBOL_CONTRACT_OPTIONS } from '@/constants/symbols';

interface TradingStatus {
  running: boolean;
  connected: boolean;
  mode: string;
  circuit_breaker_level: number;
  can_trade: boolean;
  risk_status: string;
}

interface AccountInfo {
  mode?: string;
  connected?: boolean;
  balance?: number;
  available?: number;
  margin?: number;
  float_profit?: number;
  close_profit?: number;
}

interface Position {
  symbol: string;
  direction: string;
  volume: number;
  avg_price: number;
  market_value: number;
  realized_pnl: number;
  unrealized_pnl: number;
  total_pnl: number;
  margin: number;
  is_long: boolean;
  is_short: boolean;
}

interface Order {
  order_id: string;
  symbol: string;
  direction: string;
  offset: string;
  volume: number;
  price: number | null;
  order_type: string;
  status: string;
  filled_volume: number;
  filled_price: number;
  remaining_volume: number;
  created_at: string;
}

const SYMBOLS = SYMBOL_CONTRACT_OPTIONS;

export default function Trading() {
  const [status, setStatus] = useState<TradingStatus | null>(null);
  const [account, setAccount] = useState<AccountInfo | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // 下单表单
  const [orderForm, setOrderForm] = useState({
    symbol: 'KQ.m@SHFE.rb',
    direction: 'buy',
    offset: 'open',
    volume: 1,
    price: '',
    order_type: 'limit',
  });

  // 紧急平仓对话框
  const [showEmergencyDialog, setShowEmergencyDialog] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/execution/status`);
      if (response.ok) {
        const data = await response.json();
        setStatus(data);
      }
    } catch (err) {
      console.error('Failed to fetch status:', err);
    }
  }, []);

  const fetchAccount = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/execution/account`);
      if (response.ok) {
        const data = await response.json();
        setAccount(data);
      }
    } catch (err) {
      console.error('Failed to fetch account:', err);
    }
  }, []);

  const fetchPositions = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/trading/positions/non-flat`);
      if (response.ok) {
        const data = await response.json();
        setPositions(data);
      }
    } catch (err) {
      console.error('Failed to fetch positions:', err);
    }
  }, []);

  const fetchOrders = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/trading/orders/active`);
      if (response.ok) {
        const data = await response.json();
        setOrders(data);
      }
    } catch (err) {
      console.error('Failed to fetch orders:', err);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    fetchAccount();
    fetchPositions();
    fetchOrders();

    const interval = setInterval(() => {
      fetchStatus();
      fetchAccount();
      fetchPositions();
      fetchOrders();
    }, 3000);

    return () => clearInterval(interval);
  }, [fetchStatus, fetchAccount, fetchPositions, fetchOrders]);

  const showMessage = (msg: string, type: 'error' | 'success') => {
    if (type === 'error') {
      setError(msg);
      setTimeout(() => setError(null), 5000);
    } else {
      setSuccess(msg);
      setTimeout(() => setSuccess(null), 3000);
    }
  };

  const startGateway = async (mode: string) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/execution/start?mode=${mode}`, {
        method: 'POST',
      });
      const data = await response.json();
      if (data.success) {
        showMessage(`交易网关已启动 (${mode}模式)`, 'success');
        fetchStatus();
      } else {
        showMessage(data.error || '启动失败', 'error');
      }
    } catch (err) {
      showMessage('启动失败: ' + (err as Error).message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const stopGateway = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/execution/stop`, {
        method: 'POST',
      });
      const data = await response.json();
      if (data.success) {
        showMessage('交易网关已停止', 'success');
        fetchStatus();
      }
    } catch (err) {
      showMessage('停止失败: ' + (err as Error).message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const placeOrder = async () => {
    if (!orderForm.price && orderForm.order_type === 'limit') {
      showMessage('请输入价格', 'error');
      return;
    }

    setLoading(true);
    try {
      const params = new URLSearchParams({
        symbol: orderForm.symbol,
        direction: orderForm.direction,
        offset: orderForm.offset,
        volume: orderForm.volume.toString(),
        order_type: orderForm.order_type,
        ...(orderForm.price && { price: orderForm.price }),
      });

      const response = await fetch(`${API_BASE_URL}/execution/order?${params}`, {
        method: 'POST',
      });
      const data = await response.json();
      if (data.success) {
        showMessage(`订单已提交: ${data.order_id}`, 'success');
        fetchOrders();
      } else {
        showMessage(data.error || '下单失败', 'error');
      }
    } catch (err) {
      showMessage('下单失败: ' + (err as Error).message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const cancelOrder = async (orderId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/execution/order/${orderId}/cancel`, {
        method: 'POST',
      });
      const data = await response.json();
      if (data.success) {
        showMessage('订单已撤销', 'success');
        fetchOrders();
      }
    } catch (err) {
      showMessage('撤单失败: ' + (err as Error).message, 'error');
    }
  };

  const closePosition = async (symbol: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/execution/position/${encodeURIComponent(symbol)}/close`, {
        method: 'POST',
      });
      const data = await response.json();
      if (data.success) {
        showMessage('平仓指令已发送', 'success');
        fetchPositions();
      } else {
        showMessage(data.error || '平仓失败', 'error');
      }
    } catch (err) {
      showMessage('平仓失败: ' + (err as Error).message, 'error');
    }
  };

  const emergencyClose = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/execution/emergency-close`, {
        method: 'POST',
      });
      const data = await response.json();
      if (data.success) {
        showMessage('紧急平仓已执行', 'success');
        setShowEmergencyDialog(false);
        fetchPositions();
        fetchOrders();
      }
    } catch (err) {
      showMessage('紧急平仓失败: ' + (err as Error).message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'normal': return 'bg-green-500';
      case 'warning': return 'bg-yellow-500';
      case 'danger': return 'bg-orange-500';
      case 'critical': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'normal': return '正常';
      case 'warning': return '警告';
      case 'danger': return '危险';
      case 'critical': return '严重';
      default: return '未知';
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">交易执行</h1>
        <div className="flex items-center gap-4">
          {status && (
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${getStatusColor(status.risk_status)}`} />
              <span className="text-sm text-muted-foreground">
                风险状态: {getStatusText(status.risk_status)}
              </span>
            </div>
          )}
          {status && status.circuit_breaker_level > 0 && (
            <Badge variant="destructive">
              熔断等级 {status.circuit_breaker_level}
            </Badge>
          )}
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {success && (
        <Alert className="bg-green-50 border-green-200">
          <CheckCircle className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-800">{success}</AlertDescription>
        </Alert>
      )}

      {/* 网关控制 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="w-5 h-5" />
            网关控制
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            {!status?.running ? (
              <>
                <Button 
                  onClick={() => startGateway('mock')} 
                  disabled={loading}
                  variant="outline"
                >
                  <Play className="w-4 h-4 mr-2" />
                  启动模拟模式
                </Button>
                <Button 
                  onClick={() => startGateway('paper')} 
                  disabled={loading}
                  variant="outline"
                >
                  <Play className="w-4 h-4 mr-2" />
                  启动模拟账户
                </Button>
                <Button 
                  onClick={() => startGateway('live')} 
                  disabled={loading}
                  variant="default"
                  className="bg-red-600 hover:bg-red-700"
                >
                  <Play className="w-4 h-4 mr-2" />
                  启动实盘
                </Button>
              </>
            ) : (
              <Button 
                onClick={stopGateway} 
                disabled={loading}
                variant="destructive"
              >
                <Square className="w-4 h-4 mr-2" />
                停止网关
              </Button>
            )}

            {status && (
              <div className="flex items-center gap-4 ml-4 text-sm">
                <Badge variant={status.running ? 'default' : 'secondary'}>
                  {status.running ? '运行中' : '已停止'}
                </Badge>
                <Badge variant="outline">{status.mode?.toUpperCase()}</Badge>
                <span className="text-muted-foreground">
                  {status.can_trade ? '可以交易' : '交易暂停'}
                </span>
              </div>
            )}

            <div className="flex-1" />

            <Button
              variant="destructive"
              onClick={() => setShowEmergencyDialog(true)}
              disabled={!status?.running}
              className="bg-red-600 hover:bg-red-700"
            >
              <Shield className="w-4 h-4 mr-2" />
              紧急平仓
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 账户信息 */}
      {account && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wallet className="w-5 h-5" />
              账户信息
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-5 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold">¥{(account.balance || 0).toLocaleString()}</div>
                <div className="text-sm text-muted-foreground">总资产</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">¥{(account.available || 0).toLocaleString()}</div>
                <div className="text-sm text-muted-foreground">可用资金</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">¥{(account.margin || 0).toLocaleString()}</div>
                <div className="text-sm text-muted-foreground">占用保证金</div>
              </div>
              <div className="text-center">
                <div className={`text-2xl font-bold ${(account.float_profit || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  ¥{(account.float_profit || 0).toLocaleString()}
                </div>
                <div className="text-sm text-muted-foreground">浮动盈亏</div>
              </div>
              <div className="text-center">
                <div className={`text-2xl font-bold ${(account.close_profit || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  ¥{(account.close_profit || 0).toLocaleString()}
                </div>
                <div className="text-sm text-muted-foreground">已实现盈亏</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="order" className="space-y-4">
        <TabsList>
          <TabsTrigger value="order">下单</TabsTrigger>
          <TabsTrigger value="positions">持仓 ({positions.length})</TabsTrigger>
          <TabsTrigger value="orders">活跃订单 ({orders.length})</TabsTrigger>
        </TabsList>

        {/* 下单 */}
        <TabsContent value="order">
          <Card>
            <CardHeader>
              <CardTitle>下单</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>合约</Label>
                  <Select 
                    value={orderForm.symbol} 
                    onValueChange={(v) => setOrderForm({...orderForm, symbol: v})}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {SYMBOLS.map(s => (
                        <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>方向</Label>
                  <Select 
                    value={orderForm.direction} 
                    onValueChange={(v) => setOrderForm({...orderForm, direction: v})}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="buy">
                        <div className="flex items-center gap-2">
                          <TrendingUp className="w-4 h-4 text-red-500" />
                          买入
                        </div>
                      </SelectItem>
                      <SelectItem value="sell">
                        <div className="flex items-center gap-2">
                          <TrendingDown className="w-4 h-4 text-green-500" />
                          卖出
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>开平</Label>
                  <Select 
                    value={orderForm.offset} 
                    onValueChange={(v) => setOrderForm({...orderForm, offset: v})}
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

                <div className="space-y-2">
                  <Label>类型</Label>
                  <Select 
                    value={orderForm.order_type} 
                    onValueChange={(v) => setOrderForm({...orderForm, order_type: v})}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="limit">限价单</SelectItem>
                      <SelectItem value="market">市价单</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>手数</Label>
                  <Input 
                    type="number" 
                    min={1}
                    value={orderForm.volume}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setOrderForm({...orderForm, volume: parseInt(e.target.value) || 1})}
                  />
                </div>

                <div className="space-y-2">
                  <Label>价格 {orderForm.order_type === 'market' && '(市价单忽略)'}</Label>
                  <Input 
                    type="number" 
                    step="0.5"
                    value={orderForm.price}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setOrderForm({...orderForm, price: e.target.value})}
                    disabled={orderForm.order_type === 'market'}
                    placeholder={orderForm.order_type === 'market' ? '市价成交' : '请输入价格'}
                  />
                </div>
              </div>

              <Button 
                onClick={placeOrder} 
                disabled={loading || !status?.can_trade}
                className="w-full"
                size="lg"
              >
                {orderForm.direction === 'buy' ? (
                  <TrendingUp className="w-4 h-4 mr-2" />
                ) : (
                  <TrendingDown className="w-4 h-4 mr-2" />
                )}
                {orderForm.direction === 'buy' ? '买入' : '卖出'}
                {orderForm.offset === 'open' ? '开仓' : '平仓'}
              </Button>

              {!status?.can_trade && status?.running && (
                <p className="text-sm text-red-500 text-center">
                  当前处于熔断状态，无法交易
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* 持仓 */}
        <TabsContent value="positions">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                当前持仓
              </CardTitle>
              {positions.length > 0 && (
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => positions.forEach(p => closePosition(p.symbol))}
                >
                  全部平仓
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {positions.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  暂无持仓
                </div>
              ) : (
                <div className="space-y-2">
                  {positions.map((pos) => (
                    <div 
                      key={pos.symbol} 
                      className="flex items-center justify-between p-4 border rounded-lg"
                    >
                      <div className="flex items-center gap-4">
                        <Badge variant={pos.is_long ? 'default' : 'destructive'}>
                          {pos.is_long ? '多' : '空'}
                        </Badge>
                        <div>
                          <div className="font-medium">{pos.symbol}</div>
                          <div className="text-sm text-muted-foreground">
                            {pos.volume}手 @ ¥{pos.avg_price.toFixed(2)}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <div className={`font-bold ${pos.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {pos.total_pnl >= 0 ? '+' : ''}¥{pos.total_pnl.toFixed(2)}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            市值 ¥{pos.market_value.toFixed(2)}
                          </div>
                        </div>
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => closePosition(pos.symbol)}
                        >
                          平仓
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* 活跃订单 */}
        <TabsContent value="orders">
          <Card>
            <CardHeader>
              <CardTitle>活跃订单</CardTitle>
            </CardHeader>
            <CardContent>
              {orders.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  暂无活跃订单
                </div>
              ) : (
                <div className="space-y-2">
                  {orders.map((order) => (
                    <div 
                      key={order.order_id} 
                      className="flex items-center justify-between p-4 border rounded-lg"
                    >
                      <div className="flex items-center gap-4">
                        <Badge variant={order.direction === 'buy' ? 'default' : 'destructive'}>
                          {order.direction === 'buy' ? '买' : '卖'}
                        </Badge>
                        <div>
                          <div className="font-medium">{order.symbol}</div>
                          <div className="text-sm text-muted-foreground">
                            {order.offset === 'open' ? '开仓' : '平仓'} {order.volume}手
                            {order.price ? ` @ ¥${order.price}` : ' 市价'}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <div className="text-sm">
                            成交: {order.filled_volume}/{order.volume}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {order.status}
                          </div>
                        </div>
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => cancelOrder(order.order_id)}
                        >
                          <XCircle className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* 紧急平仓确认对话框 */}
      <Dialog open={showEmergencyDialog} onOpenChange={setShowEmergencyDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="w-5 h-5" />
              确认紧急平仓
            </DialogTitle>
            <DialogDescription>
              此操作将立即取消所有活跃订单并平掉所有仓位。该操作不可撤销，请确认是否继续？
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEmergencyDialog(false)}>
              取消
            </Button>
            <Button 
              variant="destructive" 
              onClick={emergencyClose}
              disabled={loading}
            >
              确认紧急平仓
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
