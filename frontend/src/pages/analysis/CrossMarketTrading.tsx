import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Badge } from '../../components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { API_BASE_URL } from '../../config'

interface ArbitrageOpportunity {
  opportunity_id: string
  market1: string
  market2: string
  symbol: string
  price1: number
  price2: number
  spread: number
  profit_potential: number
  timestamp: string
}

interface LinkageOpportunity {
  linkage_id: string
  symbol1: string
  symbol2: string
  correlation: number
  deviation: number
  signal: 'long' | 'short' | 'neutral'
}

export default function CrossMarketTrading() {
  const [arbitrages, setArbitrages] = useState<ArbitrageOpportunity[]>([])
  const [linkages, setLinkages] = useState<LinkageOpportunity[]>([])
  const [loading, setLoading] = useState(false)

  const fetchArbitrages = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/cross-market-trading/arbitrages`)
      if (res.ok) {
        const data = await res.json()
        setArbitrages(Array.isArray(data.opportunities) ? data.opportunities : [])
      }
    } catch (error) {
      console.error('Failed to fetch arbitrage opportunities:', error)
    }
  }

  const fetchLinkages = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/cross-market-trading/linkages`)
      if (res.ok) {
        const data = await res.json()
        setLinkages(Array.isArray(data.opportunities) ? data.opportunities : [])
      }
    } catch (error) {
      console.error('Failed to fetch linkage opportunities:', error)
    }
  }

  const handleExecuteArbitrage = async (opportunityId: string) => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/cross-market-trading/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ opportunity_id: opportunityId }),
      })
      if (res.ok) {
        alert('套利交易已执行')
        fetchArbitrages()
      } else {
        alert('套利交易执行失败')
      }
    } catch (error) {
      console.error('Failed to execute arbitrage:', error)
      alert('套利交易执行失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchArbitrages()
    fetchLinkages()
  }, [])

  const getSignalBadge = (signal: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive'> = {
      long: 'default',
      short: 'destructive',
      neutral: 'secondary',
    }
    const labels: Record<string, string> = {
      long: '做多',
      short: '做空',
      neutral: '中等',
    }
    return <Badge variant={variants[signal]}>{labels[signal]}</Badge>
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">跨市场交易</h1>

      <Card>
        <CardHeader>
          <CardTitle>套利机会</CardTitle>
          <CardDescription>跨市场套利机会</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>机会ID</TableHead>
                <TableHead>市场1</TableHead>
                <TableHead>市场2</TableHead>
                <TableHead>品种</TableHead>
                <TableHead>价格1</TableHead>
                <TableHead>价格2</TableHead>
                <TableHead>价差</TableHead>
                <TableHead>潜在利润</TableHead>
                <TableHead>时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {arbitrages.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={10} className="text-center text-muted-foreground">
                    暂无套利机会
                  </TableCell>
                </TableRow>
              ) : (
                arbitrages.map((arb) => (
                  <TableRow key={arb.opportunity_id}>
                    <TableCell>{arb.opportunity_id}</TableCell>
                    <TableCell>{arb.market1}</TableCell>
                    <TableCell>{arb.market2}</TableCell>
                    <TableCell>{arb.symbol}</TableCell>
                    <TableCell>{arb.price1.toFixed(2)}</TableCell>
                    <TableCell>{arb.price2.toFixed(2)}</TableCell>
                    <TableCell className={arb.spread > 0 ? 'text-green-600' : 'text-red-600'}>
                      {arb.spread.toFixed(2)}
                    </TableCell>
                    <TableCell className={arb.profit_potential > 0 ? 'text-green-600' : 'text-red-600'}>
                      {(arb.profit_potential * 100).toFixed(2)}%
                    </TableCell>
                    <TableCell>{new Date(arb.timestamp).toLocaleString()}</TableCell>
                    <TableCell>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleExecuteArbitrage(arb.opportunity_id)}
                        disabled={loading}
                      >
                        执行
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>联动交易机会</CardTitle>
          <CardDescription>品种联动交易机会</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>联动ID</TableHead>
                <TableHead>品种1</TableHead>
                <TableHead>品种2</TableHead>
                <TableHead>相关性</TableHead>
                <TableHead>偏离度</TableHead>
                <TableHead>信号</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {linkages.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground">
                    暂无联动机会
                  </TableCell>
                </TableRow>
              ) : (
                linkages.map((link) => (
                  <TableRow key={link.linkage_id}>
                    <TableCell>{link.linkage_id}</TableCell>
                    <TableCell>{link.symbol1}</TableCell>
                    <TableCell>{link.symbol2}</TableCell>
                    <TableCell>{link.correlation.toFixed(3)}</TableCell>
                    <TableCell className={Math.abs(link.deviation) > 2 ? 'text-red-600' : 'text-green-600'}>
                      {link.deviation.toFixed(2)}%
                    </TableCell>
                    <TableCell>{getSignalBadge(link.signal)}</TableCell>
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
