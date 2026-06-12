import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Badge } from '../../components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { API_BASE_URL } from '../../config'

interface QualityReport {
  symbol: string
  data_points: number
  missing_rate: number
  outlier_rate: number
  quality_score: number
  last_updated: string
}

interface DataCheck {
  check_id: string
  check_type: string
  status: 'passed' | 'failed' | 'warning'
  message: string
  timestamp: string
}

export default function DataQuality() {
  const [reports, setReports] = useState<QualityReport[]>([])
  const [checks, setChecks] = useState<DataCheck[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchReports()
    fetchChecks()
  }, [])

  const fetchReports = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/data-quality/summary`)
      if (res.ok) {
        const data = await res.json()
        setReports(Array.isArray(data.reports) ? data.reports : [])
      }
    } catch (error) {
      console.error('Failed to fetch quality reports:', error)
    }
  }

  const fetchChecks = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/data-quality/checks`)
      if (res.ok) {
        const data = await res.json()
        setChecks(Array.isArray(data.checks) ? data.checks : [])
      }
    } catch (error) {
      console.error('Failed to fetch data checks:', error)
    }
  }

  const handleRunCheck = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/data-quality/check`, {
        method: 'POST',
      })
      if (res.ok) {
        fetchReports()
        fetchChecks()
      }
    } catch (error) {
      console.error('Failed to run data check:', error)
    } finally {
      setLoading(false)
    }
  }

  const getScoreBadge = (score: number) => {
    if (score >= 90) return <Badge variant="default">优秀</Badge>
    if (score >= 70) return <Badge variant="secondary">良好</Badge>
    if (score >= 50) return <Badge variant="outline">一天</Badge>
    return <Badge variant="destructive">失败</Badge>
  }

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive'> = {
      passed: 'default',
      warning: 'secondary',
      failed: 'destructive',
    }
    const labels: Record<string, string> = {
      passed: '通过',
      warning: '警告',
      failed: '失败',
    }
    return <Badge variant={variants[status]}>{labels[status]}</Badge>
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">数据质量监控</h1>
        <Button onClick={handleRunCheck} disabled={loading}>
          {loading ? '检查中...' : '运行检查'}
        </Button>
      </div>

      {/* 质量报告 */}
      <Card>
        <CardHeader>
          <CardTitle>数据质量报告</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>品种</TableHead>
                <TableHead>数据点数</TableHead>
                <TableHead>缺失率</TableHead>
                <TableHead>异常值</TableHead>
                <TableHead>质量评分</TableHead>
                <TableHead>最后更新</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {reports.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground">
                    暂无质量报告
                  </TableCell>
                </TableRow>
              ) : (
                reports.map((report, idx) => (
                  <TableRow key={idx}>
                    <TableCell>{report.symbol}</TableCell>
                    <TableCell>{report.data_points.toLocaleString()}</TableCell>
                    <TableCell>{(report.missing_rate * 100).toFixed(2)}%</TableCell>
                    <TableCell>{(report.outlier_rate * 100).toFixed(2)}%</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span>{report.quality_score.toFixed(1)}</span>
                        {getScoreBadge(report.quality_score)}
                      </div>
                    </TableCell>
                    <TableCell>{new Date(report.last_updated).toLocaleString()}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 数据检查结果*/}
      <Card>
        <CardHeader>
          <CardTitle>数据检查结果</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>检查ID</TableHead>
                <TableHead>检查类型</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>消息</TableHead>
                <TableHead>时间</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {checks.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground">
                    暂无检查结果                  </TableCell>
                </TableRow>
              ) : (
                checks.map((check, idx) => (
                  <TableRow key={idx}>
                    <TableCell>{check.check_id}</TableCell>
                    <TableCell>{check.check_type}</TableCell>
                    <TableCell>{getStatusBadge(check.status)}</TableCell>
                    <TableCell>{check.message}</TableCell>
                    <TableCell>{new Date(check.timestamp).toLocaleString()}</TableCell>
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
