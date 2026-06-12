import { useState, useMemo } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import {
  GitBranch,
  Activity,
  Dna,
  Trophy,
  Zap,
  RefreshCw,
  ChevronRight,
  Crown,
  Swords,
} from 'lucide-react'
import { useEvolution } from '@/hooks/useEvolution'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  Tooltip as UITooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { cn, formatNumber } from '@/lib/utils'
import { useAppStore } from '@/store'

const COLORS = [
  '#3b82f6',
  '#10b981',
  '#f59e0b',
  '#ef4444',
  '#8b5cf6',
  '#ec4899',
  '#06b6d4',
  '#84cc16',
]

function TreeNodeCard({
  node,
  isSelected,
  onClick,
}: {
  node: import('@/hooks/useEvolution').TreeNode
  isSelected: boolean
  onClick: () => void
}) {
  return (
    <UITooltip>
      <TooltipTrigger asChild>
        <button
          onClick={onClick}
          className={cn(
            'relative flex flex-col items-center gap-1 rounded-lg border px-3 py-2 text-xs transition-all',
            node.isRunning && 'border-green-500 bg-green-500/10 ring-1 ring-green-500',
            node.isCandidate && !node.isRunning && 'border-amber-500 bg-amber-500/10',
            !node.isRunning && !node.isCandidate && 'border-border bg-card hover:bg-accent',
            isSelected && 'ring-2 ring-primary'
          )}
        >
          <div className="flex items-center gap-1">
            {node.isRunning && <Crown className="h-3 w-3 text-green-500" />}
            {node.isCandidate && !node.isRunning && (
              <Swords className="h-3 w-3 text-amber-500" />
            )}
            <span className="font-mono font-medium">{node.factorInfo?.name ?? node.factor_id.slice(0, 6)}</span>
          </div>
          <span className={cn(
            'font-mono',
            (node.sharpe_ratio ?? 0) > 1.5 ? 'text-green-500' : (node.sharpe_ratio ?? 0) > 0.5 ? 'text-amber-500' : 'text-muted-foreground'
          )}>
            S={formatNumber(node.sharpe_ratio ?? 0)}
          </span>
        </button>
      </TooltipTrigger>
      <TooltipContent side="top" className="space-y-1">
        <p className="font-semibold">{node.factorInfo?.name ?? node.factor_id}</p>
        <p>Sharpe: {formatNumber(node.sharpe_ratio ?? 0)}</p>
        <p>Generation: {node.generation}</p>
        {node.isRunning && <p className="text-green-500">当前Running策略</p>}
        {node.isCandidate && !node.isRunning && <p className="text-amber-500">候选挑战者</p>}
      </TooltipContent>
    </UITooltip>
  )
}

function TreeLevel({
  nodes,
  selectedId,
  onSelect,
}: {
  nodes: import('@/hooks/useEvolution').TreeNode[]
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  return (
    <div className="flex items-center justify-center gap-4">
      {nodes.map((node) => (
        <TreeNodeCard
          key={node.id}
          node={node}
          isSelected={selectedId === node.id}
          onClick={() => onSelect(node.id)}
        />
      ))}
    </div>
  )
}

function StrategyTree({
  treeData,
  selectedId,
  onSelect,
}: {
  treeData: import('@/hooks/useEvolution').TreeNode[]
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  const levels = useMemo(() => {
    const maxDepth = Math.max(...treeData.map((n) => n.depth), 0)
    const result: import('@/hooks/useEvolution').TreeNode[][] = []
    for (let d = 0; d <= maxDepth; d++) {
      result.push(treeData.filter((n) => n.depth === d))
    }
    return result
  }, [treeData])

  if (treeData.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-muted-foreground">
        暂无策略血缘数据
      </div>
    )
  }

  return (
    <div className="space-y-6 overflow-x-auto py-4">
      {levels.map((level, idx) => (
        <div key={idx} className="space-y-2">
          <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
            <GitBranch className="h-3 w-3" />
            <span>第 {idx + 1} 代</span>
          </div>
          <TreeLevel nodes={level} selectedId={selectedId} onSelect={onSelect} />
        </div>
      ))}
    </div>
  )
}

export default function EvolutionTree() {
  const symbols = useAppStore((s) => s.symbols)
  const [selectedSymbol, setSelectedSymbol] = useState<string>(() =>
    symbols.length > 0 ? symbols[0].symbol : 'RB2501'
  )
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)

  const {
    generations,
    primitiveFamilies,
    treeData,
    diversityMetrics,
    loading,
    error,
    refresh,
  } = useEvolution(selectedSymbol)

  const selectedNode = useMemo(
    () => treeData.find((n) => n.id === selectedNodeId) ?? null,
    [treeData, selectedNodeId]
  )

  const fitnessData = useMemo(() => {
    return generations.map((g) => ({
      gen: `G${g.generation}`,
      best: Number(g.bestFitness.toFixed(3)),
      avg: Number(g.avgFitness.toFixed(3)),
    }))
  }, [generations])

  const pieData = useMemo(() => {
    return primitiveFamilies.map((f) => ({
      name: f.name,
      value: f.count,
    }))
  }, [primitiveFamilies])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <GitBranch className="h-6 w-6 text-primary" />
            进化树
          </h1>
          <p className="text-muted-foreground">因子进化历史与血缘关系</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={selectedSymbol}
            onChange={(e) => setSelectedSymbol(e.target.value)}
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          >
            {symbols.map((s) => (
              <option key={s.symbol} value={s.symbol}>
                {s.symbol} - {s.name}
              </option>
            ))}
          </select>
          <Button variant="outline" size="sm" onClick={refresh} disabled={loading}>
            <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-destructive bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-lg border bg-card p-4">
          <div className="mb-4 flex items-center gap-2 text-sm font-semibold">
            <Activity className="h-4 w-4 text-primary" />
            适应度曲线
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={fitnessData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="gen" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '0.5rem',
                  }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="best"
                  name="最佳适应度"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="avg"
                  name="平均适应度"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-lg border bg-card p-4">
          <div className="mb-4 flex items-center gap-2 text-sm font-semibold">
            <Dna className="h-4 w-4 text-primary" />
            原语族占比
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={90}
                  paddingAngle={2}
                  dataKey="value"
                  nameKey="name"
                >
                  {pieData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '0.5rem',
                  }}
                />
                <Legend fontSize={12} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-lg border bg-card p-4">
          <div className="mb-4 flex items-center gap-2 text-sm font-semibold">
            <Trophy className="h-4 w-4 text-primary" />
            种群多样性指标
          </div>
          <div className="space-y-4">
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">信息熵</span>
                <span className="font-mono font-medium">{diversityMetrics.entropy}</span>
              </div>
              <Progress value={Math.min(diversityMetrics.entropy * 20, 100)} />
            </div>
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">交叉率</span>
                <span className="font-mono font-medium">{diversityMetrics.crossRate}%</span>
              </div>
              <Progress value={diversityMetrics.crossRate} />
            </div>
            <div className="grid grid-cols-2 gap-3 pt-2">
              <div className="rounded-md bg-accent p-3 text-center">
                <div className="text-lg font-bold">{diversityMetrics.uniquePrimitives}</div>
                <div className="text-xs text-muted-foreground">独特原语</div>
              </div>
              <div className="rounded-md bg-accent p-3 text-center">
                <div className="text-lg font-bold">{diversityMetrics.totalStrategies}</div>
                <div className="text-xs text-muted-foreground">策略总数</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2 rounded-lg border bg-card p-4">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <GitBranch className="h-4 w-4 text-primary" />
              策略血缘树
            </div>
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <span className="inline-block h-2 w-2 rounded-full bg-green-500" />
                Running
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block h-2 w-2 rounded-full bg-amber-500" />
                候选
              </span>
            </div>
          </div>
          <StrategyTree
            treeData={treeData}
            selectedId={selectedNodeId}
            onSelect={setSelectedNodeId}
          />
        </div>

        <div className="rounded-lg border bg-card p-4">
          <div className="mb-4 flex items-center gap-2 text-sm font-semibold">
            <Zap className="h-4 w-4 text-primary" />
            策略详情
          </div>
          {selectedNode ? (
            <div className="space-y-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">名称</span>
                <span className="font-mono font-medium">{selectedNode.factorInfo?.name ?? selectedNode.factor_id}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">夏普比率</span>
                <span className={cn(
                  'font-mono font-medium',
                  (selectedNode.sharpe_ratio ?? 0) > 1.5 ? 'text-green-500' : (selectedNode.sharpe_ratio ?? 0) > 0.5 ? 'text-amber-500' : 'text-muted-foreground'
                )}>
                  {formatNumber(selectedNode.sharpe_ratio ?? 0)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">代际</span>
                <Badge variant="secondary">Gen {selectedNode.generation}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">胜率</span>
                <span className="font-mono">{formatNumber((selectedNode.factorInfo?.win_rate ?? 0) * 100)}%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">交易次数</span>
                <span className="font-mono">{selectedNode.factorInfo?.trade_count ?? 0}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">最大回撤</span>
                <span className="font-mono text-destructive">{formatNumber((selectedNode.factorInfo?.max_drawdown ?? 0) * 100)}%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">状态</span>
                <div className="flex gap-1">
                  {selectedNode.isRunning && <Badge className="bg-green-500/10 text-green-500 hover:bg-green-500/20">Running</Badge>}
                  {selectedNode.isCandidate && <Badge className="bg-amber-500/10 text-amber-500 hover:bg-amber-500/20">候选</Badge>}
                  {!selectedNode.isRunning && !selectedNode.isCandidate && <Badge variant="outline">历史</Badge>}
                </div>
              </div>
              {selectedNode.parent_id && (
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">父节点</span>
                  <span className="font-mono text-xs">{selectedNode.parent_id.slice(0, 8)}...</span>
                </div>
              )}
              <div className="pt-2">
                <Button variant="outline" size="sm" className="w-full" onClick={() => setSelectedNodeId(null)}>
                  清除选择
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex h-48 flex-col items-center justify-center gap-2 text-muted-foreground">
              <ChevronRight className="h-8 w-8 opacity-50" />
              <p className="text-sm">点击血缘树节点查看详情</p>
            </div>
          )}
        </div>
      </div>

      <div className="rounded-lg border bg-card p-4">
        <div className="mb-4 flex items-center gap-2 text-sm font-semibold">
          <Activity className="h-4 w-4 text-primary" />
          代际时间线
        </div>
        <div className="flex items-center gap-2 overflow-x-auto pb-2">
          {generations.map((g, idx) => (
            <div
              key={g.generation}
              className="flex shrink-0 flex-col items-center gap-1 rounded-md border border-border bg-accent/50 px-4 py-2"
            >
              <span className="text-xs font-semibold">Gen {g.generation}</span>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span className="text-green-500">{formatNumber(g.bestFitness)}</span>
                <span>/</span>
                <span>{g.count}个</span>
              </div>
              {idx < generations.length - 1 && (
                <ChevronRight className="absolute right-0 h-3 w-3 translate-x-1/2 text-muted-foreground" />
              )}
            </div>
          ))}
          {generations.length === 0 && (
            <div className="text-sm text-muted-foreground">暂无代际数据</div>
          )}
        </div>
      </div>
    </div>
  )
}
