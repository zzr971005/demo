import { useState, useEffect, useCallback } from 'react'
import api from '@/lib/api'

export interface PrimitiveParam {
  name: string
  type: string
  default: string | number | boolean | null
  description?: string
}

export interface PrimitiveInfo {
  name: string
  family: string
  family_code: string
  description: string
  params: PrimitiveParam[]
  supports: string[]
}

export interface FactorLibrary {
  total: number
  families: Record<string, number>
  primitives: PrimitiveInfo[]
}

export interface FactorDetail {
  primitive: PrimitiveInfo
  example: string
  related_primitives: string[]
}

export interface ValidationViolation {
  code: string
  message: string
  severity: 'fatal' | 'warning'
  penalty: number
}

export interface ValidationResult {
  is_valid: boolean
  penalty_factor: number
  violations: ValidationViolation[]
  ast?: Record<string, unknown>
  expression: string
}

export interface TestResult {
  success: boolean
  result?: number[]
  error?: string
  execution_time_ms: number
}

export interface FamilyInfo {
  name: string
  code: string
  count: number
  primitives: string[]
}

export interface FamiliesResponse {
  total_families: number
  families: Record<string, FamilyInfo>
}

export function useFactors() {
  const [library, setLibrary] = useState<FactorLibrary | null>(null)
  const [families, setFamilies] = useState<FamiliesResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 获取因子库列表
  const fetchLibrary = useCallback(async (family?: string) => {
    setLoading(true)
    setError(null)
    try {
      const params = family ? `?family=${encodeURIComponent(family)}` : ''
      const response = await api.get<FactorLibrary>(`/factors${params}`)
      setLibrary(response.data)
      return response.data
    } catch (err) {
      const msg = err instanceof Error ? err.message : '获取因子库失败'
      setError(msg)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  // 获取因子族列表
  const fetchFamilies = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.get<FamiliesResponse>('/families')
      setFamilies(response.data)
      return response.data
    } catch (err) {
      const msg = err instanceof Error ? err.message : '获取因子族失败'
      setError(msg)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  // 获取因子详情
  const getFactorDetail = useCallback(async (name: string): Promise<FactorDetail> => {
    const response = await api.get<FactorDetail>(`/factors/${name}`)
    return response.data
  }, [])

  // 验证因子表达式
  const validateExpression = useCallback(async (
    expression: string,
    symbol?: string
  ): Promise<ValidationResult> => {
    const response = await api.post<ValidationResult>('/factors/validate', {
      expression,
      symbol,
    })
    return response.data
  }, [])

  // 测试因子表达式
  const testExpression = useCallback(async (
    expression: string,
    data: Record<string, number[]>
  ): Promise<TestResult> => {
    const response = await api.post<TestResult>('/factors/test', {
      expression,
      data,
    })
    return response.data
  }, [])

  useEffect(() => {
    fetchLibrary()
    fetchFamilies()
  }, [fetchLibrary, fetchFamilies])

  return {
    library,
    families,
    loading,
    error,
    fetchLibrary,
    fetchFamilies,
    getFactorDetail,
    validateExpression,
    testExpression,
  }
}
