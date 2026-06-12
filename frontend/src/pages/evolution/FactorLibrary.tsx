import { useState, useMemo, useEffect } from 'react'
import {
  Search,
  Filter,
  Code,
  CheckCircle,
  XCircle,
  AlertTriangle,
  BookOpen,
  Layers,
  FunctionSquare,
  TrendingUp,
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useFactors, type PrimitiveInfo, type ValidationResult } from '@/hooks/useFactors'
import { cn } from '@/lib/utils'
import api from '@/lib/api'

// 族颜色映射
const FAMILY_COLORS: Record<string, string> = {
  'F1动量族': 'bg-red-500/10 text-red-600 border-red-500/20',
  'F2均值回归族': 'bg-blue-500/10 text-blue-600 border-blue-500/20',
  'F3波动率族': 'bg-purple-500/10 text-purple-600 border-purple-500/20',
  'F4价量族': 'bg-green-500/10 text-green-600 border-green-500/20',
  'F5期限结构族': 'bg-amber-500/10 text-amber-600 border-amber-500/20',
  'F6持仓量族': 'bg-cyan-500/10 text-cyan-600 border-cyan-500/20',
  'F7微观结构族': 'bg-pink-500/10 text-pink-600 border-pink-500/20',
  'F8宏观映射族': 'bg-indigo-500/10 text-indigo-600 border-indigo-500/20',
}

const FAMILY_ICONS: Record<string, string> = {
  MOMENTUM: 'F1',
  MEAN_REVERSION: 'F2',
  VOLATILITY: 'F3',
  PRICE_VOLUME: 'F4',
  TERM_STRUCTURE: 'F5',
  OPEN_INTEREST: 'F6',
  MICROSTRUCTURE: 'F7',
  MACRO_PROXY: 'F8',
}

function FamilyBadge({ family, code }: { family: string; code: string }) {
  const colorClass = FAMILY_COLORS[family] || 'bg-gray-500/10 text-gray-600'
  const icon = FAMILY_ICONS[code] || 'F?'

  return (
    <Badge variant="outline" className={cn('gap-1 font-mono', colorClass)}>
      <Layers className="h-3 w-3" />
      {icon}
    </Badge>
  )
}

function PrimitiveCard({
  primitive,
  onClick,
}: {
  primitive: PrimitiveInfo
  onClick: () => void
}) {
  return (
    <Card
      className="cursor-pointer transition-all hover:shadow-md hover:border-primary/50"
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <FunctionSquare className="h-4 w-4 text-primary" />
              <span className="font-mono font-semibold text-sm">{primitive.name}</span>
              <FamilyBadge family={primitive.family} code={primitive.family_code} />
            </div>
            <p className="text-xs text-muted-foreground line-clamp-2">
              {primitive.description}
            </p>
          </div>
        </div>
        <div className="mt-3 flex items-center gap-2">
          {primitive.params.slice(0, 2).map((param) => (
            <Badge key={param.name} variant="secondary" className="text-xs">
              {param.name}: {param.default}
            </Badge>
          ))}
          {primitive.params.length > 2 && (
            <Badge variant="secondary" className="text-xs">
              +{primitive.params.length - 2}
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function PrimitiveDetailDialog({
  primitive,
  open,
  onOpenChange,
}: {
  primitive: PrimitiveInfo | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const { validateExpression } = useFactors()
  const [expression, setExpression] = useState('')
  const [validation, setValidation] = useState<ValidationResult | null>(null)

  if (!primitive) return null

  const handleValidate = async () => {
    if (!expression.trim()) return
    const result = await validateExpression(expression)
    setValidation(result)
  }

  // 生成示例表达式
  const exampleExpression = useMemo(() => {
    const params = primitive.params
    if (primitive.name.startsWith('ts_') || primitive.name === 'zscore') {
      return `${primitive.name}(close, ${params[0]?.default || 20})`
    }
    if (primitive.name === 'obv') {
      return `${primitive.name}(close, volume)`
    }
    if (primitive.name === 'atr') {
      return `${primitive.name}(high, low, close, ${params[0]?.default || 14})`
    }
    return `${primitive.name}(${params.map((p) => p.name).join(', ')})`
  }, [primitive])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FunctionSquare className="h-5 w-5" />
            {primitive.name}
            <FamilyBadge family={primitive.family} code={primitive.family_code} />
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* 描述 */}
          <div>
            <h4 className="text-sm font-semibold mb-2">描述</h4>
            <p className="text-sm text-muted-foreground">{primitive.description}</p>
          </div>

          {/* 参数 */}
          <div>
            <h4 className="text-sm font-semibold mb-2">参数</h4>
            <div className="space-y-2">
              {(Array.isArray(primitive.params) ? primitive.params : []).map((param) => (
                <div key={param.name} className="flex items-center gap-4 text-sm">
                  <code className="bg-muted px-2 py-1 rounded">{param.name}</code>
                  <Badge variant="outline">{param.type}</Badge>
                  <span className="text-muted-foreground">默认: {String(param.default)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* 示例 */}
          <div>
            <h4 className="text-sm font-semibold mb-2">示例</h4>
            <code className="block bg-muted p-3 rounded text-sm font-mono">
              {exampleExpression}
            </code>
          </div>

          {/* 验证器 */}
          <div>
            <h4 className="text-sm font-semibold mb-2">表达式验证</h4>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="输入因子表达式，如: ts_mean(close, 20)"
                value={expression}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setExpression(e.target.value)}
                className="flex-1 px-3 py-2 border rounded-md font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <Button onClick={handleValidate} size="sm">
                <CheckCircle className="h-4 w-4 mr-1" />
                验证
              </Button>
            </div>

            {validation && (
              <div className="mt-3 space-y-2">
                <div className="flex items-center gap-2">
                  {validation.is_valid ? (
                    <>
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span className="text-sm text-green-600">验证通过</span>
                    </>
                  ) : (
                    <>
                      <XCircle className="h-4 w-4 text-red-500" />
                      <span className="text-sm text-red-600">验证失败</span>
                    </>
                  )}
                  <Badge variant="secondary">
                    惩罚系数: {validation.penalty_factor.toFixed(2)}
                  </Badge>
                </div>

                {validation.violations.length > 0 && (
                  <div className="space-y-1">
                    {(Array.isArray(validation.violations) ? validation.violations : []).map((v, i) => (
                      <div
                        key={i}
                        className={cn(
                          'text-xs p-2 rounded flex items-start gap-2',
                          v.severity === 'fatal'
                            ? 'bg-red-500/10 text-red-600'
                            : 'bg-amber-500/10 text-amber-600'
                        )}
                      >
                        {v.severity === 'fatal' ? (
                          <XCircle className="h-3 w-3 mt-0.5" />
                        ) : (
                          <AlertTriangle className="h-3 w-3 mt-0.5" />
                        )}
                        <div>
                          <span className="font-mono">[{v.code}]</span> {v.message}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export default function FactorLibrary() {
  const { library, families, loading } = useFactors()
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedFamily, setSelectedFamily] = useState<string>('all')
  const [selectedPrimitive, setSelectedPrimitive] = useState<PrimitiveInfo | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [icFilteredFactors, setIcFilteredFactors] = useState<any[]>([])
  const [icLoading, setIcLoading] = useState(false)

  // 加载IC筛选的因子
  useEffect(() => {
    fetchIcFilteredFactors()
  }, [])

  const fetchIcFilteredFactors = async () => {
    try {
      setIcLoading(true)
      const res = await api.get('/factors/ic-filtered')
      setIcFilteredFactors(res.data.factors)
    } catch (error) {
      console.error('Failed to fetch IC filtered factors:', error)
    } finally {
      setIcLoading(false)
    }
  }

  // 筛选原语
  const filteredPrimitives = useMemo(() => {
    if (!library) return []
    return library.primitives.filter((p) => {
      const matchesSearch =
        searchQuery === '' ||
        p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.description.toLowerCase().includes(searchQuery.toLowerCase())
      const matchesFamily =
        selectedFamily === 'all' || p.family_code === selectedFamily
      return matchesSearch && matchesFamily
    })
  }, [library, searchQuery, selectedFamily])

  const handlePrimitiveClick = (primitive: PrimitiveInfo) => {
    setSelectedPrimitive(primitive)
    setDetailOpen(true)
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 标题 */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <BookOpen className="h-6 w-6" />
            因子库
          </h1>
          <p className="text-muted-foreground">
            共 {library?.total || 0} 个因子原语，{families?.total_families || 0} 个族
          </p>
        </div>
      </div>

      <Tabs defaultValue="primitives" className="space-y-4">
        <TabsList>
          <TabsTrigger value="primitives">因子原语</TabsTrigger>
          <TabsTrigger value="ic-filtered">IC筛选因子</TabsTrigger>
        </TabsList>

        <TabsContent value="primitives" className="space-y-4">
          {/* 统计卡片 */}
          {families && (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
              {Object.entries(families.families).map(([code, info]) => (
                <Card
                  key={code}
                  className={cn(
                    'cursor-pointer transition-all',
                    selectedFamily === code
                      ? 'ring-2 ring-primary border-primary'
                      : 'hover:border-primary/50'
                  )}
                  onClick={() =>
                    setSelectedFamily(selectedFamily === code ? 'all' : code)
                  }
                >
                  <CardContent className="p-3 text-center">
                    <div className="text-lg font-bold">{info.count}</div>
                    <div className="text-xs text-muted-foreground truncate">
                      {FAMILY_ICONS[code]}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* 搜索和筛选 */}
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder="搜索因子原语..."
                value={searchQuery}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <Button
              variant={selectedFamily === 'all' ? 'default' : 'outline'}
              onClick={() => setSelectedFamily('all')}
            >
              <Filter className="h-4 w-4 mr-1" />
              全部
            </Button>
          </div>

          {/* 原语列表 */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filteredPrimitives.map((primitive) => (
              <PrimitiveCard
                key={primitive.name}
                primitive={primitive}
                onClick={() => handlePrimitiveClick(primitive)}
              />
            ))}
          </div>

          {filteredPrimitives.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              <Code className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>未找到匹配的因子原语</p>
            </div>
          )}

          {/* 详情对话框 */}
          <PrimitiveDetailDialog
            primitive={selectedPrimitive}
            open={detailOpen}
            onOpenChange={setDetailOpen}
          />
        </TabsContent>

        <TabsContent value="ic-filtered" className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">IC筛选因子</h2>
              <p className="text-sm text-muted-foreground">
                通过IC筛选的前50个因子
              </p>
            </div>
            <Button onClick={fetchIcFilteredFactors} size="sm">
              <TrendingUp className="h-4 w-4 mr-1" />
              刷新
            </Button>
          </div>

          {icLoading ? (
            <div className="flex h-64 items-center justify-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : (
            <div className="space-y-2">
              {icFilteredFactors.map((factor) => (
                <Card key={factor.id}>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <Badge variant="outline">{factor.symbol}</Badge>
                          <Badge variant="secondary">代数 {factor.generation}</Badge>
                          {factor.factor_category && (
                            <Badge variant="outline">{factor.factor_category}</Badge>
                          )}
                        </div>
                        <code className="block text-sm font-mono bg-muted p-2 rounded mb-2">
                          {factor.formula}
                        </code>
                        <div className="grid grid-cols-4 gap-4 text-sm">
                          <div>
                            <div className="text-muted-foreground">Sharpe</div>
                            <div className="font-semibold">{factor.sharpe_train?.toFixed(2)}</div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">IC 4h</div>
                            <div className="font-semibold">{factor.ic_mean_4h?.toFixed(3)}</div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">IC 24h</div>
                            <div className="font-semibold">{factor.ic_mean_24h?.toFixed(3)}</div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">IC 168h</div>
                            <div className="font-semibold">{factor.ic_mean_168h?.toFixed(3)}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
              {icFilteredFactors.length === 0 && (
                <div className="text-center py-12 text-muted-foreground">
                  <TrendingUp className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>暂无IC筛选因子</p>
                </div>
              )}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
