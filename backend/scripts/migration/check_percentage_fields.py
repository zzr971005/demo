"""
检查数据库中所有涉及百分比的数值存储格式
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def check_percentage_fields():
    db_url = os.getenv('DATABASE_URL', 'postgresql://quant_user:quant_pass@localhost:5432/quant_db')
    db_url = db_url.replace('+psycopg2', '').replace('+pg8000', '')
    if not db_url.startswith('postgresql://'):
        db_url = 'postgresql+psycopg2' + db_url[db_url.find(':'):]
    else:
        db_url = 'postgresql+psycopg2' + db_url[len('postgresql'):]
    
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        print("=== 检查百分比相关字段的存储格式 ===\n")
        
        # 1. 检查所有相关字段的统计信息
        fields_to_check = [
            'total_return', 'avg_trade_return', 'max_drawdown', 'win_rate',
            'sharpe_train', 'sharpe_val', 'sharpe_test', 'calmar'
        ]
        
        for field in fields_to_check:
            result = conn.execute(text(f'''
                SELECT 
                    COUNT(*) as total_count,
                    COUNT({field}) as non_null_count,
                    MIN({field}) as min_value,
                    MAX({field}) as max_value,
                    AVG({field}) as avg_value
                FROM candidates 
                WHERE {field} IS NOT NULL
            '''))
            
            stats = result.fetchone()
            print(f"=== {field} 字段统计 ===")
            print(f"总记录数: {stats[0]}")
            print(f"非NULL记录数: {stats[1]}")
            min_val = f"{stats[2]:.6f}" if stats[2] is not None else "NULL"
            max_val = f"{stats[3]:.6f}" if stats[3] is not None else "NULL"
            avg_val = f"{stats[4]:.6f}" if stats[4] is not None else "NULL"
            print(f"最小值: {min_val}")
            print(f"最大值: {max_val}")
            print(f"平均值: {avg_val}")
            
            # 判断可能的存储格式
            if stats[1] > 0:
                max_val = stats[3]
                min_val = stats[2]
                
                if field in ['total_return', 'avg_trade_return']:
                    if max_val > 100:
                        print("🔍 分析: 可能是百分比格式 (值 > 100)")
                    elif max_val > 1:
                        print("🔍 分析: 可能是百分比格式 (值 > 1)")
                    else:
                        print("🔍 分析: 可能是小数格式 (值 <= 1)")
                elif field in ['max_drawdown']:
                    if max_val > 1:
                        print("🔍 分析: 可能是百分比格式")
                    else:
                        print("🔍 分析: 可能是小数格式")
                elif field in ['win_rate']:
                    if max_val <= 1:
                        print("🔍 分析: 可能是小数格式 (0-1范围)")
                    else:
                        print("🔍 分析: 可能是百分比格式")
                elif field in ['sharpe_train', 'sharpe_val', 'sharpe_test']:
                    print("🔍 分析: 夏普比率，通常为小数格式")
                elif field in ['calmar']:
                    print("🔍 分析: 卡玛比率，通常为小数格式")
            
            print()
        
        # 2. 检查具体示例数据
        print("=== 具体数据示例 ===")
        result = conn.execute(text('''
            SELECT 
                symbol, id,
                total_return, total_trades, avg_trade_return,
                max_drawdown, win_rate,
                sharpe_train, calmar
            FROM candidates 
            WHERE total_return IS NOT NULL 
            ORDER BY created_at DESC 
            LIMIT 3
        '''))
        
        for row in result:
            print(f"\n因子: {row[1][:30]}...")
            print(f"品种: {row[0]}")
            print(f"总收益率: {row[2]:.6f} → 显示为: {row[2]:.1f}%")
            print(f"交易次数: {row[3]}")
            print(f"单次平均收益率: {row[4]:.6f} → 显示为: {row[4]:.3f}%")
            print(f"最大回撤: {row[5]:.6f} → 显示为: {row[5]*100:.1f}%")
            print(f"胜率: {row[6]:.6f} → 显示为: {row[6]*100:.1f}%")
            print(f"夏普比率: {row[7]:.6f}")
            print(f"卡玛比率: {row[8]:.6f}")
            
            # 验证计算关系
            if row[3] and row[3] > 0:
                calculated_avg = row[2] / row[3]
                print(f"验证: {row[2]:.6f} / {row[3]} = {calculated_avg:.6f} (实际: {row[4]:.6f})")
                print(f"匹配: {abs(calculated_avg - row[4]) < 0.000001}")
        
        # 3. 检查回测引擎的原始输出格式
        print("\n=== 检查回测引擎计算逻辑 ===")
        print("从 engine.py 中的计算逻辑:")
        print("- total_return = (equity[-1] - equity[0]) / equity[0]")
        print("- avg_trade_return = total_return / total_trades")
        print("这表明 total_return 是小数格式 (如 0.596 表示 59.6%)")
        print("但数据库中的值显示为百分比格式，说明在某个环节有转换")

if __name__ == '__main__':
    check_percentage_fields()
