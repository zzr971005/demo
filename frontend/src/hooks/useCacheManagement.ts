import { useState, useEffect } from 'react'

export interface CacheStatus {
  total_symbols: number
  total_size: string
  data_integrity: number
  last_update: string | null
  next_update: string | null
}

export interface CacheSymbol {
  symbol: string
  data_type: string
  time_range: string
  record_count: number
  file_size: string
  quality: string
  status: string
  last_update: string | null
}

export interface SchedulerStatus {
  status: string
  next_run: string | null
  cron_expression: string
  last_run: string | null
  last_result: string
  auto_start: boolean
}

export interface QualityCheck {
  integrity: { status: string; details: string }
  backup_consistency: { status: string; details: string }
  term_structure: { status: string; details: string }
  timeliness: { status: string; details: string }
  anomalies: Array<{ symbol: string; type: string; description: string }>
}

export interface UpdateHistory {
  id: string
  timestamp: string
  type: string
  symbols: string[]
  status: string
  duration: string
  message: string
}

export function useCacheManagement() {
  const [status, setStatus] = useState<CacheStatus | null>(null)
  const [symbols, setSymbols] = useState<CacheSymbol[]>([])
  const [history, setHistory] = useState<UpdateHistory[]>([])
  const [quality, setQuality] = useState<QualityCheck | null>(null)
  const [scheduler, setScheduler] = useState<SchedulerStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

  const fetchStatus = async () => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/cache/status`)
      if (!res.ok) throw new Error('Failed to fetch cache status')
      const data = await res.json()
      setStatus(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const fetchSymbols = async () => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/cache/symbols`)
      if (!res.ok) throw new Error('Failed to fetch cache symbols')
      const data = await res.json()
      setSymbols(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const fetchQuality = async () => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/cache/quality/check`)
      if (!res.ok) throw new Error('Failed to fetch quality check')
      const data = await res.json()
      setQuality(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const fetchScheduler = async () => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/cache/scheduler/status`)
      if (!res.ok) throw new Error('Failed to fetch scheduler status')
      const data = await res.json()
      setScheduler(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const fetchHistory = async (limit: number = 20) => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/cache/history?limit=${limit}`)
      if (!res.ok) throw new Error('Failed to fetch update history')
      const data = await res.json()
      setHistory(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const triggerUpdate = async (type: string, symbols?: string[]) => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/cache/update`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ type, symbols }),
      })
      if (!res.ok) throw new Error('Failed to trigger update')
      const data = await res.json()
      return data
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      throw err
    } finally {
      setLoading(false)
    }
  }

  const triggerScheduler = async () => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/cache/scheduler/trigger`, {
        method: 'POST',
      })
      if (!res.ok) throw new Error('Failed to trigger scheduler')
      const data = await res.json()
      return data
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      throw err
    } finally {
      setLoading(false)
    }
  }

  const deleteCache = async (symbol: string, dataType: string) => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/cache/${symbol}/${dataType}`, {
        method: 'DELETE',
      })
      if (!res.ok) throw new Error('Failed to delete cache')
      const data = await res.json()
      return data
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      throw err
    } finally {
      setLoading(false)
    }
  }

  const cleanupExpired = async (days: number = 30) => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/cache/cleanup/expired`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ days }),
      })
      if (!res.ok) throw new Error('Failed to cleanup expired cache')
      const data = await res.json()
      return data
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      throw err
    } finally {
      setLoading(false)
    }
  }

  const refreshAll = async () => {
    await Promise.all([
      fetchStatus(),
      fetchSymbols(),
      fetchQuality(),
      fetchScheduler(),
      fetchHistory(),
    ])
  }

  // Initial load
  useEffect(() => {
    refreshAll()
  }, [])

  return {
    status,
    symbols,
    history,
    quality,
    scheduler,
    loading,
    error,
    fetchStatus,
    fetchSymbols,
    fetchQuality,
    fetchScheduler,
    fetchHistory,
    triggerUpdate,
    triggerScheduler,
    deleteCache,
    cleanupExpired,
    refreshAll,
  }
}
