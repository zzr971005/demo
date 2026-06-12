import { Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  GitBranch,
  SlidersHorizontal,
  Moon,
  Sun,
  Activity,
  Wifi,
  WifiOff,
  BookOpen,
  Zap,
  TrendingUp,
  CheckCircle2,
  Scale,
  RefreshCcw,
  Settings,
  FileCheck,
  Database,
  Play,
  Shield,
  DollarSign,
  Bell,
  Layers,
  BarChart3,
  ClipboardCheck,
  AlertTriangle,
  LineChart,
  PieChart,
  Target,
  ChevronDown,
  ChevronRight,
  FlaskConical,
  TestTube,
  FileText,
  Monitor,
  Repeat,
  SearchCheck,
} from 'lucide-react'
import { useAppStore } from '@/store'
import { cn } from '@/lib/utils'
import { useState } from 'react'

const navSections = [
  {
    title: '核心功能',
    items: [
      { path: '/', label: '仪表盘', icon: LayoutDashboard },
      { path: '/evolution-center', label: '进化中心', icon: Zap },
      { path: '/evolution', label: '进化树', icon: GitBranch },
      { path: '/factors', label: '因子库', icon: BookOpen },
      { path: '/evolution-mode-selector', label: '进化模式', icon: FlaskConical },
    ],
  },
  {
    title: '策略管理',
    items: [
      { path: '/validation', label: '验证监控', icon: CheckCircle2 },
      { path: '/baseline', label: '基线对比', icon: Scale },
      { path: '/strategy-evaluation', label: '策略评估', icon: Activity },
      { path: '/strategy-replacement', label: '策略替换', icon: RefreshCcw },
      { path: '/strategy-management', label: '策略管理', icon: Settings },
      { path: '/generalization-test', label: '泛化测试', icon: TestTube },
    ],
  },
  {
    title: '交易执行',
    items: [
      { path: '/simulation', label: '模拟交易', icon: Play },
      { path: '/live-trading', label: '实盘监控', icon: Activity },
      { path: '/trading', label: '交易执行', icon: TrendingUp },
      { path: '/manual', label: '手动切换', icon: SlidersHorizontal },
      { path: '/replay-engine', label: '行情回放', icon: Repeat },
      { path: '/multi-symbol-monitor', label: '多品种监控', icon: Monitor },
    ],
  },
  {
    title: '风控管理',
    items: [
      { path: '/risk-management', label: '风控管理', icon: Shield },
      { path: '/position-limit', label: '仓位配置', icon: Layers },
      { path: '/strategy-switch', label: '策略切换', icon: RefreshCcw },
      { path: '/capital-management', label: '资金管理', icon: DollarSign },
      { path: '/alert-system', label: '告警管理', icon: Bell },
    ],
  },
  {
    title: '高级分析',
    items: [
      { path: '/order-types', label: '订单类型', icon: Layers },
      { path: '/microstructure', label: '市场微观结构', icon: BarChart3 },
      { path: '/portfolio-optimization', label: '组合优化', icon: PieChart },
      { path: '/data-quality', label: '数据质量', icon: ClipboardCheck },
      { path: '/liquidity-risk', label: '流动性风险', icon: AlertTriangle },
      { path: '/transaction-cost', label: '交易成本', icon: DollarSign },
      { path: '/correlation-analysis', label: '相关性分析', icon: LineChart },
      { path: '/backtest-live-comparison', label: '回测实盘对比', icon: Target },
      { path: '/ab-testing', label: 'AB测试', icon: FlaskConical },
      { path: '/cross-market-trading', label: '跨市场交易', icon: TrendingUp },
      { path: '/anomaly-detection', label: '异常检测', icon: SearchCheck },
    ],
  },
  {
    title: '系统管理',
    items: [
      { path: '/scheduler', label: '调度管理', icon: Settings },
      { path: '/position-reconciliation', label: '仓位对账', icon: FileCheck },
      { path: '/cache', label: '数据缓存', icon: Database },
      { path: '/data-integrity', label: '数据完整性', icon: FileCheck },
      { path: '/report-generation', label: '报告生成', icon: FileText },
    ],
  },
]

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const theme = useAppStore((s) => s.theme)
  const toggleTheme = useAppStore((s) => s.toggleTheme)
  const wsConnected = useAppStore((s) => s.wsConnected)
  const systemStatus = useAppStore((s) => s.systemStatus)
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['核心功能', '策略管理', '交易执行']))

  const toggleSection = (title: string) => {
    const newExpanded = new Set(expandedSections)
    if (newExpanded.has(title)) {
      newExpanded.delete(title)
    } else {
      newExpanded.add(title)
    }
    setExpandedSections(newExpanded)
  }

  const handleThemeToggle = () => {
    console.log('Theme toggle clicked, current theme:', theme)
    toggleTheme()
  }

  const getCurrentPageLabel = () => {
    for (const section of navSections) {
      const item = section.items.find((i) => i.path === location.pathname)
      if (item) return item.label
    }
    return '仪表盘'
  }

  return (
    <div className="flex h-screen w-full bg-background text-foreground">
      <aside className="hidden md:flex w-56 flex-col border-r border-border bg-card">
        <div className="flex h-14 items-center gap-2 border-b border-border px-4">
          <Activity className="h-5 w-5 text-primary" />
          <span className="text-sm font-bold">因子挖掘系统</span>
        </div>

        <nav className="flex-1 space-y-1 p-3 overflow-auto">
          {navSections.map((section) => {
            const isExpanded = expandedSections.has(section.title)
            return (
              <div key={section.title}>
                <button
                  onClick={() => toggleSection(section.title)}
                  className="flex items-center justify-between w-full px-3 py-2 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
                >
                  {section.title}
                  {isExpanded ? (
                    <ChevronDown className="h-3 w-3" />
                  ) : (
                    <ChevronRight className="h-3 w-3" />
                  )}
                </button>
                {isExpanded && (
                  <div className="space-y-1 pl-2">
                    {section.items.map((item) => {
                      const active = location.pathname === item.path
                      const Icon = item.icon
                      return (
                        <Link
                          key={item.path}
                          to={item.path}
                          className={cn(
                            'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                            active
                              ? 'bg-primary text-primary-foreground'
                              : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                          )}
                        >
                          <Icon className="h-4 w-4" />
                          {item.label}
                        </Link>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}
        </nav>

        <div className="border-t border-border p-3">
          <button
            onClick={handleThemeToggle}
            className="inline-flex items-center justify-center gap-2 w-full h-7 px-3 py-2 rounded-lg text-sm font-medium transition-all hover:bg-muted hover:text-foreground bg-transparent border border-transparent"
          >
            {theme === 'dark' ? (
              <>
                <Sun className="h-4 w-4" />
                <span>切换亮色</span>
              </>
            ) : (
              <>
                <Moon className="h-4 w-4" />
                <span>切换暗色</span>
              </>
            )}
          </button>
        </div>
      </aside>

      <div className="flex flex-1 flex-col min-w-0">
        <header className="flex h-14 items-center justify-between border-b border-border bg-card px-4 md:px-6">
          <div className="flex items-center gap-2 md:gap-4">
            <h2 className="text-sm font-semibold truncate">
              {getCurrentPageLabel()}
            </h2>
          </div>

          <div className="flex items-center gap-2 md:gap-4">
            <div className="hidden sm:flex items-center gap-2">
              {wsConnected ? (
                <Wifi className="h-4 w-4 text-green-500" />
              ) : (
                <WifiOff className="h-4 w-4 text-destructive" />
              )}
              <span className="text-xs text-muted-foreground hidden md:inline">
                {wsConnected ? '实时连接' : '连接断开'}
              </span>
            </div>

            <div
              className={cn(
                'h-2 w-2 rounded-full flex-shrink-0',
                systemStatus === 'running' && 'bg-green-500',
                systemStatus === 'paused' && 'bg-yellow-500',
                systemStatus === 'error' && 'bg-destructive'
              )}
            />
            <span className="text-xs text-muted-foreground capitalize hidden sm:inline">
              {systemStatus === 'running' && '运行中'}
              {systemStatus === 'paused' && '已暂停'}
              {systemStatus === 'error' && '异常'}
            </span>
          </div>
        </header>

        <main className="flex-1 overflow-auto p-4 md:p-6">{children}</main>
      </div>
    </div>
  )
}