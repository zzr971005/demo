"""检查evolution_center是否使用了最新的验证逻辑"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from quant_engine.ops.gp_fitness import FitnessEvaluator
import inspect

print("=== 检查evolution_center是否使用了最新的验证逻辑 ===")

evaluator = FitnessEvaluator()

# 检查_validate_parameter_types方法是否存在
if hasattr(evaluator, '_validate_parameter_types'):
    print("✅ _validate_parameter_types 方法存在")

    # 检查方法源码是否包含浮点数检查
    source = inspect.getsource(evaluator._validate_parameter_types)
    if 'is_integer()' in source:
        print("✅ 包含浮点数检查逻辑")
    else:
        print("❌ 缺少浮点数检查逻辑")

    if 'param_type == int' in source:
        print("✅ 包含int类型检查")
    else:
        print("❌ 缺少int类型检查")
else:
    print("❌ _validate_parameter_types 方法不存在")

# 检查evaluate方法是否调用了_validate_parameter_types
evaluate_source = inspect.getsource(evaluator.evaluate)
if '_validate_parameter_types' in evaluate_source:
    print("✅ evaluate方法调用了_validate_parameter_types")
else:
    print("❌ evaluate方法未调用_validate_parameter_types")

print("\n=== 检查完成 ===")
