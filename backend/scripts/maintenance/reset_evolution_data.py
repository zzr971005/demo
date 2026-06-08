"""
彻底清空所有进化相关数据

用途：当发现进化引擎使用模拟数据运行，所有历史进化结果不可信时，
      一键清除所有进化产物，从零开始。

清空的表：
- candidates          (所有因子候选)
- evolution_tasks     (所有进化任务)
- generation_stats    (所有世代统计)
- baseline_comparison_results (所有基线对比)
- trades              (与候选关联的交易记录)

保留的表：
- symbol_switches     (品种配置)
- risk_events         (风控事件)
- ohlcv_1h / ohlcv_1d (历史行情数据，这是真金白银买来的)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.db import engine

TABLES_TO_TRUNCATE = [
    "candidates",
    "evolution_tasks",
    "generation_stats",
    "baseline_comparison_results",
    "trades",
]


def reset_evolution_data():
    print("=" * 60)
    print("  清空所有进化数据")
    print("=" * 60)
    print("\n即将永久删除以下表的所有数据：")
    for t in TABLES_TO_TRUNCATE:
        print(f"  - {t}")
    print("\n保留表：symbol_switches, ohlcv_1h, ohlcv_1d, risk_events")

    confirm = input("\n确认清空? 输入 'yes' 继续: ")
    if confirm.strip().lower() != "yes":
        print("操作已取消")
        return

    with engine.connect() as conn:
        for table in TABLES_TO_TRUNCATE:
            try:
                result = conn.execute(text(f"DELETE FROM {table}"))
                conn.commit()
                print(f"  [OK] {table:30s} 已清空 ({result.rowcount} 条)")
            except Exception as e:
                print(f"  [ERR] {table:30s} 清空失败: {e}")

    print("\n" + "=" * 60)
    print("  所有进化数据已清空")
    print("=" * 60)
    print("\n下一步：")
    print("  1. 确保已修复 run_continuous_evolution.py 的 DataHub 配置")
    print("  2. 重新启动进化引擎（使用真实数据）")
    print("  3. 前端刷新页面（Ctrl+F5）")


if __name__ == "__main__":
    reset_evolution_data()
