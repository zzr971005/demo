"""
数据库迁移脚本 - 新增模拟交易相关表
确保向后兼容，不修改现有表
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import get_settings
from app.models import Base


async def migrate_database():
    """执行数据库迁移"""
    settings = get_settings()
    
    print(f"连接数据库: {settings.database_url}")
    engine = create_async_engine(settings.database_url, echo=True)
    
    async with engine.begin() as conn:
        # 创建所有新表（checkfirst=True确保不重复创建）
        print("开始创建新表...")
        await conn.run_sync(Base.metadata.create_all)
        print("新表创建完成")
    
    await engine.dispose()
    print("数据库迁移完成")


if __name__ == "__main__":
    asyncio.run(migrate_database())
