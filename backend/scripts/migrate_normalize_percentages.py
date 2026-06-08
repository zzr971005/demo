"""
数据迁移脚本：将百分比数值格式统一转换为小数格式

运行方式：
    cd backend && python scripts/migrate_normalize_percentages.py

说明：
    - 旧数据格式：百分比数值（如 total_return = 15898.77 表示 15898.77%）
    - 新数据格式：小数格式（如 total_return = 1.589877 表示 158.99%）
    - 转换规则：数值 > 10 的字段视为旧格式，除以 100

涉及的表和字段：
    - candidates: max_drawdown, total_return, win_rate, avg_trade_return, sharpe_train, sharpe_val, calmar
"""

import sys
import os
from pathlib import Path

# 确保 backend 目录在 sys.path
script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

from sqlalchemy import select, update
from app.db import get_session
from app.models import Candidate


def needs_normalization(value: float) -> bool:
    """判断数值是否需要归一化（旧格式特征：数值 > 10）"""
    if value is None:
        return False
    # 百分比格式的特征：数值通常 > 10（如 15898.77）
    # 小数格式的特征：数值通常 < 10（如 1.589877）
    return abs(value) > 10


def migrate_candidates():
    """迁移 candidates 表中的百分比数据"""
    fields_to_migrate = [
        'max_drawdown',
        'total_return',
        'win_rate',
        'avg_trade_return',
        'sharpe_train',
        'sharpe_val',
        'calmar',
    ]

    with get_session() as session:
        # 获取所有候选者
        candidates = session.execute(select(Candidate)).scalars().all()

        migrated_count = 0
        skipped_count = 0

        for candidate in candidates:
            needs_update = False
            updates = {}

            for field in fields_to_migrate:
                value = getattr(candidate, field)
                if value is not None and needs_normalization(value):
                    # 旧格式：除以 100 转换为小数
                    new_value = value / 100
                    updates[field] = new_value
                    needs_update = True
                    print(f"  [{candidate.id[:8]}] {field}: {value:.4f} -> {new_value:.4f}")

            if needs_update:
                # 执行更新
                for field, new_value in updates.items():
                    setattr(candidate, field, new_value)
                migrated_count += 1
            else:
                skipped_count += 1

        return migrated_count, skipped_count


def main():
    print("=" * 60)
    print(" 数据迁移：百分比格式归一化")
    print("=" * 60)
    print()
    print("迁移规则：数值 > 10 的字段视为旧格式，除以 100 转换为小数")
    print()

    try:
        migrated, skipped = migrate_candidates()

        print()
        print("=" * 60)
        print(f" 迁移完成")
        print("=" * 60)
        print(f" 已迁移记录数: {migrated}")
        print(f" 已跳过记录数: {skipped}")
        print()
        print("提示：请验证数据正确性，如有问题请从备份恢复")
        print()

    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
