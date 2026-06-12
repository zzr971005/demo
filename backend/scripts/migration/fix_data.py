"""
修复数据问题：
1. 修复异常大的total_return值（可能是百分比存储错误）
2. 计算并更新avg_trade_return值
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_data():
    db_url = os.getenv('DATABASE_URL', 'postgresql://quant_user:quant_pass@localhost:5432/quant_db')
    db_url = db_url.replace('+psycopg2', '').replace('+pg8000', '')
    if not db_url.startswith('postgresql://'):
        db_url = 'postgresql+psycopg2' + db_url[db_url.find(':'):]
    else:
        db_url = 'postgresql+psycopg2' + db_url[len('postgresql'):]
    
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        # 1. 修复异常大的total_return值（如果值>100，可能是百分比存储错误，需要除以100）
        logger.info("修复异常大的total_return值...")
        
        # 检查有多少异常值
        abnormal_count = conn.execute(text('''
            SELECT COUNT(*) FROM candidates 
            WHERE ABS(total_return) > 100 AND total_return IS NOT NULL
        ''')).scalar()
        logger.info(f"发现 {abnormal_count} 条异常大的total_return记录")
        
        if abnormal_count > 0:
            # 将异常大的值除以100
            conn.execute(text('''
                UPDATE candidates 
                SET total_return = total_return / 100.0
                WHERE ABS(total_return) > 100 AND total_return IS NOT NULL
            '''))
            conn.commit()
            logger.info("已修复异常大的total_return值")
        
        # 2. 计算并更新avg_trade_return值
        logger.info("计算并更新avg_trade_return值...")
        
        # 更新avg_trade_return = total_return / total_trades
        updated_count = conn.execute(text('''
            UPDATE candidates 
            SET avg_trade_return = CASE 
                WHEN total_trades > 0 AND total_trades IS NOT NULL AND total_return IS NOT NULL 
                THEN total_return / total_trades 
                ELSE 0 
            END
            WHERE avg_trade_return IS NULL OR avg_trade_return = 0
        ''')).rowcount
        conn.commit()
        logger.info(f"已更新 {updated_count} 条记录的avg_trade_return值")
        
        # 3. 验证修复结果
        logger.info("验证修复结果...")
        
        # 检查修复后的数据
        result = conn.execute(text('''
            SELECT symbol, id, total_return, total_trades, avg_trade_return, sharpe_train
            FROM candidates 
            ORDER BY created_at DESC 
            LIMIT 5
        '''))
        
        print("\n修复后的数据示例:")
        for row in result:
            print(f'符号: {row[0]}, ID: {row[1][:20]}..., 总收益率: {row[2]:.6f} ({row[2]*100:.2f}%), '
                  f'交易次数: {row[3]}, 平均交易收益率: {row[4]:.6f} ({row[4]*100:.3f}%), 夏普: {row[5]:.3f}')
        
        # 检查是否还有异常值
        remaining_abnormal = conn.execute(text('''
            SELECT COUNT(*) FROM candidates 
            WHERE ABS(total_return) > 10
        ''')).scalar()
        logger.info(f"修复后仍有 {remaining_abnormal} 条total_return > 10的记录")
        
        logger.info("数据修复完成!")

if __name__ == '__main__':
    fix_data()
