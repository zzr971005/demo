"""测试修复后的变异逻辑"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from quant_engine.ops.gp_individual import create_individual_from_expr
from quant_engine.ops.gp_operators import point_mutation
from quant_engine.ops.gp_fitness import FitnessEvaluator, FitnessConfig

print("=== 测试修复后的变异逻辑 ===")

# 测试包含整数参数的公式
test_formulas = [
    "ts_mean(close, 20)",
    "ts_max(open, 30)",
]

config = FitnessConfig()
evaluator = FitnessEvaluator(config)

for formula in test_formulas:
    print(f"\n原始公式: {formula}")
    try:
        individual = create_individual_from_expr(formula, generation=0)
        
        # 执行多次变异
        for i in range(5):
            mutated = point_mutation(individual, mutation_rate=1.0)
            mutated_expr = mutated.to_expression()
            print(f"  变异{i+1}: {mutated_expr}")
            
            # 验证参数类型
            is_valid = evaluator._validate_parameter_types(mutated)
            print(f"  参数验证: {is_valid}")
            
            if not is_valid:
                print(f"  *** 警告: 变异后参数验证失败 ***")
    except Exception as e:
        print(f"异常: {e}")

print("\n=== 完成 ===")
