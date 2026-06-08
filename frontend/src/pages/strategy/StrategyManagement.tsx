import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface FactorInfo {
  id: string;
  symbol: string;
  formula: string;
  sharpe_train?: number;
  sharpe_test?: number;
  calmar?: number;
  max_drawdown?: number;
  win_rate?: number;
  total_trades?: number;
  ic_mean_4h?: number;
  ic_mean_24h?: number;
  ic_mean_168h?: number;
  ic_std?: number;
  ic_ir?: number;
  ic_half_life?: number;
  factor_category?: string;
  strategy_rank?: number;
}

interface RotationHistoryItem {
  id: number;
  symbol: string;
  old_factor_id?: string;
  new_factor_id: string;
  rotation_reason?: string;
  score_improvement?: number;
  rotated_at: string;
}

interface DecayHistoryItem {
  id: number;
  factor_id: string;
  symbol: string;
  ic_value: number;
  ic_window: number;
  recorded_at: string;
}

const StrategyManagement: React.FC = () => {
  const [selectedSymbol, setSelectedSymbol] = useState<string>('RB');
  const [topFactors, setTopFactors] = useState<FactorInfo[]>([]);
  const [currentStrategies, setCurrentStrategies] = useState<FactorInfo[]>([]);
  const [rotationHistory, setRotationHistory] = useState<RotationHistoryItem[]>([]);
  const [decayHistory, setDecayHistory] = useState<DecayHistoryItem[]>([]);
  const [selectedFactorId, setSelectedFactorId] = useState<string | null>(null);

  const symbols = ['RB', 'HC', 'I', 'J', 'JM', 'CU', 'AL', 'ZN', 'NI', 'SN'];

  useEffect(() => {
    loadData();
  }, [selectedSymbol]);

  useEffect(() => {
    if (selectedFactorId) {
      loadDecayHistory(selectedFactorId);
    }
  }, [selectedFactorId]);

  const loadData = async () => {
    try {
      // Load factor pool
      const poolResponse = await fetch(`/api/strategy-management/pool/${selectedSymbol}?limit=50`);
      const poolData = await poolResponse.json();
      setTopFactors(poolData);

      // Load current strategies
      const strategiesResponse = await fetch(`/api/strategy-management/strategies/current/${selectedSymbol}`);
      const strategiesData = await strategiesResponse.json();
      setCurrentStrategies(strategiesData);

      // Load rotation history
      const rotationResponse = await fetch(`/api/strategy-management/rotation-history/${selectedSymbol}?limit=50`);
      const rotationData = await rotationResponse.json();
      setRotationHistory(rotationData);
    } catch (error) {
      console.error('Failed to load data:', error);
    }
  };

  const loadDecayHistory = async (factorId: string) => {
    try {
      const response = await fetch(`/api/strategy-management/decay-history/${factorId}?limit=100`);
      const data = await response.json();
      setDecayHistory(data);
    } catch (error) {
      console.error('Failed to load decay history:', error);
    }
  };

  const handleManualRotation = async () => {
    try {
      const response = await fetch('/api/strategy-management/strategies/rotate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: selectedSymbol }),
      });
      const data = await response.json();
      alert(data.message);
      loadData();
    } catch (error) {
      console.error('Failed to rotate strategies:', error);
      alert('策略轮换失败');
    }
  };

  const handleSelectStrategies = async () => {
    try {
      await fetch('/api/strategy-management/strategies/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: selectedSymbol, count: 5 }),
      });
      alert('策略选择完成');
      loadData();
    } catch (error) {
      console.error('Failed to select strategies:', error);
      alert('策略选择失败');
    }
  };

  const getCategoryColor = (category?: string) => {
    switch (category) {
      case 'fast': return 'bg-red-500';
      case 'medium': return 'bg-yellow-500';
      case 'slow': return 'bg-green-500';
      default: return 'bg-gray-500';
    }
  };

  const getCategoryLabel = (category?: string) => {
    switch (category) {
      case 'fast': return '快速衰减';
      case 'medium': return '中等衰减';
      case 'slow': return '慢速衰减';
      default: return '未分类';
    }
  };

  const decayChartData = decayHistory.map(item => ({
    date: new Date(item.recorded_at).toLocaleDateString(),
    icValue: item.ic_value,
  }));

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">策略管理</h1>
        <div className="flex gap-4">
          <Select value={selectedSymbol} onValueChange={setSelectedSymbol}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="选择品种" />
            </SelectTrigger>
            <SelectContent>
              {symbols.map(symbol => (
                <SelectItem key={symbol} value={symbol}>{symbol}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={handleSelectStrategies}>选择策略</Button>
          <Button onClick={handleManualRotation} variant="outline">手动轮换</Button>
        </div>
      </div>

      <Tabs defaultValue="pool" className="space-y-4">
        <TabsList>
          <TabsTrigger value="pool">因子池 (50)</TabsTrigger>
          <TabsTrigger value="strategies">当前策略 (5)</TabsTrigger>
          <TabsTrigger value="rotation">轮换历史</TabsTrigger>
          <TabsTrigger value="decay">因子衰减</TabsTrigger>
        </TabsList>

        <TabsContent value="pool">
          <Card>
            <CardHeader>
              <CardTitle>最优因子池</CardTitle>
              <CardDescription>按IC和回测绩效综合评分排序的前50个因子</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>排名</TableHead>
                    <TableHead>因子ID</TableHead>
                    <TableHead>分类</TableHead>
                    <TableHead>IC_4h</TableHead>
                    <TableHead>IC_24h</TableHead>
                    <TableHead>IC_IR</TableHead>
                    <TableHead>半衰期</TableHead>
                    <TableHead>Sharpe</TableHead>
                    <TableHead>Calmar</TableHead>
                    <TableHead>胜率</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {topFactors.map((factor, index) => (
                    <TableRow key={factor.id}>
                      <TableCell>{index + 1}</TableCell>
                      <TableCell className="font-mono text-xs">{factor.id.slice(-8)}</TableCell>
                      <TableCell>
                        <Badge className={getCategoryColor(factor.factor_category)}>
                          {getCategoryLabel(factor.factor_category)}
                        </Badge>
                      </TableCell>
                      <TableCell>{factor.ic_mean_4h?.toFixed(3) ?? '-'}</TableCell>
                      <TableCell>{factor.ic_mean_24h?.toFixed(3) ?? '-'}</TableCell>
                      <TableCell>{factor.ic_ir?.toFixed(3) ?? '-'}</TableCell>
                      <TableCell>{factor.ic_half_life ? `${factor.ic_half_life.toFixed(0)}h` : '-'}</TableCell>
                      <TableCell>{factor.sharpe_test?.toFixed(2) ?? '-'}</TableCell>
                      <TableCell>{factor.calmar?.toFixed(2) ?? '-'}</TableCell>
                      <TableCell>{(factor.win_rate! * 100).toFixed(1)}%</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="strategies">
          <Card>
            <CardHeader>
              <CardTitle>当前策略</CardTitle>
              <CardDescription>正在运行的5个策略</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>策略排名</TableHead>
                    <TableHead>因子ID</TableHead>
                    <TableHead>分类</TableHead>
                    <TableHead>IC_4h</TableHead>
                    <TableHead>IC_IR</TableHead>
                    <TableHead>Sharpe</TableHead>
                    <TableHead>Calmar</TableHead>
                    <TableHead>胜率</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {currentStrategies.map((strategy) => (
                    <TableRow key={strategy.id}>
                      <TableCell>
                        <Badge variant="outline">#{strategy.strategy_rank}</Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs">{strategy.id.slice(-8)}</TableCell>
                      <TableCell>
                        <Badge className={getCategoryColor(strategy.factor_category)}>
                          {getCategoryLabel(strategy.factor_category)}
                        </Badge>
                      </TableCell>
                      <TableCell>{strategy.ic_mean_4h?.toFixed(3) ?? '-'}</TableCell>
                      <TableCell>{strategy.ic_ir?.toFixed(3) ?? '-'}</TableCell>
                      <TableCell>{strategy.sharpe_test?.toFixed(2) ?? '-'}</TableCell>
                      <TableCell>{strategy.calmar?.toFixed(2) ?? '-'}</TableCell>
                      <TableCell>{(strategy.win_rate! * 100).toFixed(1)}%</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="rotation">
          <Card>
            <CardHeader>
              <CardTitle>策略轮换历史</CardTitle>
              <CardDescription>策略轮换记录</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>时间</TableHead>
                    <TableHead>旧因子</TableHead>
                    <TableHead>新因子</TableHead>
                    <TableHead>原因</TableHead>
                    <TableHead>评分提升</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rotationHistory.map((record) => (
                    <TableRow key={record.id}>
                      <TableCell>{new Date(record.rotated_at).toLocaleString()}</TableCell>
                      <TableCell className="font-mono text-xs">{record.old_factor_id?.slice(-8) ?? '-'}</TableCell>
                      <TableCell className="font-mono text-xs">{record.new_factor_id.slice(-8)}</TableCell>
                      <TableCell>{record.rotation_reason ?? '-'}</TableCell>
                      <TableCell>
                        {record.score_improvement !== null && record.score_improvement !== undefined ? (
                          <Badge variant={record.score_improvement > 0 ? 'default' : 'destructive'}>
                            {record.score_improvement > 0 ? '+' : ''}{record.score_improvement.toFixed(3)}
                          </Badge>
                        ) : '-'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="decay">
          <Card>
            <CardHeader>
              <CardTitle>因子衰减曲线</CardTitle>
              <CardDescription>选择因子查看IC衰减历史</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Select value={selectedFactorId ?? ''} onValueChange={setSelectedFactorId}>
                <SelectTrigger className="w-[300px]">
                  <SelectValue placeholder="选择因子" />
                </SelectTrigger>
                <SelectContent>
                  {topFactors.map((factor) => (
                    <SelectItem key={factor.id} value={factor.id}>
                      {factor.id.slice(-8)} - {getCategoryLabel(factor.factor_category)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {selectedFactorId && decayChartData.length > 0 && (
                <div className="h-[400px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={decayChartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="icValue" stroke="#8884d8" name="IC值" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}

              {selectedFactorId && decayChartData.length === 0 && (
                <p className="text-center text-gray-500">暂无衰减历史数据</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default StrategyManagement;
