import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { Badge } from '../../components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { API_BASE_URL } from '../../config'
import { SYMBOLS } from '@/constants/symbols'

interface Report {
  report_id: string
  report_type: string
  symbol: string
  generated_at: string
  status: 'completed' | 'generating' | 'failed'
  file_url: string
}

export default function ReportGeneration() {
  const [reports, setReports] = useState<Report[]>([])
  const [loading, setLoading] = useState(false)
  const [reportType, setReportType] = useState('performance')
  const [symbol, setSymbol] = useState('RB')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  const fetchReports = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/report-generation/reports`)
      if (res.ok) {
        const data = await res.json()
        setReports(Array.isArray(data.reports) ? data.reports : [])
      }
    } catch (error) {
      console.error('Failed to fetch reports:', error)
    }
  }

  const handleGenerateReport = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/report-generation/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          report_type: reportType,
          symbol,
          start_date: startDate,
          end_date: endDate,
        }),
      })
      if (res.ok) {
        alert('报告生成任务已提交')
        fetchReports()
      } else {
        alert('报告生成失败')
      }
    } catch (error) {
      console.error('Failed to generate report:', error)
      alert('报告生成失败')
    } finally {
      setLoading(false)
    }
  }

  const handleDownloadReport = async (reportId: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/report-generation/download/${reportId}`)
      if (res.ok) {
        const blob = await res.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `report_${reportId}.pdf`
        a.click()
      }
    } catch (error) {
      console.error('Failed to download report:', error)
    }
  }

  useEffect(() => {
    fetchReports()
  }, [])

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive'> = {
      completed: 'default',
      generating: 'secondary',
      failed: 'destructive',
    }
    const labels: Record<string, string> = {
      completed: '已完成',
      generating: '生成中',
      failed: '失败',
    }
    return <Badge variant={variants[status]}>{labels[status]}</Badge>
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">报告管理</h1>

      <Card>
        <CardHeader>
          <CardTitle>生成报告</CardTitle>
          <CardDescription>选择报告类型和参数</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="text-sm font-medium">报告类型</label>
              <Select value={reportType} onValueChange={setReportType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="performance">性能报告</SelectItem>
                  <SelectItem value="risk">风险报告</SelectItem>
                  <SelectItem value="factor">因子报告</SelectItem>
                  <SelectItem value="strategy">策略报告</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium">品种</label>
              <Select value={symbol} onValueChange={setSymbol}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SYMBOLS.map((s) => (
                    <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium">开始日期</label>
              <Input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium">结束日期</label>
              <Input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
          </div>
          <Button className="mt-4" onClick={handleGenerateReport} disabled={loading}>
            {loading ? '生成中..' : '生成报告'}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>报告列表</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>报告ID</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>品种</TableHead>
                <TableHead>生成时间</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {reports.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground">
                    暂无报告
                  </TableCell>
                </TableRow>
              ) : (
                reports.map((report) => (
                  <TableRow key={report.report_id}>
                    <TableCell>{report.report_id}</TableCell>
                    <TableCell>{report.report_type}</TableCell>
                    <TableCell>{report.symbol}</TableCell>
                    <TableCell>{new Date(report.generated_at).toLocaleString()}</TableCell>
                    <TableCell>{getStatusBadge(report.status)}</TableCell>
                    <TableCell>
                      {report.status === 'completed' && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleDownloadReport(report.report_id)}
                        >
                          下载
                        </Button>
                      )}
                    </TableCell>
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
