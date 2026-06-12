"""
数据备份管理 — CSV备份与恢复功能

提供：
- 数据库数据自动备份到CSV
- 从CSV恢复数据到数据库
- 备份状态检查（数据库 vs CSV）
- 元数据管理
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class DataBackup:
    """数据备份管理类"""
    
    def __init__(self, backup_root: Optional[str] = None):
        """
        初始化备份管理器
        
        Args:
            backup_root: 备份根目录，如果为None则使用项目根目录下的data_backup
        """
        if backup_root is None:
            # 默认在项目根目录下的data_backup
            self.backup_root = Path(__file__).resolve().parent.parent.parent.parent / "data_backup"
        else:
            self.backup_root = Path(backup_root)
        
        self.ohlcv_dir = self.backup_root / "ohlcv"
        self.factors_dir = self.backup_root / "factors"
        self.metadata_path = self.backup_root / "metadata.json"
        
        # 创建目录结构
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        """确保备份目录存在"""
        self.ohlcv_dir.mkdir(parents=True, exist_ok=True)
        self.factors_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建各频率子目录
        for freq in ["1m", "5m", "15m", "30m", "1h", "1d"]:
            (self.ohlcv_dir / freq).mkdir(exist_ok=True)

    @property
    def term_structure_dir(self) -> Path:
        """期限结构CSV备份目录"""
        path = self.backup_root / "term_structure"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _get_term_csv_path(self, symbol: str, freq: str) -> Path:
        """获取期限结构CSV文件路径"""
        freq_dir = self.term_structure_dir / freq
        freq_dir.mkdir(parents=True, exist_ok=True)
        return freq_dir / f"{symbol}.csv"
    
    def _get_csv_path(self, symbol: str, freq: str) -> Path:
        """
        获取CSV文件路径
        
        Args:
            symbol: 品种代码
            freq: 频率（1m, 1h, 1d等）
        
        Returns:
            CSV文件路径
        """
        return self.ohlcv_dir / freq / f"{symbol}.csv"
    
    def _load_metadata(self) -> Dict[str, Any]:
        """加载元数据"""
        if self.metadata_path.exists():
            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "last_backup_time": None,
            "total_records": 0,
            "symbols": {},
            "schema_version": "v1"
        }
    
    def _save_metadata(self, metadata: Dict[str, Any]):
        """保存元数据"""
        metadata["last_backup_time"] = datetime.utcnow().isoformat()
        with open(self.metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    def backup_ohlcv(self, symbol: str, freq: str, df: pd.DataFrame):
        """
        备份OHLCV数据到CSV
        
        Args:
            symbol: 品种代码
            freq: 频率
            df: 数据DataFrame
        """
        if df.empty:
            logger.warning(f"空数据，跳过备份: {symbol} {freq}")
            return
        
        csv_path = self._get_csv_path(symbol, freq)
        
        # 确保列顺序和格式正确
        expected_columns = [
            'symbol', 'datetime', 'open', 'high', 'low', 'close', 
            'volume', 'open_oi', 'close_oi'
        ]
        
        # 重命名列以匹配期望格式
        df_backup = df.copy()
        
        # 检查datetime列
        if 'datetime' not in df_backup.columns and 'ts' in df_backup.columns:
            df_backup = df_backup.rename(columns={'ts': 'datetime'})
        
        # 确保symbol列存在
        if 'symbol' not in df_backup.columns:
            df_backup['symbol'] = symbol
        
        # 只保留需要的列
        available_columns = [col for col in expected_columns if col in df_backup.columns]
        df_backup = df_backup[available_columns]
        
        # 保存到CSV
        df_backup.to_csv(csv_path, index=False, encoding='utf-8')
        
        # 更新元数据
        metadata = self._load_metadata()
        if "symbols" not in metadata:
            metadata["symbols"] = {}
        if symbol not in metadata["symbols"]:
            metadata["symbols"][symbol] = {}
        
        metadata["symbols"][symbol][freq] = {
            "records": len(df_backup),
            "last_datetime": str(df_backup['datetime'].max()) if 'datetime' in df_backup.columns else None
        }
        
        # 计算总记录数
        total = 0
        for sym_data in metadata["symbols"].values():
            for freq_data in sym_data.values():
                total += freq_data.get("records", 0)
        metadata["total_records"] = total
        
        self._save_metadata(metadata)
        
        logger.info(f"备份完成: {symbol} {freq} → {csv_path} ({len(df_backup)}条)")

    def backup_term_structure(self, symbol: str, freq: str, df: pd.DataFrame):
        """
        备份期限结构数据到CSV

        Args:
            symbol: 品种代码
            freq: 频率
            df: 期限结构DataFrame
        """
        if df.empty:
            logger.warning(f"空数据，跳过期限结构备份: {symbol} {freq}")
            return

        csv_path = self._get_term_csv_path(symbol, freq)

        # 确保关键列存在
        df_backup = df.copy()
        if 'datetime' not in df_backup.columns and 'ts' in df_backup.columns:
            df_backup = df_backup.rename(columns={'ts': 'datetime'})

        # 确保symbol列存在
        if 'symbol' not in df_backup.columns:
            df_backup['symbol'] = symbol

        # 保存到CSV
        df_backup.to_csv(csv_path, index=False, encoding='utf-8')

        logger.info(f"期限结构备份完成: {symbol} {freq} → {csv_path} ({len(df_backup)}条)")

    def restore_term_structure(self, symbol: str, freq: str) -> Optional[pd.DataFrame]:
        """
        从CSV恢复期限结构数据

        Args:
            symbol: 品种代码
            freq: 频率

        Returns:
            恢复的DataFrame，如果文件不存在返回None
        """
        csv_path = self._get_term_csv_path(symbol, freq)

        if not csv_path.exists():
            logger.warning(f"期限结构备份文件不存在: {csv_path}")
            return None

        try:
            df = pd.read_csv(csv_path, encoding='utf-8')

            # 转换datetime列
            if 'datetime' in df.columns:
                df['datetime'] = pd.to_datetime(df['datetime'])
                df['ts'] = df['datetime']

            logger.info(f"期限结构恢复完成: {csv_path} → {symbol} {freq} ({len(df)}条)")
            return df

        except Exception as e:
            logger.error(f"期限结构恢复失败: {csv_path}, 错误: {e}")
            return None
    
    def restore_ohlcv(self, symbol: str, freq: str) -> Optional[pd.DataFrame]:
        """
        从CSV恢复OHLCV数据
        
        Args:
            symbol: 品种代码
            freq: 频率
        
        Returns:
            恢复的DataFrame，如果文件不存在返回None
        """
        csv_path = self._get_csv_path(symbol, freq)
        
        if not csv_path.exists():
            logger.warning(f"备份文件不存在: {csv_path}")
            return None
        
        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
            
            # 转换datetime列
            if 'datetime' in df.columns:
                df['datetime'] = pd.to_datetime(df['datetime'])
                # 同时创建ts列（兼容原格式）
                df['ts'] = df['datetime']
            
            logger.info(f"恢复完成: {csv_path} → {symbol} {freq} ({len(df)}条)")
            return df
            
        except Exception as e:
            logger.error(f"恢复失败: {csv_path}, 错误: {e}")
            return None
    
    def get_csv_record_count(self, symbol: str, freq: str) -> int:
        """
        获取CSV备份中的记录数
        
        Args:
            symbol: 品种代码
            freq: 频率
        
        Returns:
            记录数
        """
        csv_path = self._get_csv_path(symbol, freq)
        if not csv_path.exists():
            return 0
        
        try:
            df = pd.read_csv(csv_path, encoding='utf-8', usecols=[0])
            return len(df)
        except Exception:
            return 0
    
    def check_backup_status(self, db_counts: Dict[Tuple[str, str], int]) -> Dict[str, Any]:
        """
        检查备份状态（数据库 vs CSV）
        
        Args:
            db_counts: 数据库记录数，格式为 {(symbol, freq): count}
        
        Returns:
            状态检查结果
        """
        metadata = self._load_metadata()
        csv_counts = {}
        
        # 统计CSV记录数
        for (symbol, freq), _ in db_counts.items():
            csv_counts[(symbol, freq)] = self.get_csv_record_count(symbol, freq)
        
        # 检查各品种
        issues = []
        all_ok = True
        
        for (symbol, freq), db_count in db_counts.items():
            csv_count = csv_counts.get((symbol, freq), 0)
            
            if db_count == 0 and csv_count > 0:
                issues.append({
                    "symbol": symbol,
                    "freq": freq,
                    "issue": "database_empty",
                    "db_count": db_count,
                    "csv_count": csv_count
                })
                all_ok = False
            elif db_count < csv_count * 0.9 and csv_count > 0:
                issues.append({
                    "symbol": symbol,
                    "freq": freq,
                    "issue": "database_outdated",
                    "db_count": db_count,
                    "csv_count": csv_count
                })
                all_ok = False
        
        return {
            "all_ok": all_ok,
            "metadata": metadata,
            "db_counts": db_counts,
            "csv_counts": csv_counts,
            "issues": issues,
            "needs_restore": not all_ok
        }
    
    def get_backup_metadata(self) -> Dict[str, Any]:
        """获取备份元数据"""
        return self._load_metadata()
    
    def list_backed_up_symbols(self) -> List[str]:
        """列出所有有备份的品种"""
        metadata = self._load_metadata()
        return list(metadata.get("symbols", {}).keys())
    
    def list_backed_up_freqs(self, symbol: str) -> List[str]:
        """列出指定品种的备份频率"""
        metadata = self._load_metadata()
        sym_data = metadata.get("symbols", {}).get(symbol, {})
        return list(sym_data.keys())
    
    def get_latest_timestamp(self, symbol: str, freq: str) -> Optional[datetime]:
        """
        获取CSV备份中的最新时间戳
        
        Args:
            symbol: 品种代码
            freq: 频率
        
        Returns:
            最新时间戳，如果备份不存在返回None
        """
        csv_path = self._get_csv_path(symbol, freq)
        
        if not csv_path.exists():
            return None
        
        try:
            df = pd.read_csv(csv_path, encoding='utf-8', usecols=['datetime'])
            if df.empty:
                return None
            
            # 解析datetime列
            df['datetime'] = pd.to_datetime(df['datetime'])
            latest_dt = df['datetime'].max()
            
            # 转换为标准datetime对象
            if isinstance(latest_dt, pd.Timestamp):
                latest_dt = latest_dt.to_pydatetime()
            
            return latest_dt
            
        except Exception as e:
            logger.debug(f"获取最新时间戳失败: {csv_path}, 错误: {e}")
            return None
