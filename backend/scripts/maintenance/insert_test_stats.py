"""插入测试数据到 generation_stats 表"""
import sys
from pathlib import Path
import os

backend_path = str(Path(__file__).parent)
sys.path.insert(0, backend_path)
os.environ.setdefault("APP_ENV", "development")

from sqlalchemy import create_engine, text
from datetime import datetime

def get_db_url():
    """读取数据库URL"""
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
    # 转同步驱动
    if "asyncpg" in url:
        url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    elif "pg8000" in url:
        url = url.replace("postgresql+pg8000://", "postgresql://")
    return url

def insert_test_data():
    """插入测试数据"""
    db_url = get_db_url()
    engine = create_engine(db_url)

    try:
        with engine.connect() as conn:
            # 插入10代测试数据
            for gen in range(10):
                conn.execute(text("""
                    INSERT INTO generation_stats (
                        task_id, symbol, generation,
                        avg_sharpe, max_sharpe, min_sharpe, top_10_avg_sharpe,
                        avg_fitness, best_fitness,
                        diversity_score, unique_expressions,
                        population_size, elite_count,
                        created_at
                    ) VALUES (
                        'TEST_TASK_001', 'RB', :gen,
                        :avg_sharpe, :max_sharpe, :min_sharpe, :top10_avg,
                        :avg_fitness, :best_fitness,
                        :diversity, :unique_expr,
                        100, 10,
                        :created_at
                    )
                    ON CONFLICT (task_id, generation) DO NOTHING
                """), {
                    'gen': gen,
                    'avg_sharpe': 0.5 + gen * 0.1 + (gen % 3) * 0.05,
                    'max_sharpe': 1.0 + gen * 0.15,
                    'min_sharpe': 0.1 + (gen % 2) * 0.05,
                    'top10_avg': 0.8 + gen * 0.12,
                    'avg_fitness': 0.4 + gen * 0.08,
                    'best_fitness': 0.9 + gen * 0.13,
                    'diversity': 0.6 + (gen % 5) * 0.05,
                    'unique_expr': 50 + gen * 2,
                    'created_at': datetime.utcnow()
                })

            conn.commit()
            print("✓ 插入10代测试数据成功")
            print("刷新前端页面，图表应该显示数据了")

    except Exception as e:
        print(f"✗ 插入失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    insert_test_data()
