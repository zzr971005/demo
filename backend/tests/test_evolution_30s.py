"""自动化测试脚本：激活RB品种，运行30秒进化，然后检查结果"""
import sys
sys.path.insert(0, '.')

import time
import subprocess
from app.db import get_session
from app.models import SymbolSwitch, SymbolMode
from sqlalchemy import select

print("=== 开始自动化进化测试 ===")

# 1. 清理数据
print("\n1. 清理旧数据...")
from app.models import Candidate, EvolutionTask, GenerationStats
with get_session() as session:
    session.query(Candidate).filter(Candidate.symbol == 'RB').delete()
    session.query(EvolutionTask).filter(EvolutionTask.symbol == 'RB').delete()
    session.query(GenerationStats).delete()
    session.commit()
    print("  数据已清理")

# 2. 激活RB品种
print("\n2. 激活RB品种...")
with get_session() as session:
    stmt = select(SymbolSwitch).where(SymbolSwitch.symbol == 'RB')
    result = session.execute(stmt).scalar_one_or_none()
    if result:
        result.mode = SymbolMode.PAPER
        session.commit()
        print(f"  RB已激活: {result.mode}")
    else:
        print("  未找到RB品种记录")

# 3. 启动持续进化引擎（后台运行）
print("\n3. 启动持续进化引擎...")
process = subprocess.Popen(
    [sys.executable, "scripts/run_continuous_evolution.py"],
    cwd=".",
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
print(f"  进程已启动，PID: {process.pid}")

# 4. 等待30秒
print("\n4. 等待30秒让进化运行...")
time.sleep(30)

# 5. 停止进化引擎
print("\n5. 停止进化引擎...")
process.terminate()
try:
    process.wait(timeout=10)
    print("  进程已停止")
except subprocess.TimeoutExpired:
    process.kill()
    print("  进程已强制停止")

# 6. 停用RB品种
print("\n6. 停用RB品种...")
with get_session() as session:
    stmt = select(SymbolSwitch).where(SymbolSwitch.symbol == 'RB')
    result = session.execute(stmt).scalar_one_or_none()
    if result:
        result.mode = SymbolMode.OFF
        session.commit()
        print(f"  RB已停用: {result.mode}")

# 7. 检查结果
print("\n7. 检查结果...")
with get_session() as session:
    stmt = select(Candidate).where(Candidate.symbol == 'RB')
    results = session.execute(stmt).scalars().all()
    print(f"  总因子数: {len(results)}")

    if len(results) > 0:
        # 按性能指标分组
        from collections import defaultdict
        groups = defaultdict(list)
        for c in results:
            key = (round(c.sharpe_train, 4), round(c.calmar, 4), c.total_trades)
            groups[key].append(c)

        print(f"  重复组数: {len([g for g in groups.values() if len(g) > 1])}")

        # 找出最大的重复组
        if groups:
            max_group = max(groups.values(), key=len)
            print(f"  最大重复组: {len(max_group)} 个因子")
            print(f"  性能指标: Sharpe={max_group[0].sharpe_train:.4f}, Calmar={max_group[0].calmar:.4f}, TotalTrades={max_group[0].total_trades}")

            # 检查公式是否真的不同
            formulas = [c.formula for c in max_group]
            unique_formulas = set(formulas)
            print(f"  唯一公式数: {len(unique_formulas)}")

            if len(unique_formulas) < len(formulas):
                print(f"  有 {len(formulas) - len(unique_formulas)} 个完全重复的公式")
            else:
                print(f"  所有公式都不同，但产生相同性能指标")
    else:
        print("  未生成任何因子")

print("\n=== 测试完成 ===")
