"""重新评估数据库中的种子因子"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from app.models import Candidate
from app.db import get_session
from quant_engine.ops.gp_fitness import FitnessEvaluator, FitnessConfig
from quant_engine.ops.gp_individual import create_individual_from_expr
from quant_engine.data.unified_hub import DataHub
from sqlalchemy import select, desc

print("=== 重新评估数据库中的种子因子 ===")

# 加载真实数据
data_hub = DataHub()
data = data_hub.get_ohlcv(
    symbol="RB",
    start_date="2024-01-01",
    end_date="2024-12-31",
    frequency="1H"
)

# 添加期限结构所需的列
data['near_close'] = data['close']
data['far_close'] = data['close']
data['days_to_expiry'] = 30

print(f"加载数据: {len(data)} 条")

# 创建评估器
config = FitnessConfig()
evaluator = FitnessEvaluator(config)

with get_session() as session:
    # 查询前5个RB因子
    stmt = select(Candidate).where(Candidate.symbol == "RB").order_by(desc(Candidate.sharpe_train)).limit(5)
    candidates = session.execute(stmt).scalars().all()
    
    print(f"\n重新评估前5个因子:")
    for i, c in enumerate(candidates):
        print(f"\n{i+1}. 公式: {c.formula}")
        print(f"   数据库性能: Sharpe={c.sharpe_train:.4f}, Calmar={c.calmar:.4f}, TotalTrades={c.total_trades}")
        
        try:
            # 从表达式创建个体
            individual = create_individual_from_expr(c.formula, generation=0)
            
            # 重新评估
            result = evaluator.evaluate(individual, data, "RB")
            
            if result.valid:
                print(f"   重新评估性能: Sharpe={result.sharpe:.4f}, Calmar={result.calmar:.4f}, TotalTrades={result.total_trades}")
                
                # 对比差异
                sharpe_diff = abs(result.sharpe - c.sharpe_train)
                calmar_diff = abs(result.calmar - c.calmar)
                trades_diff = abs(result.total_trades - c.total_trades)
                
                if sharpe_diff > 0.01 or calmar_diff > 0.1 or trades_diff > 0:
                    print(f"   *** 性能指标不匹配! ***")
                else:
                    print(f"   性能指标匹配")
            else:
                print(f"   重新评估失败: {result.error_message}")
        except Exception as e:
            print(f"   重新评估异常: {e}")

print("\n=== 完成 ===")
