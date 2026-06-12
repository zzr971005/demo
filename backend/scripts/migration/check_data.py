"""
检查数据库中的数据情况
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def check_data():
    db_url = os.getenv('DATABASE_URL', 'postgresql://quant_user:quant_pass@localhost:5432/quant_db')
    db_url = db_url.replace('+psycopg2', '').replace('+pg8000', '')
    if not db_url.startswith('postgresql://'):
        db_url = 'postgresql+psycopg2' + db_url[db_url.find(':'):]
    else:
        db_url = 'postgresql+psycopg2' + db_url[len('postgresql'):]
    
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        # 检查表中有多少数据
        count_result = conn.execute(text('SELECT COUNT(*) FROM candidates'))
        total_count = count_result.scalar()
        print(f'candidates表总记录数: {total_count}')
        
        # 检查运行中的记录
        running_result = conn.execute(text("SELECT COUNT(*) FROM candidates WHERE status = 'RUNNING'"))
        running_count = running_result.scalar()
        print(f'运行中的记录数: {running_count}')
        
        # 查看一些示例数据
        if total_count > 0:
            result = conn.execute(text('''
                SELECT symbol, id, total_return, total_trades, avg_trade_return, sharpe_train
                FROM candidates 
                ORDER BY created_at DESC 
                LIMIT 5
            '''))
            print('\n最近5条记录:')
            for row in result:
                print(f'符号: {row[0]}, ID: {row[1]}, 总收益率: {row[2]}, 交易次数: {row[3]}, 平均交易收益率: {row[4]}, 夏普: {row[5]}')
        
        # 检查异常大的total_return值
        abnormal_result = conn.execute(text('''
            SELECT symbol, id, total_return, total_trades
            FROM candidates 
            WHERE ABS(total_return) > 1000
            ORDER BY ABS(total_return) DESC
            LIMIT 5
        '''))
        print('\n异常大的收益率记录:')
        for row in abnormal_result:
            print(f'符号: {row[0]}, ID: {row[1]}, 总收益率: {row[2]}, 交易次数: {row[3]}')

if __name__ == '__main__':
    check_data()
