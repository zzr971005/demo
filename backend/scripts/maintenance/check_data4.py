"""验证问题假设"""
from app.db import get_session
from app.models import Candidate, EvolutionTask
from sqlalchemy import select, func, desc

with get_session() as session:
    # 检查gen1_0003这个ID的所有历史记录
    print("=== 检查gen1_0003的详细信息 ===")
    c = session.query(Candidate).filter(Candidate.id == "gen1_0003").first()
    if c:
        print(f"ID: {c.id}")
        print(f"generation字段: {c.generation}")
        print(f"夏普: {c.sharpe_train}")
        print(f"创建时间: {c.created_at}")
        print(f"更新时间: {c.updated_at}")
        print(f"公式: {c.formula[:100]}...")
    else:
        print("未找到gen1_0003")

    # 检查gen11_0002
    print("\n=== 检查gen11_0002的详细信息 ===")
    c = session.query(Candidate).filter(Candidate.id == "gen11_0002").first()
    if c:
        print(f"ID: {c.id}")
        print(f"generation字段: {c.generation}")
        print(f"夏普: {c.sharpe_train}")
        print(f"创建时间: {c.created_at}")
        print(f"更新时间: {c.updated_at}")
        print(f"公式: {c.formula[:100]}...")
    else:
        print("未找到gen11_0002")

    # 统计各世代的实际个体数量（按ID前缀）
    print("\n=== 统计各世代的实际个体数量 ===")
    all_candidates = session.query(Candidate).all()
    gen_count = {}
    for c in all_candidates:
        # 从ID提取世代号
        if c.id.startswith("gen"):
            parts = c.id.split("_")
            if len(parts) >= 2:
                try:
                    gen = int(parts[0][3:])  # 提取gen后面的数字
                    gen_count[gen] = gen_count.get(gen, 0) + 1
                except:
                    pass

    # 按世代排序显示
    for gen in sorted(gen_count.keys())[:20]:
        print(f"  世代 {gen}: {gen_count[gen]} 个个体")

    print(f"\n总共 {len(gen_count)} 个不同的世代")
    print(f"最新世代: {max(gen_count.keys())}")
