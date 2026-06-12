# 遗传编程因子挖掘系统 - 实现总结

## 系统概述

这是一个完整的基于遗传编程（Genetic Programming, GP）的期货Alpha因子自动挖掘系统。系统通过进化算法自动发现具有预测能力的因子表达式，并集成过拟合检验机制确保因子的外推能力。

## 核心组件

### 1. GP个体表示 (gp_individual.py)

**核心类：**
- `GPNode` - GP树节点，支持多种节点类型：
  - 变量节点 (var): close, high, low, volume 等
  - 常量节点 (const): 数值常量
  - 函数节点 (func): ts_mean, ts_std, ts_skew 等
  - 二元操作节点 (binop): +, -, *, /, >, < 等

- `GPIndividual` - GP个体，包含：
  - 根节点（表达式树）
  - 适应度值（原始/惩罚后）
  - 夏普比率、Calmar比率等绩效指标
  - 世代信息、起源信息

**关键功能：**
- 表达式树与人类可读表达式的相互转换
- 树深度和节点复杂度计算
- 随机个体生成
- 个体克隆和变异操作

### 2. 遗传算子 (gp_operators.py)

**选择算子：**
- `tournament_selection()` - 锦标赛选择
- `roulette_selection()` - 轮盘赌选择
- `rank_selection()` - 排名选择

**交叉算子：**
- `subtree_crossover()` - 子树交叉
- `one_point_crossover()` - 单点交叉
- `crossover()` - 综合交叉（按概率选择）

**变异算子：**
- `subtree_mutation()` - 子树变异
- `point_mutation()` - 点变异
- `hoist_mutation()` - 提升变异
- `shrink_mutation()` - 收缩变异
- `mutate()` - 综合变异（按概率选择）

### 3. 适应度评估 (gp_fitness.py)

**核心类：**
- `FactorCompiler` - 因子编译器，将GP个体转换为可执行函数
- `FitnessEvaluator` - 适应度评估器
- `MultiSymbolFitnessEvaluator` - 多品种评估器
- `FitnessConfig` - 评估配置

**评估流程：**
1. 编译GP个体为可执行因子函数
2. 在历史数据上计算因子值
3. 通过向量化回测引擎计算因子绩效
4. 应用复杂度惩罚控制过拟合
5. 返回综合适应度值

**绩效指标：**
- 夏普比率 (Sharpe Ratio)
- Calmar比率
- 总收益率
- 最大回撤
- 胜率
- 交易次数
- 换手率

### 4. 过拟合检验 (gp_overfitting.py)

**核心类：**
- `OverfittingChecker` - 过拟合检验器
- `OverfittingConfig` - 检验配置

**检验方法：**
1. **PBO (Probability of Backtest Overfitting)**
   - 通过组合对称交叉验证（CSCV）计算过拟合概率
   - PBO < 0.3 视为通过

2. **DSR (Deflated Sharpe Ratio)**
   - 考虑多重检验偏差的调整后夏普比率
   - DSR > 0.6 视为通过

3. **WFE (Walk-Forward Efficiency)**
   - 滚动窗口验证的样本外/样本内效率比
   - WFE > 0.7 视为通过

### 5. 进化引擎 (gp_evolution.py)

**核心类：**
- `PopulationManager` - 种群管理器
  - 种群初始化
  - 适应度批量评估
  - 父代选择
  - 新一代生成
  - 进化统计计算

- `GeneticProgramming` - 遗传编程主算法
  - 完整进化流程控制
  - 每代回调支持
  - 停滞检测和提前终止
  - 进化历史记录

- `GenerationStats` - 单代统计信息
- `EvolutionResult` - 进化结果

**进化流程：**
```
初始化种群 → 评估适应度 → 选择父代 → 交叉变异
    ↑                                        ↓
    └─────────────────────────────────────────┘
```

### 6. 进化中心服务 (evolution_center.py)

**核心类：**
- `EvolutionTaskConfig` - 进化任务配置
- `EvolutionCenter` - 进化中心
- `EvolutionScheduler` - 任务调度器
- `FactorRecord` - 因子记录

**功能：**
- 完整的进化任务编排
- 实时进度跟踪和回调
- 过拟合检验集成
- 结果持久化和管理
- 多任务调度支持
- 因子元数据记录

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Evolution Center (进化中心)                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Task Scheduler (任务调度)                                │  │
│  └─────────────────────────────────────────────────────────┘  │
│                               ↓                                  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Genetic Programming Engine (GP进化引擎)                  │  │
│  │  ┌─────────────────────────────────────────────────────┐│  │
│  │  │ Population Manager (种群管理)                        ││  │
│  │  └─────────────────────────────────────────────────────┘│  │
│  │  ┌─────────────────────────────────────────────────────┐│  │
│  │  │ Genetic Operators (遗传算子: 选择/交叉/变异)         ││  │
│  │  └─────────────────────────────────────────────────────┘│  │
│  └─────────────────────────────────────────────────────────┘  │
│                               ↓                                  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Fitness Evaluation (适应度评估)                          │  │
│  │  ┌─────────────────────────────────────────────────────┐│  │
│  │  │ Factor Compiler (因子编译)                           ││  │
│  │  └─────────────────────────────────────────────────────┘│  │
│  │  ┌─────────────────────────────────────────────────────┐│  │
│  │  │ Vectorized Backtest (向量化回测)                     ││  │
│  │  └─────────────────────────────────────────────────────┘│  │
│  └─────────────────────────────────────────────────────────┘  │
│                               ↓                                  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Overfitting Check (过拟合检验)                            │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐                   │  │
│  │  │   PBO   │  │   DSR   │  │   WFE   │                   │  │
│  │  └─────────┘  └─────────┘  └─────────┘                   │  │
│  └─────────────────────────────────────────────────────────┘  │
│                               ↓                                  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Output (输出结果)                                        │  │
│  │  ┌─────────────────────────────────────────────────────┐│  │
│  │  │ Factor Records (因子记录)                             ││  │
│  │  │ Evolution History (进化历史)                          ││  │
│  │  │ Performance Reports (绩效报告)                        ││  │
│  │  └─────────────────────────────────────────────────────┘│  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 快速开始

### 1. 基本使用

```python
from quant_engine.ops.evolution_center import (
    EvolutionCenter,
    EvolutionTaskConfig,
)

# 创建任务配置
config = EvolutionTaskConfig(
    task_id="RB_factor_20240101",
    symbol="RB",
    description="螺纹钢Alpha因子挖掘",
    population_size=100,
    max_generations=50,
    enable_overfitting_check=True,
)

# 创建进化中心并运行
center = EvolutionCenter(config)
result = center.run_evolution()

# 获取最佳因子
best_factors = center.get_best_factors(n=10, only_passed=True)
```

### 2. 自定义回调

```python
def on_generation(gen, stats):
    progress = (gen + 1) / config.max_generations * 100
    print(f"[{progress:.1f}%] Gen {gen}: "
          f"Best Sharpe = {stats.max_sharpe:.4f}, "
          f"Valid = {stats.valid_count}")

center.on_generation_complete = on_generation
```

### 3. 多任务调度

```python
from quant_engine.ops.evolution_center import EvolutionScheduler

scheduler = EvolutionScheduler()

# 创建多个任务
for symbol in ["RB", "MA", "AG"]:
    config = EvolutionTaskConfig(
        task_id=f"{symbol}_factor",
        symbol=symbol,
        population_size=50,
        max_generations=20,
    )
    scheduler.create_task(config)

# 运行所有任务
results = scheduler.run_all_tasks()
```

## 配置参数说明

### 进化参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| population_size | 100 | 种群大小，推荐 50-200 |
| max_generations | 50 | 最大进化代数 |
| max_stagnation | 10 | 连续 N 代无改进则停止 |
| target_fitness | None | 达到目标适应度则停止 |
| init_max_depth | 3 | 初始个体最大深度 |
| max_tree_depth | 6 | 进化中最大树深度 |
| max_node_count | 50 | 最大节点数限制 |

### 遗传算子概率

| 参数 | 默认值 | 说明 |
|------|--------|------|
| crossover_rate | 0.8 | 交叉概率 |
| mutation_rate | 0.2 | 变异概率 |
| subtree_mutation_rate | 0.4 | 子树变异概率 |
| point_mutation_rate | 0.3 | 点变异概率 |
| hoist_mutation_rate | 0.15 | 提升变异概率 |
| shrink_mutation_rate | 0.15 | 收缩变异概率 |

### 过拟合检验阈值

| 参数 | 默认值 | 说明 |
|------|--------|------|
| pbo_threshold | 0.3 | PBO < 阈值通过 |
| dsr_threshold | 0.6 | DSR > 阈值通过 |
| wfe_threshold | 0.7 | WFE > 阈值通过 |

### 适应度权重

适应度 = (夏普 × 1.0) + (Calmar × 0.5) + (收益 × 0.3) - 复杂度惩罚

## 文件结构

```
backend/quant_engine/ops/
├── gp_individual.py          # GP个体表示
├── gp_operators.py           # 遗传算子
├── gp_fitness.py            # 适应度评估
├── gp_overfitting.py        # 过拟合检验
├── gp_evolution.py          # 进化引擎
└── evolution_center.py       # 进化中心服务

backend/tests/
├── test_gp_fitness.py       # 适应度测试
└── test_evolution_end_to_end.py  # 端到端测试

backend/examples/
└── quick_start_evolution.py # 快速开始示例
```

## 测试运行

```bash
# 运行端到端测试
cd backend
poetry run python tests/test_evolution_end_to_end.py

# 运行适应度测试
poetry run python tests/test_gp_fitness.py

# 运行快速开始示例
poetry run python examples/quick_start_evolution.py
```

## 关键特性

### 1. 防过拟合机制
- 复杂度惩罚（节点数、树深度）
- PBO/DSR/WFE三重检验
- 种群多样性维护
- 表达式重复度检测

### 2. 高效计算
- Numba加速回测引擎
- 批量适应度评估
- 向量化因子计算

### 3. 可扩展性
- 插件式原语函数注册
- 自定义适应度函数
- 回调机制支持
- 多品种并行评估

### 4. 结果可解释性
- 人类可读因子表达式
- 完整进化历史记录
- 详细绩效报告
- 过拟合检验详情

## 最佳实践建议

### 种群大小选择
- 快速验证：20-50 个体
- 常规挖掘：100-200 个体
- 深度挖掘：300-500 个体

### 进化代数选择
- 快速测试：5-10 代
- 常规进化：30-50 代
- 深度进化：100-200 代

### 过拟合检验
- 始终启用过拟合检验
- 关注PBO指标，低于0.3为佳
- DSR应大于0.6
- WFE应大于0.7

### 因子多样性
- 关注表达式唯一性
- 避免简单线性变换的重复
- 定期检查种群多样性

## 后续优化方向

1. **并行计算**：分布式进化，多进程/多线程评估
2. **GPU加速**：CUDA支持的大规模回测
3. **增量进化**：基于已有因子的持续优化
4. **因子聚类**：相似性检测，减少重复因子
5. **实盘监控**：因子绩效衰减预警
6. **贝叶斯优化**：自适应进化参数调整
7. **元学习**：跨品种知识迁移
8. **强化学习**：基于市场状态的动态因子选择

## 总结

本系统实现了完整的遗传编程因子挖掘流程，包括：
- 灵活的GP个体表示和操作
- 高效的适应度评估和回测引擎
- 严格的过拟合检验机制
- 完整的任务编排和管理
- 丰富的结果输出和分析工具

系统设计遵循模块化、可扩展原则，便于后续功能扩展和性能优化。
