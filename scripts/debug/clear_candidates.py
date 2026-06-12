import psycopg2
import os

# 从环境变量读取数据库连接信息
db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/quant_db')

# 解析连接字符串
# 格式: postgresql://user:password@host:port/database
parts = db_url.replace('postgresql://', '').split('/')
conn_parts = parts[0].split('@')
user_pass = conn_parts[0].split(':')
host_port = conn_parts[1].split(':')

user = user_pass[0]
password = user_pass[1]
host = host_port[0]
port = host_port[1] if len(host_port) > 1 else '5432'
database = parts[1]

# 连接数据库
conn = psycopg2.connect(
    host=host,
    port=port,
    database=database,
    user=user,
    password=password
)

cursor = conn.cursor()

# 删除所有候选因子
cursor.execute("DELETE FROM candidates")
conn.commit()
deleted_candidates = cursor.rowcount
print(f'已删除 {deleted_candidates} 条候选因子记录')

# 删除所有进化任务
cursor.execute("DELETE FROM evolution_tasks")
conn.commit()
deleted_tasks = cursor.rowcount
print(f'已删除 {deleted_tasks} 条进化任务记录')

# 删除所有代统计
cursor.execute("DELETE FROM generation_stats")
conn.commit()
deleted_stats = cursor.rowcount
print(f'已删除 {deleted_stats} 条代统计记录')

cursor.close()
conn.close()
