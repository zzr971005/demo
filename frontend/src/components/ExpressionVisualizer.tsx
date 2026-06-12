import { useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface TreeNode {
  name: string
  value?: string
  children?: TreeNode[]
}

interface ExpressionVisualizerProps {
  expression: string
  className?: string
}

/**
 * 解析GP表达式为树形结构
 * 例如: add(mul(close, volume), sma(high, 5))
 */
function parseExpression(expr: string): TreeNode | null {
  if (!expr || expr.trim() === '') return null

  // 移除多余空格
  const cleanExpr = expr.replace(/\s+/g, '')

  let pos = 0

  function parseNode(): TreeNode | null {
    if (pos >= cleanExpr.length) return null

    // 解析函数名或变量
    let name = ''
    while (pos < cleanExpr.length && /[a-zA-Z0-9_]/.test(cleanExpr[pos])) {
      name += cleanExpr[pos]
      pos++
    }

    if (!name) return null

    // 检查是否有括号（表示函数调用）
    if (pos < cleanExpr.length && cleanExpr[pos] === '(') {
      pos++ // 跳过左括号

      const children: TreeNode[] = []
      let depth = 1
      let argStart = pos

      while (pos < cleanExpr.length && depth > 0) {
        if (cleanExpr[pos] === '(') {
          depth++
        } else if (cleanExpr[pos] === ')') {
          depth--
          if (depth === 0) {
            // 解析最后一个参数
            const arg = cleanExpr.substring(argStart, pos)
            if (arg.trim()) {
              const child = parseExpression(arg)
              if (child) children.push(child)
            }
            pos++ // 跳过右括号
            break
          }
        } else if (cleanExpr[pos] === ',' && depth === 1) {
          // 参数分隔符
          const arg = cleanExpr.substring(argStart, pos)
          if (arg.trim()) {
            const child = parseExpression(arg)
            if (child) children.push(child)
          }
          pos++
          argStart = pos
        }
        pos++
      }

      return { name, children }
    }

    // 叶子节点（变量或数字）
    return { name, value: name }
  }

  return parseNode()
}

/**
 * 递归渲染树节点
 */
function TreeNodeComponent({
  node,
  depth = 0,
}: {
  node: TreeNode
  depth?: number
}) {
  const isLeaf = !node.children || node.children.length === 0
  const colors = [
    'bg-blue-500',
    'bg-green-500',
    'bg-purple-500',
    'bg-orange-500',
    'bg-pink-500',
    'bg-cyan-500',
  ]
  const color = colors[depth % colors.length]

  return (
    <div className="flex flex-col items-center">
      {/* 节点 */}
      <div
        className={`
          px-3 py-1.5 rounded-lg text-white text-sm font-medium
          shadow-md transition-transform hover:scale-105
          ${isLeaf ? 'bg-gray-500' : color}
        `}
      >
        {node.name}
      </div>

      {/* 子节点 */}
      {node.children && node.children.length > 0 && (
        <div className="mt-3">
          {/* 连接线 */}
          <div className="flex justify-center mb-2">
            <div className="w-px h-4 bg-gray-300" />
          </div>

          {/* 子节点容器 */}
          <div className="flex gap-4">
            {node.children.map((child, index) => (
              <div key={index} className="relative">
                {/* 水平连接线 */}
                {index > 0 && (
                  <div className="absolute -left-4 top-0 w-4 h-px bg-gray-300" />
                )}
                {index < node.children!.length - 1 && (
                  <div className="absolute right-0 top-0 w-4 h-px bg-gray-300" />
                )}
                <TreeNodeComponent node={child} depth={depth + 1} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * 表达式统计信息
 */
function ExpressionStats({ expression }: { expression: string }) {
  const stats = useMemo(() => {
    const tree = parseExpression(expression)
    if (!tree) return null

    let nodeCount = 0
    let maxDepth = 0
    const operators = new Set<string>()
    const variables = new Set<string>()

    function traverse(node: TreeNode, depth: number) {
      nodeCount++
      maxDepth = Math.max(maxDepth, depth)

      if (node.children && node.children.length > 0) {
        operators.add(node.name)
        node.children.forEach(child => traverse(child, depth + 1))
      } else {
        variables.add(node.name)
      }
    }

    traverse(tree, 1)

    return {
      nodeCount,
      maxDepth,
      operators: Array.from(operators),
      variables: Array.from(variables),
    }
  }, [expression])

  if (!stats) return null

  return (
    <div className="grid grid-cols-2 gap-4 text-sm">
      <div className="space-y-1">
        <span className="text-muted-foreground">节点数:</span>
        <span className="ml-2 font-mono font-medium">{stats.nodeCount}</span>
      </div>
      <div className="space-y-1">
        <span className="text-muted-foreground">树深度:</span>
        <span className="ml-2 font-mono font-medium">{stats.maxDepth}</span>
      </div>
      <div className="col-span-2 space-y-1">
        <span className="text-muted-foreground">运算符:</span>
        <div className="flex flex-wrap gap-1 mt-1">
          {stats.operators.map(op => (
            <span key={op} className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">
              {op}
            </span>
          ))}
        </div>
      </div>
      <div className="col-span-2 space-y-1">
        <span className="text-muted-foreground">变量:</span>
        <div className="flex flex-wrap gap-1 mt-1">
          {stats.variables.map(v => (
            <span key={v} className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs">
              {v}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

/**
 * 表达式可视化组件
 */
export function ExpressionVisualizer({
  expression,
  className,
}: ExpressionVisualizerProps) {
  const tree = useMemo(() => parseExpression(expression), [expression])

  if (!tree) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-sm">因子表达式</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm">无效表达式</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-sm flex items-center gap-2">
          因子表达式
          <span className="text-xs font-normal text-muted-foreground font-mono">
            {expression.length > 50 ? expression.substring(0, 50) + '...' : expression}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 树形可视化 */}
        <div className="overflow-x-auto">
          <div className="min-w-max p-4 bg-gray-50 rounded-lg">
            <TreeNodeComponent node={tree} />
          </div>
        </div>

        {/* 统计信息 */}
        <div className="pt-4 border-t">
          <h4 className="text-sm font-medium mb-2">表达式统计</h4>
          <ExpressionStats expression={expression} />
        </div>
      </CardContent>
    </Card>
  )
}

export default ExpressionVisualizer
