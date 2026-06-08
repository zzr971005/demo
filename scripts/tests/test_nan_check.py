"""测试np.all(np.isnan())的行为"""

import numpy as np

print("=== 测试np.all(np.isnan())的行为 ===")

# 测试全NaN数组
arr_nan = np.full(10, np.nan)
print(f"\n全NaN数组: {arr_nan}")
print(f"np.all(np.isnan(arr_nan)): {np.all(np.isnan(arr_nan))}")
print(f"arr_nan.min(): {arr_nan.min()}")
print(f"np.isnan(arr_nan.min()): {np.isnan(arr_nan.min())}")

# 测试包含一个非NaN值的数组
arr_mixed = np.full(10, np.nan)
arr_mixed[0] = 1.0
print(f"\n包含一个非NaN值的数组: {arr_mixed}")
print(f"np.all(np.isnan(arr_mixed)): {np.all(np.isnan(arr_mixed))}")
print(f"arr_mixed.min(): {arr_mixed.min()}")

# 测试空数组
arr_empty = np.array([])
print(f"\n空数组: {arr_empty}")
print(f"np.all(np.isnan(arr_empty)): {np.all(np.isnan(arr_empty))}")

# 测试numpy的bool_类型
result = np.all(np.isnan(arr_nan))
print(f"\n结果类型: {type(result)}")
print(f"结果值: {result}")
print(f"结果 == True: {result == True}")
print(f"结果 is True: {result is True}")

# 测试条件判断
if np.all(np.isnan(arr_nan)):
    print("\n条件判断: 进入全NaN分支")
else:
    print("\n条件判断: 进入非全NaN分支")

# 测试在函数中的行为
def test_nan_check(arr):
    print(f"\n函数内检查:")
    print(f"  arr.min(): {arr.min()}")
    print(f"  np.all(np.isnan(arr)): {np.all(np.isnan(arr))}")
    if np.all(np.isnan(arr)):
        return "全NaN"
    else:
        return "非全NaN"

result = test_nan_check(arr_nan)
print(f"函数返回: {result}")

print("\n=== 测试完成 ===")
