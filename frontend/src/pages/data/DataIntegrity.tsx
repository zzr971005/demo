import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { dataIntegrityApi, IntegrityCheckResult, IntegrityIssue } from '@/lib/api'
import { RefreshCw, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'

export default function DataIntegrity() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<IntegrityCheckResult | null>(null)
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)

  const runCheck = async () => {
    setLoading(true)
    try {
      const response = await dataIntegrityApi.runFullCheck()
      setResult(response.data)
    } catch (error) {
      console.error('Failed to run integrity check:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    runCheck()
  }, [])

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'destructive'
      case 'medium':
        return 'default'
      case 'low':
        return 'secondary'
      default:
        return 'outline'
    }
  }

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'high':
        return <XCircle className="h-4 w-4" />
      case 'medium':
        return <AlertTriangle className="h-4 w-4" />
      case 'low':
        return <CheckCircle className="h-4 w-4" />
      default:
        return null
    }
  }

  const categories = [
    { key: 'duplicate_expressions', label: '重复表达式', icon: '🔄' },
    { key: 'missing_ic_fields', label: '缺失IC字段', icon: '📊' },
    { key: 'abnormal_factor_values', label: '异常因子值', icon: '⚠️' },
    { key: 'inconsistent_generations', label: '代数不一致', icon: '📈' },
  ]

  const getSelectedIssues = (): IntegrityIssue[] => {
    if (!result || !selectedCategory) return []
    switch (selectedCategory) {
      case 'duplicate_expressions':
        return result.duplicate_expressions
      case 'missing_ic_fields':
        return result.missing_ic_fields
      case 'abnormal_factor_values':
        return result.abnormal_factor_values
      case 'inconsistent_generations':
        return result.inconsistent_generations
      default:
        return []
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">数据完整性检查</h1>
          <p className="text-muted-foreground">检查数据库中的数据完整性问题</p>
        </div>
        <Button onClick={runCheck} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          重新检查
        </Button>
      </div>

      {loading && !result && (
        <Card>
          <CardContent className="flex items-center justify-center py-12">
            <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
          </CardContent>
        </Card>
      )}

      {result && (
        <>
          {/* 总体概览 */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {categories.map((cat) => {
              const count = result.summary[cat.key as keyof typeof result.summary] as number
              const category = categories.find(c => c.key === cat.key)
              return (
                <Card key={cat.key} className="cursor-pointer hover:shadow-md transition-shadow"
                      onClick={() => setSelectedCategory(cat.key)}>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                      <span>{category?.icon}</span>
                      {cat.label}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{count}</div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {count === 0 ? '无问题' : '发现问题'}
                    </p>
                  </CardContent>
                </Card>
              )
            })}
          </div>

          {/* 总体状态 */}
          <Alert variant={result.total_issues === 0 ? 'default' : 'destructive'}>
            {result.total_issues === 0 ? (
              <CheckCircle className="h-4 w-4" />
            ) : (
              <AlertTriangle className="h-4 w-4" />
            )}
            <AlertTitle>
              {result.total_issues === 0 ? '数据完整性良好' : `发现 ${result.total_issues} 个问题`}
            </AlertTitle>
            <AlertDescription>
              {result.total_issues === 0
                ? '所有数据完整性检查均通过，未发现问题。'
                : '建议及时处理发现的数据完整性问题，以确保系统正常运行。'}
            </AlertDescription>
          </Alert>

          {/* 详细问题列表 */}
          {selectedCategory && (
            <Card>
              <CardHeader>
                <CardTitle>
                  {categories.find(c => c.key === selectedCategory)?.label} 详细列表
                </CardTitle>
                <CardDescription>
                  共 {getSelectedIssues().length} 个问题
                </CardDescription>
              </CardHeader>
              <CardContent>
                {getSelectedIssues().length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    无问题
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>严重程度</TableHead>
                        <TableHead>类型</TableHead>
                        <TableHead>表</TableHead>
                        <TableHead>详情</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {getSelectedIssues().map((issue, index) => (
                        <TableRow key={index}>
                          <TableCell>
                            <Badge variant={getSeverityColor(issue.severity)} className="flex items-center gap-1">
                              {getSeverityIcon(issue.severity)}
                              {issue.severity.toUpperCase()}
                            </Badge>
                          </TableCell>
                          <TableCell className="font-mono text-xs">{issue.type}</TableCell>
                          <TableCell>{issue.table}</TableCell>
                          <TableCell className="font-mono text-xs max-w-md truncate">
                            {JSON.stringify(issue.details)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
