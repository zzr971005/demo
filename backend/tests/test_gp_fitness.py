"""
GP适应度评估集成测试

测试内容：
1. 因子编译器测试
2. 适应度评估器测试
3. 多品种评估测试
4. 批量评估测试
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import pandas as pd
from quant_engine.ops.gp_individual import GPNode, GPIndividual, random_individual
from quant_engine.ops.gp_fitness import (
    FitnessEvaluator,
    FitnessConfig,
    FitnessResult,
    FactorCompiler,
    MultiSymbolFitnessEvaluator,
)


def generate_test_data(n: int = 1000) -> pd.DataFrame:
    """生成测试数据"""
    np.random.seed(42)
    
    # 确保最小数据量（用于滚动计算）
    n = max(n, 100)
    
    # 生成随机价格序列
    returns = np.random.normal(0.0001, 0.02, n)
    close = 4000 * np.exp(np.cumsum(returns))
    
    # 生成OHLC
    high = close * (1 + np.abs(np.random.normal(0, 0.005, n)))
    low = close * (1 - np.abs(np.random.normal(0, 0.005, n)))
    open_px = close * (1 + np.random.normal(0, 0.002, n))
    
    # 确保高低价正确
    high = np.maximum(high, np.maximum(open_px, close))
    low = np.minimum(low, np.minimum(open_px, close))
    
    volume = np.random.randint(10000, 100000, n)
    open_interest = np.random.randint(50000, 200000, n)
    
    df = pd.DataFrame({
        'open': open_px,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
        'open_interest': open_interest,
    })
    
    return df


def test_factor_compiler():
    """测试因子编译器"""
    print("=" * 60)
    print("测试1: 因子编译器")
    print("=" * 60)
    
    # 创建简单个体: close - ts_mean(close, 20)
    root = GPNode(
        node_type='binop',
        name='-',
        children=[
            GPNode(node_type='var', name='close'),
            GPNode(
                node_type='func',
                name='ts_mean',
                children=[
                    GPNode(node_type='var', name='close'),
                    GPNode(node_type='const', name='const', value=20),
                ],
            ),
        ],
    )
    individual = GPIndividual(root=root)
    
    print(f"表达式: {individual.to_expression()}")
    print(f"节点数: {individual.get_node_count()}")
    print(f"树深度: {individual.get_depth()}")
    
    # 编译
    compiler = FactorCompiler(data_columns=['open', 'high', 'low', 'close', 'volume'])
    func = compiler.compile(individual)
    
    if func is None:
        print("编译失败!")
        return False
    
    print("编译成功!")
    
    # 测试计算
    data = generate_test_data(100)
    factor = func(data)
    
    print(f"因子值统计:")
    print(f"  长度: {len(factor)}")
    print(f"  均值: {np.nanmean(factor):.4f}")
    print(f"  标准差: {np.nanstd(factor):.4f}")
    print(f"  NaN数量: {np.sum(np.isnan(factor))}")
    
    print("通过!")
    return True


def test_fitness_evaluator():
    """测试适应度评估器"""
    print("\n" + "=" * 60)
    print("测试2: 适应度评估器")
    print("=" * 60)
    
    # 生成测试数据
    data = generate_test_data(500)
    print(f"数据长度: {len(data)}")
    
    # 创建评估器
    config = FitnessConfig(
        init_capital=1_000_000.0,
        upper_threshold=0.5,
        lower_threshold=-0.5,
        complexity_penalty_enabled=True,
    )
    evaluator = FitnessEvaluator(config)
    
    # 创建测试个体
    # 个体1: 简单动量因子 close - ts_mean(close, 20)
    root1 = GPNode(
        node_type='binop',
        name='-',
        children=[
            GPNode(node_type='var', name='close'),
            GPNode(
                node_type='func',
                name='ts_mean',
                children=[
                    GPNode(node_type='var', name='close'),
                    GPNode(node_type='const', name='const', value=20),
                ],
            ),
        ],
    )
    ind1 = GPIndividual(root=root1, id="test_001")
    
    # 个体2: zscore因子
    root2 = GPNode(
        node_type='func',
        name='zscore',
        children=[
            GPNode(node_type='var', name='close'),
            GPNode(node_type='const', name='const', value=20),
        ],
    )
    ind2 = GPIndividual(root=root2, id="test_002")
    
    # 评估个体
    print("\n评估个体1 (动量因子):")
    result1 = evaluator.evaluate(ind1, data, symbol="RB")
    if result1.valid:
        print(f"  夏普比率: {result1.sharpe:.4f}")
        print(f"  Calmar: {result1.calmar:.4f}")
        print(f"  最大回撤: {result1.max_drawdown:.4f}")
        print(f"  总收益: {result1.total_return:.4f}")
        print(f"  交易次数: {result1.total_trades}")
        print(f"  胜率: {result1.win_rate:.4f}")
        print(f"  原始适应度: {result1.raw_fitness:.4f}")
        print(f"  惩罚后适应度: {result1.penalized_fitness:.4f}")
        print(f"  节点数: {result1.node_count}")
        print(f"  树深度: {result1.tree_depth}")
    else:
        print(f"  评估失败: {result1.error_message}")
    
    print("\n评估个体2 (zscore因子):")
    result2 = evaluator.evaluate(ind2, data, symbol="RB")
    if result2.valid:
        print(f"  夏普比率: {result2.sharpe:.4f}")
        print(f"  Calmar: {result2.calmar:.4f}")
        print(f"  最大回撤: {result2.max_drawdown:.4f}")
        print(f"  总收益: {result2.total_return:.4f}")
        print(f"  交易次数: {result2.total_trades}")
        print(f"  胜率: {result2.win_rate:.4f}")
        print(f"  原始适应度: {result2.raw_fitness:.4f}")
        print(f"  惩罚后适应度: {result2.penalized_fitness:.4f}")
        print(f"  节点数: {result2.node_count}")
        print(f"  树深度: {result2.tree_depth}")
    else:
        print(f"  评估失败: {result2.error_message}")
    
    print("\n通过!")
    return True


def test_batch_evaluation():
    """测试批量评估"""
    print("\n" + "=" * 60)
    print("测试3: 批量评估")
    print("=" * 60)
    
    # 生成数据
    data = generate_test_data(300)
    
    # 创建评估器
    config = FitnessConfig()
    evaluator = FitnessEvaluator(config)
    
    # 创建多个测试个体
    individuals = []
    
    # 个体1: close - ts_mean(close, 20)
    ind1 = GPIndividual(
        root=GPNode(
            node_type='binop',
            name='-',
            children=[
                GPNode(node_type='var', name='close'),
                GPNode(
                    node_type='func',
                    name='ts_mean',
                    children=[
                        GPNode(node_type='var', name='close'),
                        GPNode(node_type='const', name='const', value=20),
                    ],
                ),
            ],
        ),
        id="batch_001",
    )
    individuals.append(ind1)
    
    # 个体2: close / high
    ind2 = GPIndividual(
        root=GPNode(
            node_type='binop',
            name='/',
            children=[
                GPNode(node_type='var', name='close'),
                GPNode(node_type='var', name='high'),
            ],
        ),
        id="batch_002",
    )
    individuals.append(ind2)
    
    # 个体3: volume
    ind3 = GPIndividual(
        root=GPNode(node_type='var', name='volume'),
        id="batch_003",
    )
    individuals.append(ind3)
    
    # 批量评估
    print(f"批量评估 {len(individuals)} 个个体...")
    results = evaluator.evaluate_batch(individuals, data, symbol="RB")
    
    print("\n评估结果汇总:")
    for result in results:
        status = "成功" if result.valid else f"失败({result.error_message})"
        print(f"  {result.individual_id}: 夏普={result.sharpe:.4f}, 适应度={result.penalized_fitness:.4f}, 状态={status}")
    
    valid_count = sum(1 for r in results if r.valid)
    print(f"\n有效评估: {valid_count}/{len(results)}")
    
    print("\n通过!")
    return True


def test_multi_symbol_evaluation():
    """测试多品种评估"""
    print("\n" + "=" * 60)
    print("测试4: 多品种评估")
    print("=" * 60)
    
    # 生成多品种数据
    symbols = ["RB", "HC", "I"]
    data_dict = {}
    for sym in symbols:
        data_dict[sym] = generate_test_data(400)
    
    print(f"品种数量: {len(symbols)}")
    
    # 创建评估器
    config = FitnessConfig()
    multi_evaluator = MultiSymbolFitnessEvaluator(config)
    
    # 创建测试个体
    root = GPNode(
        node_type='binop',
        name='-',
        children=[
            GPNode(node_type='var', name='close'),
            GPNode(
                node_type='func',
                name='ts_mean',
                children=[
                    GPNode(node_type='var', name='close'),
                    GPNode(node_type='const', name='const', value=20),
                ],
            ),
        ],
    )
    individual = GPIndividual(root=root, id="multi_001")
    
    # 多品种评估
    print("\n各品种评估结果:")
    results = multi_evaluator.evaluate(individual, data_dict)
    for symbol, result in results.items():
        if result.valid:
            print(f"  {symbol}: 夏普={result.sharpe:.4f}, 适应度={result.penalized_fitness:.4f}")
        else:
            print(f"  {symbol}: 评估失败 - {result.error_message}")
    
    # 聚合评估
    print("\n聚合评估结果:")
    agg_result, _ = multi_evaluator.evaluate_aggregate(individual, data_dict, aggregation="mean")
    if agg_result.valid:
        print(f"  聚合夏普: {agg_result.sharpe:.4f}")
        print(f"  聚合Calmar: {agg_result.calmar:.4f}")
        print(f"  聚合收益: {agg_result.total_return:.4f}")
        print(f"  聚合适应度: {agg_result.penalized_fitness:.4f}")
    
    print("\n通过!")
    return True


def test_complexity_penalty():
    """测试复杂度惩罚"""
    print("\n" + "=" * 60)
    print("测试5: 复杂度惩罚")
    print("=" * 60)
    
    data = generate_test_data(300)
    
    # 创建不同复杂度的个体
    # 简单个体: 1个节点
    simple_root = GPNode(node_type='var', name='close')
    simple_ind = GPIndividual(root=simple_root, id="simple")
    
    # 中等复杂度个体: 7个节点 (ts_mean需要2个子节点)
    medium_root = GPNode(
        node_type='binop',
        name='-',
        children=[
            GPNode(
                node_type='func',
                name='ts_mean',
                children=[
                    GPNode(node_type='var', name='close'),
                    GPNode(node_type='const', name='const', value=20),
                ],
            ),
            GPNode(
                node_type='func',
                name='ts_mean',
                children=[
                    GPNode(node_type='var', name='close'),
                    GPNode(node_type='const', name='const', value=10),
                ],
            ),
        ],
    )
    medium_ind = GPIndividual(root=medium_root, id="medium")
    
    # 评估
    config = FitnessConfig(complexity_penalty_enabled=True, complexity_penalty_coef=0.02)
    evaluator = FitnessEvaluator(config)
    
    print(f"简单个体节点数: {simple_ind.get_node_count()}")
    result1 = evaluator.evaluate(simple_ind, data, symbol="RB")
    if result1.valid:
        print(f"  原始适应度: {result1.raw_fitness:.4f}")
        print(f"  惩罚后适应度: {result1.penalized_fitness:.4f}")
    
    print(f"\n中等个体节点数: {medium_ind.get_node_count()}")
    result2 = evaluator.evaluate(medium_ind, data, symbol="RB")
    if result2.valid:
        print(f"  原始适应度: {result2.raw_fitness:.4f}")
        print(f"  惩罚后适应度: {result2.penalized_fitness:.4f}")
        print(f"  惩罚值: {result2.raw_fitness - result2.penalized_fitness:.4f}")
    
    print("\n通过!")
    return True


def test_invalid_individuals():
    """测试无效个体处理"""
    print("\n" + "=" * 60)
    print("测试6: 无效个体处理")
    print("=" * 60)
    
    data = generate_test_data(100)
    config = FitnessConfig()
    evaluator = FitnessEvaluator(config)
    
    # 无效个体1: 引用不存在的数据列
    invalid_root1 = GPNode(node_type='var', name='nonexistent_column')
    invalid_ind1 = GPIndividual(root=invalid_root1, id="invalid_001")
    
    result1 = evaluator.evaluate(invalid_ind1, data, symbol="RB")
    print(f"无效个体1 (不存在列): valid={result1.valid}, 错误={result1.error_message}")
    
    print("\n通过!")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("GP适应度评估集成测试")
    print("=" * 60)
    
    tests = [
        ("因子编译器", test_factor_compiler),
        ("适应度评估器", test_fitness_evaluator),
        ("批量评估", test_batch_evaluation),
        ("多品种评估", test_multi_symbol_evaluation),
        ("复杂度惩罚", test_complexity_penalty),
        ("无效个体处理", test_invalid_individuals),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"测试 {name} 失败!")
        except Exception as e:
            failed += 1
            print(f"测试 {name} 异常: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"测试结果: 通过 {passed}/{len(tests)}, 失败 {failed}/{len(tests)}")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
