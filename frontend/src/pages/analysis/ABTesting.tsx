import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Badge } from '../../components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { API_BASE_URL } from '../../config'

interface ABTest {
  test_id: string
  name: string
  control_strategy: string
  test_strategy: string
  status: 'running' | 'completed' | 'stopped'
  start_date: string
  end_date: string
  control_return: number
  test_return: number
  significance: number
}

export default function ABTesting() {
  const [tests, setTests] = useState<ABTest[]>([])
  const [loading, setLoading] = useState(false)

  const [newTest, setNewTest] = useState({
    name: '',
    control_strategy: '',
    test_strategy: '',
  })

  const fetchTests = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/ab-testing/tests`)
      if (res.ok) {
        const data = await res.json()
        setTests(Array.isArray(data.tests) ? data.tests : [])
      }
    } catch (error) {
      console.error('Failed to fetch A/B tests:', error)
    }
  }

  const handleCreateTest = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/ab-testing/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newTest),
      })
      if (res.ok) {
        alert('A/B测试创建成功')
        fetchTests()
        setNewTest({ name: '', control_strategy: '', test_strategy: '' })
      } else {
        alert('A/B测试创建失败')
      }
    } catch (error) {
      console.error('Failed to create test:', error)
      alert('A/B测试创建失败')
    } finally {
      setLoading(false)
    }
  }

  const handleStopTest = async (testId: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/ab-testing/tests/${testId}/finalize`, {
        method: 'POST',
      })
      if (res.ok) {
        fetchTests()
      }
    } catch (error) {
      console.error('Failed to stop test:', error)
    }
  }

  useEffect(() => {
    fetchTests()
  }, [])

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive'> = {
      running: 'default',
      completed: 'secondary',
      stopped: 'destructive',
    }
    const labels: Record<string, string> = {
      running: '运行中',
      completed: '已完成',
      stopped: '已停止',
    }
    return <Badge variant={variants[status]}>{labels[status]}</Badge>
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">A/B测试</h1>

      <Card>
        <CardHeader>
          <CardTitle>创建A/B测试</CardTitle>
          <CardDescription>对比两个策略的表现</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-sm font-medium">测试名称</label>
              <Input
                placeholder="测试名称"
                value={newTest.name}
                onChange={(e) => setNewTest({ ...newTest, name: e.target.value })}
              />
            </div>
            <div>
              <label className="text-sm font-medium">对照组策略</label>
              <Input
                placeholder="对照组策略ID"
                value={newTest.control_strategy}
                onChange={(e) => setNewTest({ ...newTest, control_strategy: e.target.value })}
              />
            </div>
            <div>
              <label className="text-sm font-medium">测试组策略</label>
              <Input
                placeholder="测试组策略ID"
                value={newTest.test_strategy}
                onChange={(e) => setNewTest({ ...newTest, test_strategy: e.target.value })}
              />
            </div>
          </div>
          <Button className="mt-4" onClick={handleCreateTest} disabled={loading}>
            {loading ? '创建中..' : '创建测试'}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>A/B测试列表</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>测试ID</TableHead>
                <TableHead>名称</TableHead>
                <TableHead>对照组策略</TableHead>
                <TableHead>测试组策略</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>对照组收益</TableHead>
                <TableHead>测试组收益</TableHead>
                <TableHead>显著性</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tests.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center text-muted-foreground">
                    暂无A/B测试
                  </TableCell>
                </TableRow>
              ) : (
                tests.map((test) => (
                  <TableRow key={test.test_id}>
                    <TableCell>{test.test_id}</TableCell>
                    <TableCell>{test.name}</TableCell>
                    <TableCell>{test.control_strategy}</TableCell>
                    <TableCell>{test.test_strategy}</TableCell>
                    <TableCell>{getStatusBadge(test.status)}</TableCell>
                    <TableCell className={test.control_return >= 0 ? 'text-green-600' : 'text-red-600'}>
                      {(test.control_return * 100).toFixed(2)}%
                    </TableCell>
                    <TableCell className={test.test_return >= 0 ? 'text-green-600' : 'text-red-600'}>
                      {(test.test_return * 100).toFixed(2)}%
                    </TableCell>
                    <TableCell>
                      <Badge variant={test.significance < 0.05 ? 'default' : 'secondary'}>
                        {test.significance.toFixed(3)}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {test.status === 'running' && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleStopTest(test.test_id)}
                        >
                          停止
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
