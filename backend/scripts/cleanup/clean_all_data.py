"""
清空所有历史因子数据和进化任务记录，用于系统验证从头开始。
警告：此操作不可逆！
"""
import logging
import os
import shutil

from sqlalchemy import text, select
from app.db import get_session
from app.models import (
    Candidate,
    EvolutionTask,
    GenerationStats,
    SymbolSwitch,
    SymbolMode,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("__main__")


def clean_all_data():
    with get_session() as session:
        # 1. 清空 candidates 表
        try:
            candidate_count = session.execute(select(Candidate)).scalars().all()
            n = len(candidate_count)
            for c in candidate_count:
                session.delete(c)
            session.commit()
            logger.info(f"已清空 candidates 表: {n} 条记录")
        except Exception as e:
            logger.error(f"清空 candidates 失败: {e}")

        # 2. 清空 evolution_tasks 表
        try:
            tasks = session.execute(select(EvolutionTask)).scalars().all()
            n = len(tasks)
            for t in tasks:
                session.delete(t)
            session.commit()
            logger.info(f"已清空 evolution_tasks 表: {n} 条记录")
        except Exception as e:
            logger.error(f"清空 evolution_tasks 失败: {e}")

        # 3. 清空 generation_stats 表
        try:
            stats = session.execute(select(GenerationStats)).scalars().all()
            n = len(stats)
            for s in stats:
                session.delete(s)
            session.commit()
            logger.info(f"已清空 generation_stats 表: {n} 条记录")
        except Exception as e:
            logger.error(f"清空 generation_stats 失败: {e}")

        # 4. 重置所有 symbol_switches 为 OFF
        try:
            switches = session.execute(select(SymbolSwitch)).scalars().all()
            n = len(switches)
            for s in switches:
                s.mode = SymbolMode.OFF
                s.current_candidate_id = None
            session.commit()
            logger.info(f"已重置 symbol_switches: {n} 条记录 -> OFF")
        except Exception as e:
            logger.error(f"重置 symbol_switches 失败: {e}")

    # 5. 删除输出目录中的因子文件
    output_dirs = [
        "./output/factors",
        "./output/evolution",
        "./output",
    ]
    for dir_path in output_dirs:
        if os.path.exists(dir_path):
            try:
                files = os.listdir(dir_path)
                for f in files:
                    fpath = os.path.join(dir_path, f)
                    if os.path.isfile(fpath):
                        os.remove(fpath)
                logger.info(f"已清理输出目录: {dir_path} ({len(files)} 个文件)")
            except Exception as e:
                logger.warning(f"清理 {dir_path} 失败: {e}")

    logger.info("=" * 60)
    logger.info(" 数据清理完成")
    logger.info(" 请重启进化引擎和前端服务")
    logger.info("=" * 60)


if __name__ == "__main__":
    logger.warning("=" * 60)
    logger.warning(" 警告: 即将清空所有因子数据、进化任务和状态!")
    logger.warning(" 此操作不可逆!")
    logger.warning("=" * 60)
    clean_all_data()
