import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { SYMBOL_CODES } from '@/constants/symbols'

const AVAILABLE_SYMBOLS = SYMBOL_CODES

export default function GeneralizationTest() {
  const [factorId, setFactorId] = useState('')
  const [originalSymbol, setOriginalSymbol] = useState('RB')
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>(['MA', 'CU'])
  const [isTesting, setIsTesting] = useState(false)
  const [testResult, setTestResult] = useState<any>(null)

  const handleSymbolToggle = (symbol: string) => {
    setSelectedSymbols(prev =>
      prev.includes(symbol)
        ? prev.filter(s => s !== symbol)
        : [...prev, symbol]
    )
  }

  const handleTest = async () => {
    setIsTesting(true)
    try {
      const response = await fetch('/api/evolution/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          factor_id: factorId,
          original_symbol: originalSymbol,
          test_symbols: selectedSymbols
        })
      })

      if (response.ok) {
        const data = await response.json()
        setTestResult(data)
      } else {
        alert('Failed to test generalization')
      }
    } catch (error) {
      console.error('Error testing generalization:', error)
      alert('Error testing generalization')
    } finally {
      setIsTesting(false)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">Generalization Test</h1>
      
      <Card>
        <CardHeader>
          <CardTitle>Factor Configuration</CardTitle>
          <CardDescription>Enter factor ID and select test symbols</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="factor-id">Factor ID</Label>
            <Input
              id="factor-id"
              value={factorId}
              onChange={(e) => setFactorId(e.target.value)}
              placeholder="Enter factor ID"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="original-symbol">Original Symbol</Label>
            <select
              id="original-symbol"
              value={originalSymbol}
              onChange={(e) => setOriginalSymbol(e.target.value)}
              className="w-full p-2 border rounded"
            >
              {AVAILABLE_SYMBOLS.map(symbol => (
                <option key={symbol} value={symbol}>{symbol}</option>
              ))}
            </select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Test Symbols</CardTitle>
          <CardDescription>Select symbols to test generalization on</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-5 gap-2">
            {AVAILABLE_SYMBOLS.filter(s => s !== originalSymbol).map(symbol => (
              <label key={symbol} className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={selectedSymbols.includes(symbol)}
                  onChange={() => handleSymbolToggle(symbol)}
                />
                <span>{symbol}</span>
              </label>
            ))}
          </div>
        </CardContent>
      </Card>

      <Button
        onClick={handleTest}
        disabled={isTesting || !factorId || selectedSymbols.length === 0}
        className="w-full"
      >
        {isTesting ? 'Testing...' : 'Run Generalization Test'}
      </Button>

      {testResult && (
        <Card>
          <CardHeader>
            <CardTitle>Test Results</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Is Universal</Label>
                <p className="text-2xl font-bold">{testResult.is_universal ? 'Yes' : 'No'}</p>
              </div>
              <div>
                <Label>Generalization Score</Label>
                <p className="text-2xl font-bold">{testResult.generalization_score.toFixed(2)}</p>
              </div>
              <div>
                <Label>Performance Mean</Label>
                <p className="text-xl">{testResult.performance_mean?.toFixed(2)}</p>
              </div>
              <div>
                <Label>Performance Std</Label>
                <p className="text-xl">{testResult.performance_std?.toFixed(2)}</p>
              </div>
              <div>
                <Label>IC Correlation</Label>
                <p className="text-xl">{testResult.ic_correlation?.toFixed(2)}</p>
              </div>
            </div>
            <div>
              <Label>Symbol Performance</Label>
              <pre className="mt-2 p-4 bg-gray-100 rounded overflow-auto">
                {JSON.stringify(testResult.symbol_performance, null, 2)}
              </pre>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
