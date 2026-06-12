"""数据库迁移脚本：添加 generation_stats 表

用途：存储每代进化的详细统计数据，用于图表展示
与 candidates 表分离：
- candidates 表：存储最佳因子（竞争模式，只保留100个）
- generation_stats 表：存储每代统计（完整历史，用于图表）
"""
import os
import sys
from pathlib import Path

# 添加backend到路径
backend_path = str(Path(__file__).parent)
sys.path.insert(0, backend_path)

# 设置环境变量
os.environ.setdefault("APP_ENV", "development")

from sqlalchemy import create_engine, text, Column, Integer, String, Float, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime
from typing import Optional

# 直接定义模型，避免导入问题
class Base(DeclarativeBase):
    pass

class GenerationStats(Base):
    """进化世代统计指标表"""
    __tablename__ = "generation_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(96), index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    generation: Mapped[int] = mapped_column(Integer, index=True)

    avg_sharpe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_sharpe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_sharpe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    top_10_avg_sharpe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    avg_fitness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    best_fitness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    diversity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unique_expressions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    pbo: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dsr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wfe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    population_size: Mapped[int] = mapped_column(Integer, default=0)
    elite_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint(
            "task_id", "generation",
            name="uq_generation_stats_task_gen"
        ),
    )

# 读取数据库URL
def get_db_url():
    """从.env文件读取数据库URL并转换为同步驱动"""
    env_path = Path(__file__).parent / ".env"
    url = None
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("DATABASE_URL="):
                    url = line.strip().split("=", 1)[1].strip().strip('"')
                    break

    if not url:
        url = "postgresql+asyncpg://postgres:postgres@localhost:5432/quant_evolution"

    # 将异步驱动转换为同步驱动
    if "asyncpg" in url:
        url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    elif "pg8000" in url:
        url = url.replace("postgresql+pg8000://", "postgresql://")

    return url

def migrate():
    """执行迁移"""
    print("=== 开始迁移：添加 generation_stats 表 ===")

    # 获取数据库URL
    db_url = get_db_url()
    print(f"数据库URL: {db_url}")

    # 创建引擎
    engine = create_engine(db_url)

    try:
        # 检查表是否已存在
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'generation_stats')"
            ))
            exists = result.scalar()

            if exists:
                print("表 generation_stats 已存在，跳过创建")
            else:
                print("创建表 generation_stats...")
                # 创建表
                GenerationStats.__table__.create(engine)
                print("✓ 表创建成功")

            # 创建索引
            print("检查索引...")
            index_result = conn.execute(text(
                """
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'generation_stats'
                AND indexname LIKE 'ix_generation_stats%'
                """
            ))
            existing_indexes = [row[0] for row in index_result]

            # task_id 索引
            if 'ix_generation_stats_task_id' not in existing_indexes:
                conn.execute(text(
                    "CREATE INDEX ix_generation_stats_task_id ON generation_stats (task_id)"
                ))
                print("✓ 创建索引 ix_generation_stats_task_id")

            # symbol 索引
            if 'ix_generation_stats_symbol' not in existing_indexes:
                conn.execute(text(
                    "CREATE INDEX ix_generation_stats_symbol ON generation_stats (symbol)"
                ))
                print("✓ 创建索引 ix_generation_stats_symbol")

            # generation 索引
            if 'ix_generation_stats_generation' not in existing_indexes:
                conn.execute(text(
                    "CREATE INDEX ix_generation_stats_generation ON generation_stats (generation)"
                ))
                print("✓ 创建索引 ix_generation_stats_generation")

            conn.commit()

        print("\n=== 迁移完成 ===")
        print("新表结构：")
        print("- id: 主键")
        print("- task_id: 任务ID（索引）")
        print("- symbol: 品种代码（索引）")
        print("- generation: 世代号（索引）")
        print("- avg_sharpe/max_sharpe/min_sharpe/top_10_avg_sharpe: 夏普统计")
        print("- avg_fitness/best_fitness: 适应度统计")
        print("- diversity_score/unique_expressions: 多样性指标")
        print("- pbo/dsr/wfe: 过拟合检验指标")
        print("- population_size/elite_count: 种群信息")
        print("- created_at: 创建时间")

        return True

    except Exception as e:
        print(f"\n✗ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
