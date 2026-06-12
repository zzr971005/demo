"""
数据库备份脚本
"""

import asyncio
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings


def backup_database():
    """备份数据库"""
    settings = get_settings()
    
    # 解析数据库连接信息
    db_url = settings.database_url
    # 格式: postgresql+asyncpg://user:password@host:port/database
    parts = db_url.replace("postgresql+asyncpg://", "").split("@")
    user_pass = parts[0].split(":")
    host_db = parts[1].split("/")
    
    user = user_pass[0]
    password = user_pass[1]
    host_port = host_db[0].split(":")
    host = host_port[0]
    port = host_port[1] if len(host_port) > 1 else "5432"
    database = host_db[1]
    
    # 创建备份目录
    backup_dir = Path(__file__).parent.parent.parent / "backups" / "database"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成备份文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"quant_db_backup_{timestamp}.sql"
    
    # 执行pg_dump
    env = {"PGPASSWORD": password}
    cmd = [
        "pg_dump",
        f"-h{host}",
        f"-p{port}",
        f"-U{user}",
        f"-d{database}",
        f"-f{backup_file}",
        "--no-owner",
        "--no-acl"
    ]
    
    print(f"开始备份数据库到: {backup_file}")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"数据库备份成功: {backup_file}")
        # 只保留最近10个备份
        backups = sorted(backup_dir.glob("quant_db_backup_*.sql"), reverse=True)
        for old_backup in backups[10:]:
            old_backup.unlink()
            print(f"删除旧备份: {old_backup}")
    else:
        print(f"数据库备份失败: {result.stderr}")
        sys.exit(1)


if __name__ == "__main__":
    backup_database()
