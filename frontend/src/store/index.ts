import { create } from 'zustand'
import type { SymbolStatus, FactorInfo } from '@/lib/api'

interface AppState {
  theme: 'light' | 'dark'
  toggleTheme: () => void

  symbols: SymbolStatus[]
  setSymbols: (symbols: SymbolStatus[]) => void
  updateSymbol: (symbol: string, patch: Partial<SymbolStatus>) => void

  selectedSymbol: string | null
  setSelectedSymbol: (symbol: string | null) => void

  factors: Record<string, FactorInfo[]>
  setFactors: (symbol: string, factors: FactorInfo[]) => void

  wsConnected: boolean
  setWsConnected: (connected: boolean) => void

  systemStatus: 'running' | 'paused' | 'error'
  setSystemStatus: (status: 'running' | 'paused' | 'error') => void
}

const getStoredTheme = (): 'light' | 'dark' => {
  try {
    const stored = localStorage.getItem('app-theme')
    if (stored === 'light' || stored === 'dark') {
      return stored
    }
  } catch {}
  return 'dark'
}

export const useAppStore = create<AppState>((set) => ({
  theme: getStoredTheme(),
  toggleTheme: () =>
    set((state) => {
      const newTheme = state.theme === 'light' ? 'dark' : 'light'
      const htmlElement = document.documentElement
      
      if (newTheme === 'dark') {
        htmlElement.classList.add('dark')
      } else {
        htmlElement.classList.remove('dark')
      }
      
      localStorage.setItem('app-theme', newTheme)
      
      console.log('[Store] Theme toggled to:', newTheme)
      console.log('[Store] HTML classList:', htmlElement.classList.toString())
      
      return { theme: newTheme }
    }),

  symbols: [],
  setSymbols: (symbols) => set({ symbols }),
  updateSymbol: (symbol, patch) =>
    set((state) => ({
      symbols: state.symbols.map((s) =>
        s.symbol === symbol ? { ...s, ...patch } : s
      ),
    })),

  selectedSymbol: null,
  setSelectedSymbol: (selectedSymbol) => set({ selectedSymbol }),

  factors: {},
  setFactors: (symbol, factors) =>
    set((state) => ({
      factors: { ...state.factors, [symbol]: factors },
    })),

  wsConnected: false,
  setWsConnected: (wsConnected) => set({ wsConnected }),

  systemStatus: 'running',
  setSystemStatus: (systemStatus) => set({ systemStatus }),
}))