"""分析因子值分布特征"""
import sys
sys.path.insert(0, '.')

from app.db import get_session
from app.models import Candidate
from sqlalchemy import select
from quant_engine.data.unified_hub import DataHub
from quant_engine.factors.registry import FACTOR_REGISTRY
from quant_engine.ops.gp_fitness import FitnessEvaluator, FactorCompiler
import pandas as pd
import numpy as np
from collections import defaultdict

# 加载数据
hub = DataHub()
data = hub.get_ohlcv('RB', '1h')
print(f"数据形状: {data.shape}")

# 创建适应度评估器
evaluator = FitnessEvaluator()

# 获取数据库中的因子
formulas = []
max_group_stats = None

with get_session() as session:
    stmt = select(Candidate).where(Candidate.symbol == 'RB')
    results = session.execute(stmt).scalars().all()

    print(f"\n总因子数: {len(results)}")

    # 按性能指标分组
    groups = defaultdict(list)
    for c in results:
        key = (round(c.sharpe_train, 4), round(c.calmar, 4), c.total_trades)
        groups[key].append(c)

    # 找出最大的重复组
    max_group = max(groups.values(), key=len)
    print(f"\n最大重复组: {len(max_group)} 个因子")
    print(f"性能指标: Sharpe={max_group[0].sharpe_train:.4f}, Calmar={max_group[0].calmar:.4f}, TotalTrades={max_group[0].total_trades}")

    # 获取唯一公式
    formulas = list(set([c.formula for c in max_group]))
    max_group_stats = (max_group[0].sharpe_train, max_group[0].calmar, max_group[0].total_trades)

print(f"唯一公式数: {len(formulas)}")

# 计算每个公式的因子值
print(f"\n=== 计算因子值分布 ===")
factor_values = {}
factor_stats = {}

# 构建评估命名空间
eval_namespace = {
    'open': data['open'].values,
    'high': data['high'].values,
    'low': data['low'].values,
    'close': data['close'].values,
    'volume': data['volume'].values,
    'open_interest': data.get('open_interest', pd.Series([0]*len(data))).values,
    'far_close': data['close'].values,  # 简化处理
    'near_close': data['close'].values,  # 简化处理
}

# 添加所有因子函数到命名空间
for name, meta in FACTOR_REGISTRY.items():
    eval_namespace[name] = meta.func

for i, formula in enumerate(formulas[:20]):  # 只分析前20个
    try:
        # 使用eval直接计算因子值
        raw_values = eval(formula, eval_namespace)

        # 确保是numpy数组
        if not isinstance(raw_values, np.ndarray):
            raw_values = np.array(raw_values)

        factor_values[formula] = raw_values

        # 统计信息
        valid = raw_values[np.isfinite(raw_values)]
        if len(valid) == 0:
            print(f"\n{i+1}. {formula[:50]}... 无有效值")
            continue

        stats = {
            'min': valid.min(),
            'max': valid.max(),
            'mean': valid.mean(),
            'std': valid.std(),
            'median': np.median(valid),
            'q25': np.percentile(valid, 25),
            'q75': np.percentile(valid, 75),
            'iqr': np.percentile(valid, 75) - np.percentile(valid, 25),
        }
        factor_stats[formula] = stats

        print(f"\n{i+1}. {formula[:50]}...")
        print(f"   原始值: min={stats['min']:.4f}, max={stats['max']:.4f}, mean={stats['mean']:.4f}, std={stats['std']:.4f}")
        print(f"   分位数: q25={stats['q25']:.4f}, median={stats['median']:.4f}, q75={stats['q75']:.4f}, iqr={stats['iqr']:.4f}")

        # 分位数归一化
        normalized = evaluator._normalize_factor_quantile(raw_values)
        valid_norm = normalized[np.isfinite(normalized)]
        print(f"   归一化: min={valid_norm.min():.4f}, max={valid_norm.max():.4f}, mean={valid_norm.mean():.4f}, std={valid_norm.std():.4f}")

    except Exception as e:
        print(f"\n{i+1}. {formula[:50]}... 错误: {e}")
        continue

# 分析因子值分布相似度
print(f"\n=== 因子值分布相似度分析 ===")
formula_list = list(factor_stats.keys())
similarity_matrix = np.zeros((len(formula_list), len(formula_list)))

for i in range(len(formula_list)):
    for j in range(i+1, len(formula_list)):
        f1, f2 = formula_list[i], formula_list[j]
        v1 = factor_values[f1]
        v2 = factor_values[f2]

        # 只比较有效位置
        valid_mask = np.isfinite(v1) & np.isfinite(v2)
        if valid_mask.sum() > 0:
            # 计算相关系数
            corr = np.corrcoef(v1[valid_mask], v2[valid_mask])[0, 1]
            similarity_matrix[i, j] = corr
            similarity_matrix[j, i] = corr

            if abs(corr) > 0.9:
                print(f"高度相关 ({corr:.3f}):")
                print(f"  {f1[:40]}...")
                print(f"  {f2[:40]}...")

# 分析归一化后的交易信号相似度
print(f"\n=== 归一化后交易信号相似度 ===")
signal_similarity = np.zeros((len(formula_list), len(formula_list)))

for i in range(len(formula_list)):
    for j in range(i+1, len(formula_list)):
        f1, f2 = formula_list[i], formula_list[j]
        v1 = factor_values[f1]
        v2 = factor_values[f2]

        # 归一化
        norm1 = evaluator._normalize_factor_quantile(v1)
        norm2 = evaluator._normalize_factor_quantile(v2)

        # 生成交易信号
        sig1 = np.zeros_like(norm1)
        sig1[norm1 > 0.5] = 1
        sig1[norm1 < -0.5] = -1

        sig2 = np.zeros_like(norm2)
        sig2[norm2 > 0.5] = 1
        sig2[norm2 < -0.5] = -1

        # 比较信号
        valid_mask = np.isfinite(norm1) & np.isfinite(norm2)
        same = np.sum(sig1[valid_mask] == sig2[valid_mask])
        total = valid_mask.sum()
        signal_similarity[i, j] = same / total if total > 0 else 0
        signal_similarity[j, i] = signal_similarity[i, j]

        if signal_similarity[i, j] > 0.9:
            print(f"信号高度相似 ({signal_similarity[i, j]:.3f}):")
            print(f"  {f1[:40]}...")
            print(f"  {f2[:40]}...")

# 统计信息
print(f"\n=== 统计摘要 ===")
print(f"分析了 {len(formula_list)} 个公式")
print(f"因子值相关系数 > 0.9 的对数: {np.sum((similarity_matrix > 0.9) & (similarity_matrix < 1)) // 2}")
print(f"信号相似度 > 0.9 的对数: {np.sum((signal_similarity > 0.9) & (signal_similarity < 1)) // 2}")
