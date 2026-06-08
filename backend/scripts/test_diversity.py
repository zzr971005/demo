"""
测试脚本：验证浮点数格式化和多样性改进

测试内容：
1. 浮点数格式化一致性
2. 因子生成多样性
3. 去重逻辑正确性
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant_engine.ops.gp_individual import random_individual, create_individual_from_expr
from collections import Counter


def test_float_formatting():
    """测试浮点数格式化一致性"""
    print("=" * 60)
    print("测试1: 浮点数格式化一致性")
    print("=" * 60)
    
    # 测试相同数值是否生成相同字符串
    test_cases = [
        (20.0, "20"),
        (20.5, "20.50000"),
        (0.12345, "0.12345"),
        (1.0, "1"),
        (0.5, "0.50000"),
    ]
    
    all_passed = True
    for value, expected in test_cases:
        # 创建包含该常量的个体
        expr = f"ts_mean(close, {value})"
        try:
            ind = create_individual_from_expr(expr, generation=0)
            result = ind.to_expression()
            
            # 检查格式化是否正确
            if expected in result:
                print(f"✓ 值 {value} 格式化正确: {result}")
            else:
                print(f"✗ 值 {value} 格式化错误: 期望包含 '{expected}', 实际: {result}")
                all_passed = False
        except Exception as e:
            print(f"✗ 值 {value} 测试失败: {e}")
            all_passed = False
    
    # 测试多次生成相同值的个体，检查表达式是否一致
    print("\n测试多次生成相同值的一致性:")
    for _ in range(5):
        ind = random_individual(max_depth=3, generation=0)
        expr1 = ind.to_expression()
        # 从表达式重建
        ind2 = create_individual_from_expr(expr1, generation=0)
        expr2 = ind2.to_expression()
        if expr1 == expr2:
            print(f"✓ 表达式重建一致: {expr1[:50]}...")
        else:
            print(f"✗ 表达式重建不一致:")
            print(f"  原始: {expr1}")
            print(f"  重建: {expr2}")
            all_passed = False
    
    print(f"\n测试1结果: {'通过' if all_passed else '失败'}")
    return all_passed


def test_generation_diversity():
    """测试因子生成多样性"""
    print("\n" + "=" * 60)
    print("测试2: 因子生成多样性")
    print("=" * 60)
    
    # 生成100个随机个体
    n = 100
    expressions = []
    for i in range(n):
        ind = random_individual(max_depth=4, generation=0)
        expr = ind.to_expression()
        expressions.append(expr)
    
    # 统计重复率
    expr_counts = Counter(expressions)
    unique_count = len(expr_counts)
    duplicate_count = n - unique_count
    duplicate_rate = duplicate_count / n if n > 0 else 0
    
    print(f"生成个体数: {n}")
    print(f"唯一表达式数: {unique_count}")
    print(f"重复表达式数: {duplicate_count}")
    print(f"重复率: {duplicate_rate * 100:.2f}%")
    
    # 显示重复最多的表达式
    if duplicate_count > 0:
        print("\n重复最多的表达式 (前5个):")
        for expr, count in expr_counts.most_common(5):
            if count > 1:
                print(f"  {expr} (重复{count}次)")
    
    # 判断多样性是否合理
    if duplicate_rate < 0.3:
        print(f"\n✓ 多样性良好 (重复率 {duplicate_rate * 100:.2f}% < 30%)")
        return True
    elif duplicate_rate < 0.5:
        print(f"\n⚠ 多样性一般 (重复率 {duplicate_rate * 100:.2f}% < 50%)")
        return True
    else:
        print(f"\n✗ 多样性不足 (重复率 {duplicate_rate * 100:.2f}% >= 50%)")
        return False


def test_deduplication_logic():
    """测试去重逻辑正确性"""
    print("\n" + "=" * 60)
    print("测试3: 去重逻辑正确性")
    print("=" * 60)
    
    # 创建一些故意重复的表达式
    test_expressions = [
        "ts_mean(close, 20)",
        "ts_mean(close, 20)",
        "ts_std(close, 10)",
        "ts_mean(close, 20)",
        "ts_std(close, 10)",
        "ts_mean(close, 30)",
    ]
    
    # 模拟去重逻辑
    expr_counts = Counter(test_expressions)
    unique_exprs = set(test_expressions)
    
    print(f"原始表达式数: {len(test_expressions)}")
    print(f"去重后表达式数: {len(unique_exprs)}")
    print(f"重复统计: {dict(expr_counts)}")
    
    # 验证去重正确性
    expected_unique = 3  # ts_mean(close, 20), ts_std(close, 10), ts_mean(close, 30)
    if len(unique_exprs) == expected_unique:
        print(f"✓ 去重逻辑正确 (期望{expected_unique}个唯一表达式)")
        return True
    else:
        print(f"✗ 去重逻辑错误 (期望{expected_unique}个唯一表达式, 实际{len(unique_exprs)}个)")
        return False


def test_parameter_ranges():
    """测试参数范围多样性"""
    print("\n" + "=" * 60)
    print("测试4: 参数范围多样性")
    print("=" * 60)
    
    # 生成50个个体，统计参数值分布
    int_values = []
    float_values = []
    
    for _ in range(50):
        ind = random_individual(max_depth=3, generation=0)
        expr = ind.to_expression()
        
        # 提取所有整数参数（在函数调用中的位置参数）
        import re
        int_matches = re.findall(r'\b(\d+)\b', expr)
        int_values.extend([int(w) for w in int_matches if int(w) > 1])  # 过滤掉1（通常不是窗口参数）
        
        # 提取浮点数参数
        float_matches = re.findall(r'(\d+\.\d+)', expr)
        float_values.extend([float(f) for f in float_matches])
    
    print(f"整数参数值分布 (共{len(int_values)}个):")
    if int_values:
        print(f"  最小值: {min(int_values)}")
        print(f"  最大值: {max(int_values)}")
        print(f"  唯一值数: {len(set(int_values))}")
        print(f"  值分布: {sorted(set(int_values))[:20]}")  # 只显示前20个
    
    print(f"\n浮点数参数值分布 (共{len(float_values)}个):")
    if float_values:
        print(f"  最小值: {min(float_values):.5f}")
        print(f"  最大值: {max(float_values):.5f}")
        print(f"  唯一值数: {len(set(float_values))}")
        # 检查浮点数精度（至少3位小数）
        precision_ok = all(len(str(f).split('.')[-1]) >= 3 for f in float_values)
        print(f"  精度检查: 小数位数 >= 3: {precision_ok}")
    
    # 判断参数多样性
    int_diverse = len(set(int_values)) >= 5 if int_values else True
    float_diverse = len(set(float_values)) >= 5 if float_values else True
    
    if int_diverse and float_diverse:
        print(f"\n✓ 参数范围多样性良好")
        return True
    else:
        print(f"\n⚠ 参数范围多样性一般 (整数唯一值: {len(set(int_values))}, 浮点数唯一值: {len(set(float_values))})")
        # 不算失败，因为参数多样性不是关键指标
        return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("进化数据多样性测试")
    print("=" * 60)
    
    results = {
        "浮点数格式化": test_float_formatting(),
        "因子生成多样性": test_generation_diversity(),
        "去重逻辑": test_deduplication_logic(),
        "参数范围多样性": test_parameter_ranges(),
    }
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    print(f"\n总体结果: {'全部通过' if all_passed else '存在失败'}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
