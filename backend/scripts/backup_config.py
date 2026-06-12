"""
配置文件备份脚本
"""

import shutil
from datetime import datetime
from pathlib import Path


def backup_config():
    """备份配置文件"""
    # 配置文件目录
    config_dir = Path(__file__).parent.parent / "config"
    
    # 备份目录
    backup_dir = Path(__file__).parent.parent.parent / "backups" / "config"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成备份文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_subdir = backup_dir / f"config_backup_{timestamp}"
    backup_subdir.mkdir(exist_ok=True)
    
    # 复制所有配置文件
    config_files = [
        "system.yaml",
        "trading_config.yaml",
        "simulation_config.yaml",
        "live_risk_config.yaml",
        "factor_pool_config.yaml"
    ]
    
    print(f"开始备份配置文件到: {backup_subdir}")
    
    for config_file in config_files:
        src = config_dir / config_file
        if src.exists():
            dst = backup_subdir / config_file
            shutil.copy2(src, dst)
            print(f"备份: {config_file}")
        else:
            print(f"跳过不存在的文件: {config_file}")
    
    print(f"配置文件备份完成: {backup_subdir}")
    
    # 只保留最近10个备份
    backups = sorted(backup_dir.glob("config_backup_*"), reverse=True)
    for old_backup in backups[10:]:
        shutil.rmtree(old_backup)
        print(f"删除旧备份: {old_backup}")


if __name__ == "__main__":
    backup_config()
