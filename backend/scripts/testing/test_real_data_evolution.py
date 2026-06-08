"""测试使用真实数据库数据进行进化"""
import sys
sys.path.insert(0, '.')

from quant_engine.ops.evolution_center import EvolutionCenter, EvolutionTaskConfig
from quant_engine.data.hub import TimescaleHub as DataHub
import datetime

print("=== 使用真实数据库数据测试进化 ===")

# 创建DataHub连接
print("\n1. 初始化DataHub...")
try:
    data_hub = DataHub()
    print("✅ DataHub初始化成功")
except Exception as e:
    print(f"❌ DataHub初始化失败: {e}")
    sys.exit(1)

# 查看可用品种
print("\n2. 查询可用数据...")
try:
    symbols = data_hub.get_available_symbols()
    print(f"✅ 可用品种: {symbols}")
    
    # 查看某个品种的数据范围
    if symbols:
        symbol = "RB"
        info = data_hub.get_symbol_info(symbol)
        print(f"\n{symbol} 数据信息:")
        print(f"  时间范围: {info['min_time']} ~ {info['max_time']}")
        print(f"  数据量: {info['count']} 条")
except Exception as e:
    print(f"❌ 查询数据失败: {e}")

# 创建进化配置
print("\n3. 创建进化任务配置...")
config = EvolutionTaskConfig(
    task_id=f"RB_factor_{datetime.datetime.now().strftime('%Y%m%d')}",
    symbol="RB",
    data_frequency="1H",
    data_start_date="2024-01-01",
    data_end_date="2024-12-31",
    population_size=50,
    max_generations=10,
    max_stagnation=5,
    target_fitness=0.6,
    init_capital=1_000_000,
    position_size_pct=0.95,
    contract_value_per_lot=50000,
    save_top_n=20,
    save_path="./output/factors",
)

# 创建进化中心（传入data_hub）
print("\n4. 创建进化中心...")
center = EvolutionCenter(config, data_hub=data_hub)

# 注册回调
def on_generation(gen, stats):
    progress = (gen + 1) / config.max_generations * 100
    print(f"  [{progress:5.1f}%] 第{gen:2d}代 | "
          f"最佳夏普: {stats.max_sharpe:.4f} | "
          f"平均夏普: {stats.mean_sharpe:.4f} | "
          f"有效个体: {stats.valid_count}/{stats.population_size}")

center.on_generation_complete = on_generation

# 运行进化
print("\n5. 开始进化...")
try:
    result = center.run_evolution()
    
    print("\n" + "=" * 70)
    print("进化完成!")
    print("=" * 70)
    print(f"总耗时: {result.total_time:.2f}秒")
    print(f"总代数: {result.total_generations}")
    print(f"最佳适应度: {result.best_fitness:.4f}")
    print(f"最佳夏普: {result.best_sharpe:.4f}")
    
    # 展示最佳因子
    best_factors = center.get_best_factors(n=5, only_passed=False)
    if best_factors:
        print("\n" + "=" * 70)
        print("最佳因子 (Top 5)")
        print("=" * 70)
        
        for i, factor in enumerate(best_factors, 1):
            status = "✓ 通过" if factor.overfitting_passed else "✗ 未通过"
            print(f"\n#{i}: {factor.factor_id} [{status}]")
            print(f"   表达式: {factor.expression}")
            print(f"   夏普比率: {factor.sharpe:.4f} | Calmar: {factor.calmar:.4f}")
            print(f"   总收益: {factor.total_return:.2%} | 最大回撤: {factor.max_drawdown:.2%}")
            print(f"   胜率: {factor.win_rate:.2%} | 交易次数: {factor.total_trades}")
            
except Exception as e:
    print(f"❌ 进化失败: {e}")
    import traceback
    traceback.print_exc()
