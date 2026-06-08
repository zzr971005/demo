import { useState, useEffect } from 'react'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'

import { Button } from '../../components/ui/button'

import { Input } from '../../components/ui/input'

import { Badge } from '../../components/ui/badge'

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'

import { API_BASE_URL } from '../../config'



interface CorrelationMatrix {

  symbols: string[]

  matrix: number[][]

  avg_correlation: number

}



interface HighCorrelationPair {

  symbol1: string

  symbol2: string

  correlation: number

}



interface DiversificationSuggestion {

  symbol: string

  current_weight: number

  suggested_weight: number

  reason: string

}



export default function CorrelationAnalysis() {

  const [matrix, setMatrix] = useState<CorrelationMatrix | null>(null)

  const [highCorrelations, setHighCorrelations] = useState<HighCorrelationPair[]>([])

  const [suggestions, setSuggestions] = useState<DiversificationSuggestion[]>([])

  const [loading, setLoading] = useState(false)

  const [symbols, setSymbols] = useState<string[]>(['RB', 'MA', 'CU', 'AL'])



  const fetchMatrix = async () => {

    setLoading(true)

    try {

      const res = await fetch(`${API_BASE_URL}/correlation-analysis/matrix`, {

        method: 'POST',

        headers: { 'Content-Type': 'application/json' },

        body: JSON.stringify({ symbols, period: '1d' }),

      })

      if (res.ok) {

        const data = await res.json()

        setMatrix(data)

      }

    } catch (error) {

      console.error('Failed to fetch correlation matrix:', error)

    } finally {

      setLoading(false)

    }

  }



  const fetchHighCorrelations = async () => {

    try {

      const res = await fetch(`${API_BASE_URL}/correlation-analysis/highly-correlated`)

      if (res.ok) {

        const data = await res.json()

        setHighCorrelations(Array.isArray(data.pairs) ? data.pairs : [])

      }

    } catch (error) {

      console.error('Failed to fetch high correlations:', error)

    }

  }



  const fetchSuggestions = async () => {

    try {

      const res = await fetch(`${API_BASE_URL}/correlation-analysis/diversify`)

      if (res.ok) {

        const data = await res.json()

        setSuggestions(Array.isArray(data.suggestions) ? data.suggestions : [])

      }

    } catch (error) {

      console.error('Failed to fetch diversification suggestions:', error)

    }

  }



  useEffect(() => {

    fetchMatrix()

    fetchHighCorrelations()

    fetchSuggestions()

  }, [])



  return (

    <div className="p-6 space-y-6">

      <h1 className="text-3xl font-bold">相关性分析</h1>



      <Card>

        <CardHeader>

          <CardTitle>相关性矩阵</CardTitle>

          <CardDescription>分析品种间的相关性</CardDescription>

        </CardHeader>

        <CardContent>

          <div className="mb-4">

            <label className="text-sm font-medium">品种列表（逗号分隔）</label>

            <Input

              placeholder="RB,MA,CU,AL"

              value={symbols.join(',')}

              onChange={(e) => setSymbols(e.target.value.split(',').map(s => s.trim()))}

            />

          </div>

          <Button onClick={fetchMatrix} disabled={loading}>

            {loading ? '计算中..' : '计算相关性'}

          </Button>

        </CardContent>

      </Card>



      {matrix && (

        <>

          <Card>

            <CardHeader>

              <CardTitle>相关性矩阵</CardTitle>

            </CardHeader>

            <CardContent>

              <div className="overflow-x-auto">

                <table className="w-full">

                  <thead>

                    <tr>

                      <th className="p-2"></th>

                      {(matrix.symbols || []).map((s, i) => (

                        <th key={i} className="p-2">{s}</th>

                      ))}

                    </tr>

                  </thead>

                  <tbody>

                    {(matrix.matrix || []).map((row, i) => (

                      <tr key={i}>

                        <td className="p-2 font-medium">{(matrix.symbols || [])[i]}</td>

                        {row.map((val, j) => (

                          <td

                            key={j}

                            className="p-2 text-center"

                            style={{

                              backgroundColor: `rgba(${val > 0 ? '0, 100, 255' : '255, 0, 0'}, ${Math.abs(val)})`,

                              color: Math.abs(val) > 0.5 ? 'white' : 'black',

                            }}

                          >

                            {val.toFixed(2)}

                          </td>

                        ))}

                      </tr>

                    ))}

                  </tbody>

                </table>

              </div>

              <div className="mt-4">

                <span className="text-sm">平均相关性 </span>

                <span className="font-bold">{matrix.avg_correlation.toFixed(3)}</span>

              </div>

            </CardContent>

          </Card>



          <Card>

            <CardHeader>

              <CardTitle>高相关性策略对</CardTitle>

            </CardHeader>

            <CardContent>

              <Table>

                <TableHeader>

                  <TableRow>

                    <TableHead>品种1</TableHead>

                    <TableHead>品种2</TableHead>

                    <TableHead>相关性</TableHead>

                  </TableRow>

                </TableHeader>

                <TableBody>

                  {highCorrelations.length === 0 ? (

                    <TableRow>

                      <TableCell colSpan={3} className="text-center text-muted-foreground">

                        暂无高相关性策略对

                      </TableCell>

                    </TableRow>

                  ) : (

                    highCorrelations.map((pair, idx) => (

                      <TableRow key={idx}>

                        <TableCell>{pair.symbol1}</TableCell>

                        <TableCell>{pair.symbol2}</TableCell>

                        <TableCell>

                          <Badge variant={pair.correlation > 0.8 ? 'destructive' : 'default'}>

                            {pair.correlation.toFixed(3)}

                          </Badge>

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

              <CardTitle>分散化建议</CardTitle>

            </CardHeader>

            <CardContent>

              <Table>

                <TableHeader>

                  <TableRow>

                    <TableHead>品种</TableHead>

                    <TableHead>当前权重</TableHead>

                    <TableHead>建议权重</TableHead>

                    <TableHead>原因</TableHead>

                  </TableRow>

                </TableHeader>

                <TableBody>

                  {suggestions.length === 0 ? (

                    <TableRow>

                      <TableCell colSpan={4} className="text-center text-muted-foreground">

                        暂无建议

                      </TableCell>

                    </TableRow>

                  ) : (

                    suggestions.map((sug, idx) => (

                      <TableRow key={idx}>

                        <TableCell>{sug.symbol}</TableCell>

                        <TableCell>{(sug.current_weight * 100).toFixed(1)}%</TableCell>

                        <TableCell>{(sug.suggested_weight * 100).toFixed(1)}%</TableCell>

                        <TableCell>{sug.reason}</TableCell>

                      </TableRow>

                    ))

                  )}

                </TableBody>

              </Table>

            </CardContent>

          </Card>

        </>

      )}

    </div>

  )

}

