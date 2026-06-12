import { Routes, Route, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import Dashboard from './pages/system/Dashboard'
import EvolutionTree from './pages/evolution/EvolutionTree'
import EvolutionCenter from './pages/evolution/EvolutionCenter'
import ValidationMonitor from './pages/evolution/ValidationMonitor'
import EvolutionModeSelector from './pages/evolution/EvolutionModeSelector'
import GeneralizationTest from './pages/evolution/GeneralizationTest'
import BaselineComparison from './pages/analysis/BaselineComparison'
import StrategyReplacement from './pages/strategy/StrategyReplacement'
import StrategyEvaluation from './pages/strategy/StrategyEvaluation'
import StrategyManagement from './pages/strategy/StrategyManagement'
import SchedulerManager from './pages/system/SchedulerManager'
import PositionReconciliation from './pages/trading/PositionReconciliation'
import SymbolDetail from './pages/system/SymbolDetail'
import ManualSwitch from './pages/trading/ManualSwitch'
import FactorLibrary from './pages/evolution/FactorLibrary'
import LiveTrading from './pages/trading/LiveTrading'
import Trading from './pages/trading/Trading'
import DataCacheManagement from './pages/data/DataCacheManagement'
import Simulation from './pages/trading/Simulation'
import RiskManagement from './pages/risk/RiskManagement'
import PositionLimit from './pages/risk/PositionLimit'
import StrategySwitch from './pages/strategy/StrategySwitch'
import CapitalManagement from './pages/risk/CapitalManagement'
import AlertSystem from './pages/risk/AlertSystem'
import OrderTypes from './pages/trading/OrderTypes'
import Microstructure from './pages/analysis/Microstructure'
import PortfolioOptimization from './pages/analysis/PortfolioOptimization'
import DataQuality from './pages/data/DataQuality'
import LiquidityRisk from './pages/risk/LiquidityRisk'
import TransactionCost from './pages/trading/TransactionCost'
import CorrelationAnalysis from './pages/analysis/CorrelationAnalysis'
import BacktestLiveComparison from './pages/analysis/BacktestLiveComparison'
import ReportGeneration from './pages/trading/ReportGeneration'
import ABTesting from './pages/analysis/ABTesting'
import CrossMarketTrading from './pages/analysis/CrossMarketTrading'
import AnomalyDetection from './pages/analysis/AnomalyDetection'
import ReplayEngine from './pages/trading/ReplayEngine'
import DataIntegrity from './pages/data/DataIntegrity'

// Placeholder pages for new features
const PlaceholderPage = ({ title }: { title: string }) => (
  <div className="p-6">
    <h1 className="text-2xl font-bold mb-4">{title}</h1>
    <p className="text-muted-foreground">功能开发中...</p>
  </div>
)

function RouteErrorBoundary({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const [key, setKey] = useState(location.pathname)
  useEffect(() => { setKey(location.pathname) }, [location.pathname])
  return <ErrorBoundary key={key}>{children}</ErrorBoundary>
}

function App() {
  return (
    <Layout>
      <RouteErrorBoundary>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/evolution" element={<EvolutionTree />} />
        <Route path="/evolution-center" element={<EvolutionCenter />} />
        <Route path="/validation" element={<ValidationMonitor />} />
        <Route path="/evolution-mode-selector" element={<EvolutionModeSelector />} />
        <Route path="/generalization-test" element={<GeneralizationTest />} />
        <Route path="/baseline" element={<BaselineComparison />} />
        <Route path="/strategy-replacement" element={<StrategyReplacement />} />
        <Route path="/strategy-evaluation" element={<StrategyEvaluation />} />
        <Route path="/strategy-management" element={<StrategyManagement />} />
        <Route path="/scheduler" element={<SchedulerManager />} />
        <Route path="/position-reconciliation" element={<PositionReconciliation />} />
        <Route path="/symbol/:symbol" element={<SymbolDetail />} />
        <Route path="/manual" element={<ManualSwitch />} />
        <Route path="/factors" element={<FactorLibrary />} />
        <Route path="/live-trading" element={<LiveTrading />} />
        <Route path="/trading" element={<Trading />} />
        <Route path="/cache" element={<DataCacheManagement />} />
        
        {/* New routes for advanced features */}
        <Route path="/simulation" element={<Simulation />} />
        <Route path="/risk-management" element={<RiskManagement />} />
        <Route path="/position-limit" element={<PositionLimit />} />
        <Route path="/strategy-switch" element={<StrategySwitch />} />
        <Route path="/capital-management" element={<CapitalManagement />} />
        <Route path="/alert-system" element={<AlertSystem />} />
        <Route path="/order-types" element={<OrderTypes />} />
        <Route path="/microstructure" element={<Microstructure />} />
        <Route path="/portfolio-optimization" element={<PortfolioOptimization />} />
        <Route path="/data-quality" element={<DataQuality />} />
        <Route path="/liquidity-risk" element={<LiquidityRisk />} />
        <Route path="/transaction-cost" element={<TransactionCost />} />
        <Route path="/correlation-analysis" element={<CorrelationAnalysis />} />
        <Route path="/backtest-live-comparison" element={<BacktestLiveComparison />} />
        <Route path="/report-generation" element={<ReportGeneration />} />
        <Route path="/ab-testing" element={<ABTesting />} />
        <Route path="/cross-market-trading" element={<CrossMarketTrading />} />
        <Route path="/anomaly-detection" element={<AnomalyDetection />} />
        <Route path="/replay-engine" element={<ReplayEngine />} />
        <Route path="/data-integrity" element={<DataIntegrity />} />
        <Route path="/multi-symbol-monitor" element={<PlaceholderPage title="多品种监控" />} />
      </Routes>
      </RouteErrorBoundary>
    </Layout>
  )
}

export default App
