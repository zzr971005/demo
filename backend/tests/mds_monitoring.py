"""MDS可视化监控模块 - 监控因子多样性"""
import sys
sys.path.insert(0, '.')

from app.db import get_session
from app.models import Candidate
from sqlalchemy import select
from quant_engine.data.unified_hub import DataHub
from quant_engine.factors.registry import FACTOR_REGISTRY
import numpy as np
import pandas as pd
from sklearn.manifold import MDS
from sklearn.metrics import pairwise_distances
import matplotlib.pyplot as plt
from collections import defaultdict

def compute_factor_correlation_matrix(formulas, data):
    """计算因子值相关矩阵"""
    factor_values = {}

    # 构建评估命名空间
    eval_namespace = {
        'open': data['open'].values,
        'high': data['high'].values,
        'low': data['low'].values,
        'close': data['close'].values,
        'volume': data['volume'].values,
        'open_interest': data.get('open_interest', pd.Series([0]*len(data))).values,
        'far_close': data['close'].values,
        'near_close': data['close'].values,
    }

    # 添加所有因子函数到命名空间
    for name, meta in FACTOR_REGISTRY.items():
        eval_namespace[name] = meta.func

    # 计算每个公式的因子值
    for formula in formulas:
        try:
            raw_values = eval(formula, eval_namespace)
            if not isinstance(raw_values, np.ndarray):
                raw_values = np.array(raw_values)

            # 归一化
            valid = raw_values[np.isfinite(raw_values)]
            if len(valid) > 0:
                median = np.median(valid)
                q25 = np.percentile(valid, 25)
                q75 = np.percentile(valid, 75)
                iqr = q75 - q25
                if iqr > 0:
                    normalized = (raw_values - median) / iqr
                else:
                    normalized = (raw_values - median) / (np.max(valid) - np.min(valid) + 1e-10)
                factor_values[formula] = normalized
        except Exception as e:
            print(f"计算因子值失败: {formula[:30]}... 错误: {e}")
            continue

    # 计算相关矩阵
    formulas_list = list(factor_values.keys())
    n = len(formulas_list)
    corr_matrix = np.zeros((n, n))

    for i in range(n):
        for j in range(i, n):
            v1 = factor_values[formulas_list[i]]
            v2 = factor_values[formulas_list[j]]
            valid_mask = np.isfinite(v1) & np.isfinite(v2)
            if valid_mask.sum() > 10:
                corr = np.corrcoef(v1[valid_mask], v2[valid_mask])[0, 1]
                if np.isnan(corr):
                    corr = 0
            else:
                corr = 0
            corr_matrix[i, j] = corr
            corr_matrix[j, i] = corr

    return corr_matrix, formulas_list

def compute_radius_of_gyration(embedded_points):
    """计算旋转半径（RoG）"""
    center = np.mean(embedded_points, axis=0)
    distances = np.sqrt(np.sum((embedded_points - center) ** 2, axis=1))
    rog = np.sqrt(np.mean(distances ** 2))
    return rog

def main():
    """主函数"""
    print("=== MDS因子多样性监控 ===")

    # 加载数据
    hub = DataHub()
    data = hub.get_ohlcv('RB', '1h')
    print(f"数据形状: {data.shape}")

    # 获取数据库中的因子
    with get_session() as session:
        stmt = select(Candidate).where(Candidate.symbol == 'RB')
        results = session.execute(stmt).scalars().all()

    print(f"总因子数: {len(results)}")

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
    print(f"唯一公式数: {len(formulas)}")

    # 计算相关矩阵
    print(f"\n计算因子值相关矩阵...")
    corr_matrix, formulas_list = compute_factor_correlation_matrix(formulas, data)

    # 构建不相似矩阵（1 - |corr|）
    dissimilarity_matrix = 1 - np.abs(corr_matrix)

    # MDS降维到2D
    print(f"\n执行MDS降维...")
    mds = MDS(n_components=2, dissimilarity='precomputed', random_state=42, n_init=3)
    embedded_points = mds.fit_transform(dissimilarity_matrix)

    # 计算旋转半径
    rog = compute_radius_of_gyration(embedded_points)
    print(f"旋转半径（RoG）: {rog:.4f}")

    # 计算平均相关系数
    avg_corr = np.mean(np.abs(corr_matrix[np.triu_indices_from(corr_matrix, k=1)]))
    print(f"平均绝对相关系数: {avg_corr:.4f}")

    # 可视化
    plt.figure(figsize=(10, 8))
    plt.scatter(embedded_points[:, 0], embedded_points[:, 1], alpha=0.6, s=50)
    plt.title(f'因子多样性MDS可视化 (RoG={rog:.4f}, Avg|Corr|={avg_corr:.4f})')
    plt.xlabel('Dimension 1')
    plt.ylabel('Dimension 2')
    plt.grid(True, alpha=0.3)

    # 保存图像
    output_path = 'factor_diversity_mds.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n可视化结果已保存到: {output_path}")

    # 分析分散模式
    center = np.mean(embedded_points, axis=0)
    distances = np.sqrt(np.sum((embedded_points - center) ** 2, axis=1))
    print(f"\n分散度统计:")
    print(f"  平均距离: {np.mean(distances):.4f}")
    print(f"  标准差: {np.std(distances):.4f}")
    print(f"  最大距离: {np.max(distances):.4f}")
    print(f"  最小距离: {np.min(distances):.4f}")

    # 判断是否呈现"圆形分散"模式
    if np.std(distances) / np.mean(distances) < 0.5:
        print(f"\n✓ 因子呈现良好的圆形分散模式（多样性高）")
    else:
        print(f"\n✗ 因子聚集度较高（多样性不足）")

if __name__ == '__main__':
    main()
