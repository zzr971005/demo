import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'

const AVAILABLE_SYMBOLS = ['RB', 'MA', 'CU', 'AL', 'ZN', 'NI', 'HC', 'JM', 'SF', 'SM']

export default function EvolutionModeSelector() {
  const [mode, setMode] = useState<'single' | 'joint' | 'hybrid'>('single')
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>(['RB'])
  const [populationSize, setPopulationSize] = useState(100)
  const [maxGenerations, setMaxGenerations] = useState(50)
  const [universalWeight, setUniversalWeight] = useState(0.5)
  const [isStarting, setIsStarting] = useState(false)

  const handleSymbolToggle = (symbol: string) => {
    if (mode === 'single') {
      setSelectedSymbols([symbol])
    } else {
      setSelectedSymbols(prev =>
        prev.includes(symbol)
          ? prev.filter(s => s !== symbol)
          : [...prev, symbol]
      )
    }
  }

  const handleStart = async () => {
    setIsStarting(true)
    try {
      const endpoint = mode === 'joint' 
        ? '/api/evolution/joint-start'
        : mode === 'hybrid'
        ? '/api/evolution/hybrid-start'
        : '/api/evolution/start'

      const payload = mode === 'single'
        ? { symbol: selectedSymbols[0], population_size: populationSize, max_generations: maxGenerations }
        : mode === 'joint'
        ? { symbols: selectedSymbols, population_size: populationSize, max_generations: maxGenerations }
        : { symbols: selectedSymbols, population_size: populationSize, max_generations: maxGenerations, universal_weight: universalWeight }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (response.ok) {
        const data = await response.json()
        alert(`Evolution started! Task ID: ${data.task_id}`)
      } else {
        alert('Failed to start evolution')
      }
    } catch (error) {
      console.error('Error starting evolution:', error)
      alert('Error starting evolution')
    } finally {
      setIsStarting(false)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">Evolution Mode Selector</h1>
      
      <Card>
        <CardHeader>
          <CardTitle>Evolution Mode</CardTitle>
          <CardDescription>Select the evolution mode for factor mining</CardDescription>
        </CardHeader>
        <CardContent>
          <RadioGroup value={mode} onValueChange={(value: any) => setMode(value)}>
            <div className="flex items-center space-x-2 mb-4">
              <RadioGroupItem value="single" id="single" />
              <Label htmlFor="single">Single-Symbol Evolution</Label>
            </div>
            <div className="flex items-center space-x-2 mb-4">
              <RadioGroupItem value="joint" id="joint" />
              <Label htmlFor="joint">Joint Evolution (Multi-Symbol for Universal Factors)</Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="hybrid" id="hybrid" />
              <Label htmlFor="hybrid">Hybrid Evolution (Universal + Symbol-Specific)</Label>
            </div>
          </RadioGroup>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Symbols</CardTitle>
          <CardDescription>
            {mode === 'single' ? 'Select one symbol' : 'Select multiple symbols'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-5 gap-2">
            {AVAILABLE_SYMBOLS.map(symbol => (
              <div key={symbol} className="flex items-center space-x-2">
                <Checkbox
                  id={symbol}
                  checked={selectedSymbols.includes(symbol)}
                  onCheckedChange={() => handleSymbolToggle(symbol)}
                />
                <Label htmlFor={symbol}>{symbol}</Label>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Parameters</CardTitle>
          <CardDescription>Configure evolution parameters</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="population">Population Size</Label>
            <Input
              id="population"
              type="number"
              value={populationSize}
              onChange={(e) => setPopulationSize(Number(e.target.value))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="generations">Max Generations</Label>
            <Input
              id="generations"
              type="number"
              value={maxGenerations}
              onChange={(e) => setMaxGenerations(Number(e.target.value))}
            />
          </div>
          {mode === 'hybrid' && (
            <div className="space-y-2">
              <Label htmlFor="universal-weight">Universal Factor Weight ({universalWeight})</Label>
              <Input
                id="universal-weight"
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={universalWeight}
                onChange={(e) => setUniversalWeight(Number(e.target.value))}
              />
            </div>
          )}
        </CardContent>
      </Card>

      <Button
        onClick={handleStart}
        disabled={isStarting || selectedSymbols.length === 0}
        className="w-full"
      >
        {isStarting ? 'Starting...' : 'Start Evolution'}
      </Button>
    </div>
  )
}
