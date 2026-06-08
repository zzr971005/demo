import { useEffect, useState, useCallback, useMemo } from 'react'
import { factorApi, type EvolutionNode, type EvolutionFactor } from '@/lib/api'
import { wsClient } from '@/lib/websocket'

export interface GenerationInfo {
  generation: number
  bestFitness: number
  avgFitness: number
  diversityScore: number
  count: number
}

export interface PrimitiveFamily {
  name: string
  count: number
  color: string
}

export interface TreeNode extends EvolutionNode {
  factorInfo?: EvolutionFactor
  depth: number
  x: number
  y: number
  isRunning: boolean
  isCandidate: boolean
}

export interface DiversityMetrics {
  entropy: number
  uniquePrimitives: number
  totalStrategies: number
  crossRate: number
}

export function useEvolution(symbol?: string) {
  const [nodes, setNodes] = useState<EvolutionNode[]>([])
  const [factors, setFactors] = useState<EvolutionFactor[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [runningFactorId, setRunningFactorId] = useState<string | null>(null)
  const [candidateIds, setCandidateIds] = useState<Set<string>>(new Set())

  const fetchData = useCallback(async () => {
    if (!symbol) return
    setLoading(true)
    setError(null)
    try {
      const [treeRes, factorsRes] = await Promise.all([
        factorApi.getEvolutionTree(symbol),
        factorApi.getBySymbol(symbol),
      ])
      setNodes(treeRes.data.tree || [])
      setFactors(factorsRes.data.factors || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载进化数据失败')
    } finally {
      setLoading(false)
    }
  }, [symbol])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  useEffect(() => {
    if (!symbol) return
    const unsub = wsClient.subscribe<{
      symbol: string
      running_factor_id?: string
      candidate_ids?: string[]
    }>('factor_evolution', (data) => {
      if (data.symbol !== symbol) return
      if (data.running_factor_id) {
        setRunningFactorId(data.running_factor_id)
      }
      if (data.candidate_ids) {
        setCandidateIds(new Set(data.candidate_ids))
      }
    })
    return unsub
  }, [symbol])

  const generations = useMemo<GenerationInfo[]>(() => {
    const genMap = new Map<number, GenerationInfo>()
    for (const node of nodes) {
      const gen = node.generation
      const existing = genMap.get(gen)
      if (existing) {
        existing.count++
        existing.bestFitness = Math.max(existing.bestFitness, node.sharpe_ratio)
        existing.avgFitness += node.sharpe_ratio
      } else {
        genMap.set(gen, {
          generation: gen,
          bestFitness: node.sharpe_ratio,
          avgFitness: node.sharpe_ratio,
          diversityScore: 0,
          count: 1,
        })
      }
    }
    const result = Array.from(genMap.values())
      .map((g) => ({ ...g, avgFitness: g.avgFitness / g.count }))
      .sort((a, b) => a.generation - b.generation)
    return result
  }, [nodes])

  const primitiveFamilies = useMemo<PrimitiveFamily[]>(() => {
    const familyMap = new Map<string, number>()
    for (const factor of factors) {
      const family = factor.origin || 'unknown'
      familyMap.set(family, (familyMap.get(family) || 0) + 1)
    }
    const colors = [
      '#3b82f6',
      '#10b981',
      '#f59e0b',
      '#ef4444',
      '#8b5cf6',
      '#ec4899',
      '#06b6d4',
      '#84cc16',
    ]
    return Array.from(familyMap.entries()).map(([name, count], i) => ({
      name,
      count,
      color: colors[i % colors.length],
    }))
  }, [factors])

  const treeData = useMemo<TreeNode[]>(() => {
    const factorMap = new Map(factors.map((f) => [f.id, f]))
    const nodeMap = new Map<string, TreeNode>()

    for (const node of nodes) {
      nodeMap.set(node.id, {
        ...node,
        factorInfo: factorMap.get(node.factor_id),
        depth: 0,
        x: 0,
        y: 0,
        isRunning: node.factor_id === runningFactorId,
        isCandidate: candidateIds.has(node.factor_id),
      })
    }

    const roots: TreeNode[] = []
    for (const node of nodeMap.values()) {
      if (!node.parent_id) {
        roots.push(node)
      }
    }

    function assignDepth(nodeId: string, depth: number) {
      const node = nodeMap.get(nodeId)
      if (!node) return
      node.depth = depth
      for (const childId of node.children) {
        assignDepth(childId, depth + 1)
      }
    }

    for (const root of roots) {
      assignDepth(root.id, 0)
    }

    return Array.from(nodeMap.values())
  }, [nodes, factors, runningFactorId, candidateIds])

  const diversityMetrics = useMemo<DiversityMetrics>(() => {
    const total = factors.length || 1
    const families = new Set(factors.map((f) => f.origin))
    const entropy =
      -primitiveFamilies.reduce((sum, f) => {
        const p = f.count / total
        return sum + p * Math.log2(p)
      }, 0) || 0
    return {
      entropy: Number(entropy.toFixed(2)),
      uniquePrimitives: families.size,
      totalStrategies: factors.length,
      crossRate: Number(((nodes.filter((n) => n.parent_id).length / (nodes.length || 1)) * 100).toFixed(1)),
    }
  }, [factors, primitiveFamilies, nodes])

  return {
    nodes,
    factors,
    generations,
    primitiveFamilies,
    treeData,
    diversityMetrics,
    loading,
    error,
    runningFactorId,
    candidateIds,
    refresh: fetchData,
  }
}
