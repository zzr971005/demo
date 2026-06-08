"""
数据质量监控系统 - 缺失值、异常值、延迟、一致性检查
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DataQualityMonitor:
    """数据质量监控器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化监控器
        
        Parameters
        ----------
        config : Dict[str, Any]
            配置字典
        """
        self.config = config or {}
        self.quality_thresholds = self.config.get("quality_thresholds", {
            "max_missing_ratio": 0.05,
            "max_outlier_ratio": 0.01,
            "max_delay_seconds": 60
        })
    
    def check_missing_values(
        self,
        data: np.ndarray,
        timestamps: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        检查缺失值
        
        Parameters
        ----------
        data : np.ndarray
            数据数组
        timestamps : Optional[np.ndarray]
            时间戳数组
        
        Returns
        -------
        Dict[str, Any]
            缺失值检查结果
        """
        total_count = len(data)
        missing_count = np.sum(np.isnan(data))
        missing_ratio = missing_count / total_count if total_count > 0 else 0
        
        # 检查连续缺失
        if timestamps is not None:
            expected_interval = np.median(np.diff(timestamps))
            gaps = np.diff(timestamps)
            large_gaps = gaps > expected_interval * 2
            gap_count = np.sum(large_gaps)
        else:
            gap_count = 0
        
        return {
            "total_count": total_count,
            "missing_count": int(missing_count),
            "missing_ratio": float(missing_ratio),
            "gap_count": int(gap_count),
            "passes": missing_ratio <= self.quality_thresholds["max_missing_ratio"]
        }
    
    def check_outliers(
        self,
        data: np.ndarray,
        method: str = "iqr"
    ) -> Dict[str, Any]:
        """
        检查异常值
        
        Parameters
        ----------
        data : np.ndarray
            数据数组
        method : str
            检测方法 (iqr/zscore)
        
        Returns
        -------
        Dict[str, Any]
            异常值检查结果
        """
        data_clean = data[~np.isnan(data)]
        total_count = len(data_clean)
        
        if method == "iqr":
            Q1 = np.percentile(data_clean, 25)
            Q3 = np.percentile(data_clean, 75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            outliers = (data_clean < lower_bound) | (data_clean > upper_bound)
        elif method == "zscore":
            mean = np.mean(data_clean)
            std = np.std(data_clean)
            z_scores = np.abs((data_clean - mean) / std)
            outliers = z_scores > 3
        else:
            outliers = np.zeros(len(data_clean), dtype=bool)
        
        outlier_count = np.sum(outliers)
        outlier_ratio = outlier_count / total_count if total_count > 0 else 0
        
        return {
            "total_count": total_count,
            "outlier_count": int(outlier_count),
            "outlier_ratio": float(outlier_ratio),
            "method": method,
            "passes": outlier_ratio <= self.quality_thresholds["max_outlier_ratio"]
        }
    
    def check_data_delay(
        self,
        timestamps: np.ndarray,
        expected_interval: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        检查数据延迟
        
        Parameters
        ----------
        timestamps : np.ndarray
            时间戳数组
        expected_interval : Optional[float]
            期望间隔（秒）
        
        Returns
        -------
        Dict[str, Any]
            延迟检查结果
        """
        if len(timestamps) < 2:
            return {"passes": True, "message": "数据不足"}
        
        if expected_interval is None:
            expected_interval = np.median(np.diff(timestamps))
        
        intervals = np.diff(timestamps)
        delays = intervals - expected_interval
        max_delay = np.max(delays)
        avg_delay = np.mean(delays)
        
        # 检查最新数据延迟
        latest_timestamp = timestamps[-1]
        current_time = datetime.utcnow().timestamp()
        latest_delay = current_time - latest_timestamp
        
        return {
            "max_delay": float(max_delay),
            "avg_delay": float(avg_delay),
            "latest_delay": float(latest_delay),
            "passes": latest_delay <= self.quality_thresholds["max_delay_seconds"]
        }
    
    def check_consistency(
        self,
        ohlcv_data: Dict[str, np.ndarray]
    ) -> Dict[str, Any]:
        """
        检查数据一致性
        
        Parameters
        ----------
        ohlcv_data : Dict[str, np.ndarray]
            OHLCV数据字典
        
        Returns
        -------
        Dict[str, Any]
            一致性检查结果
        """
        issues = []
        
        open_price = ohlcv_data.get("open")
        high_price = ohlcv_data.get("high")
        low_price = ohlcv_data.get("low")
        close_price = ohlcv_data.get("close")
        
        if all(v is not None for v in [open_price, high_price, low_price, close_price]):
            # 检查 high >= low
            if np.any(high_price < low_price):
                issues.append("High price < Low price")
            
            # 检查 high >= open, close
            if np.any(high_price < open_price) or np.any(high_price < close_price):
                issues.append("High price < Open or Close")
            
            # 检查 low <= open, close
            if np.any(low_price > open_price) or np.any(low_price > close_price):
                issues.append("Low price > Open or Close")
        
        return {
            "issues": issues,
            "passes": len(issues) == 0
        }
    
    def calculate_quality_score(
        self,
        checks: Dict[str, Dict[str, Any]]
    ) -> float:
        """
        计算数据质量评分
        
        Parameters
        ----------
        checks : Dict[str, Dict[str, Any]]
            各项检查结果
        
        Returns
        -------
        float
            质量评分 (0-1)
        """
        total_checks = len(checks)
        passed_checks = sum(1 for check in checks.values() if check.get("passes", False))
        
        quality_score = passed_checks / total_checks if total_checks > 0 else 0
        
        return quality_score
    
    def generate_quality_report(
        self,
        data: Dict[str, Any],
        timestamps: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        生成数据质量报告
        
        Parameters
        ----------
        data : Dict[str, Any]
            数据字典
        timestamps : Optional[np.ndarray]
            时间戳数组
        
        Returns
        -------
        Dict[str, Any]
            质量报告
        """
        checks = {}
        
        # 检查各项指标
        for key, values in data.items():
            if isinstance(values, np.ndarray):
                checks[f"{key}_missing"] = self.check_missing_values(values, timestamps)
                checks[f"{key}_outliers"] = self.check_outliers(values)
        
        if timestamps is not None:
            checks["delay"] = self.check_data_delay(timestamps)
        
        # 检查一致性
        if all(k in data for k in ["open", "high", "low", "close"]):
            ohlcv_data = {k: data[k] for k in ["open", "high", "low", "close"]}
            checks["consistency"] = self.check_consistency(ohlcv_data)
        
        # 计算综合评分
        quality_score = self.calculate_quality_score(checks)
        
        return {
            "quality_score": quality_score,
            "checks": checks,
            "report_date": datetime.utcnow(),
            "issues_count": sum(1 for c in checks.values() if not c.get("passes", False))
        }
