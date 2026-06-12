"""测试point_mutation是否会产生无效window参数"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

import random
from quant_engine.ops.gp_individual import GPIndividual, GPNode
from quant_engine.ops.gp_operators import point_mutation

print("=== 测试point_mutation对window参数的影响 ===")

# 创建一个包含window参数的个体
node = GPNode(
    node_type='func',
    name='ts_mean',
    children=[
        GPNode(node_type='var', name='close'),
        GPNode(node_type='const', name='const', value=20),
    ]
)
ind = GPIndividual(root=node, id="test", generation=0)

print(f"初始window值: {ind.root.children[1].value}")

# 多次变异
for i in range(50):
    ind = point_mutation(ind, mutation_rate=1.0)  # 强制变异
    window_value = ind.root.children[1].value
    if i % 10 == 0:
        print(f"变异{i}次后: window={window_value}")

print(f"\n最终window值: {window_value}")

# 检查是否在有效范围内
if 1 <= window_value <= 100:
    print("✅ window值在有效范围内")
else:
    print(f"❌ window值无效: {window_value}")

print("\n=== 测试完成 ===")
