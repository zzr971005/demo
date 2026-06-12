"""清理数据库并准备重新开始进化"""
from app.db import get_session, engine
from app.models import Candidate, EvolutionTask, Base
from sqlalchemy import select, delete

print("=== 清理数据库 ===")

with get_session() as session:
    # 删除所有候选者
    result = session.execute(delete(Candidate))
    print(f"删除候选者: {result.rowcount} 条")

    # 删除所有进化任务
    result = session.execute(delete(EvolutionTask))
    print(f"删除进化任务: {result.rowcount} 条")

print("\n=== 数据库已清理 ===")
print("现在可以重新启动进化任务，新的保存逻辑会生效")
print("\n修复内容：")
print("1. 使用UUID生成唯一ID，避免ID冲突")
print("2. 始终创建新记录，不更新已有记录")
print("3. 每代保存前50个最佳个体（之前只保存10个）")
