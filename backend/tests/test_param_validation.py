"""测试参数验证逻辑"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from quant_engine.ops.gp_individual import create_individual_from_expr
from quant_engine.ops.gp_fitness import FitnessEvaluator, FitnessConfig

print("=== 测试参数验证逻辑 ===")

# 测试包含浮点参数的公式
test_formulas = [
    "atr(high, open, open, -3.6252)",
    "ts_mean(close, 6.5)",
    "ts_max(open, 20)",
    "close - open",
]

config = FitnessConfig()
evaluator = FitnessEvaluator(config)

for formula in test_formulas:
    print(f"\n公式: {formula}")
    try:
        individual = create_individual_from_expr(formula, generation=0)
        is_valid = evaluator._validate_parameter_types(individual)
        print(f"参数验证结果: {is_valid}")
        
        # 打印节点树
        def print_tree(node, depth=0):
            indent = "  " * depth
            if node.node_type == 'const':
                print(f"{indent}const: {node.value} (type: {type(node.value).__name__})")
            elif node.node_type == 'var':
                print(f"{indent}var: {node.name}")
            elif node.node_type == 'func':
                print(f"{indent}func: {node.name}")
                for child in node.children:
                    print_tree(child, depth + 1)
            elif node.node_type == 'binop':
                print(f"{indent}binop: {node.name}")
                for child in node.children:
                    print_tree(child, depth + 1)
        
        print("节点树:")
        print_tree(individual.root)
    except Exception as e:
        print(f"异常: {e}")

print("\n=== 完成 ===")
